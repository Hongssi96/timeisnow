"""Synchronous per-member departure guidance for confirmed meetings.

계약 기준: meeting_api.md 5절·Notion 16절. 검증된 루틴 출발 계산(first_departure)을
약속 목표 도착에 재사용하고 개인 여정(meeting_journeys)으로 연결한다. 같은 약속 revision·
본인 여정의 재조회는 기존 여정과 저장된 후보를 재사용하며, 경로 증거가 만료되면 새 여정을
만든다. 개인 좌표는 응답에 절대 노출하지 않는다.
"""
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from pydantic import TypeAdapter
from uuid import UUID, uuid4

from fastapi import Request

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.guidance import issued
from app.guidance import service as departure
from app.guidance.dto import Departure
from app.guidance.route_walks import egress_seconds
from app.guidance.routine import signature as route_signature
from app.journeys import service as journeys
from app.journeys.dto import Endpoint, SearchInput

ENDPOINT_ADAPTER = TypeAdapter(Endpoint)
from app.journeys.models import common_candidate
from app.meetings.dto import checked_idempotency_key, meeting_id_value
from app.meetings.repository import PostgresMeetingRepository
from app.meetings.service import digest, missing_meeting
from app.places.service import parsed_id
from app.routines import repository as routine_repository


@dataclass(frozen=True)
class MeetingBinding:
    """The short-lived owner binding stored with a published guidance token."""

    user_id: object
    meeting_id: object
    meeting_revision_id: object
    meeting_journey_id: object
    member_id: object
    version: int
    signature: str
    expires_at: datetime
    place_refs: tuple


class _InnerRequest:
    """journeys.search reads the header key; a meeting guidance call derives its own."""

    def __init__(self, request, key):
        self._request = request
        self.headers = {**request.headers, 'idempotency-key': key}

    def __getattr__(self, name):
        return getattr(self._request, name)


def missing_revision():
    raise AuthError(409, 'MEETING_REVISION_CHANGED', '약속이 변경됐어요. 약속을 다시 확인해주세요.')


def origin_required():
    raise AuthError(409, 'ORIGIN_REQUIRED', '먼저 내 출발지를 설정해주세요.')


def origin_fingerprint(origin):
    return digest(json.dumps(origin, sort_keys=True, ensure_ascii=False))


def pinned_origin(connection, user_id, endpoint):
    """Validate the endpoint against owned places; saved_place pins its current version."""
    refs = []
    journeys.resolve(connection, user_id, endpoint, refs)
    origin = endpoint.model_dump(mode='json')
    if refs:
        origin['location_version'] = refs[0]['location_version']
    return origin


def prepare(connection, repo, meeting_id, user_id, body):
    """Membership, confirmation, latest revision and a validated origin in one read pass."""
    member = repo.find_member(connection, meeting_id, user_id)
    if not member or member['participation_status'] != 'active':
        missing_meeting()
    meeting = repo.find_meeting(connection, meeting_id)
    if not meeting:
        missing_meeting()
    if meeting['status'] != 'confirmed':
        raise AuthError(409, 'MEETING_NOT_CONFIRMED', '먼저 약속 장소와 시각을 확정해주세요.')
    revision = repo.latest_revision(connection, meeting['id'])
    if revision is None or str(revision['id']) != body.meeting_revision_id:
        missing_revision()
    raw_origin = body.origin_override.model_dump() if body.origin_override is not None else member['private_origin']
    if raw_origin is None:
        origin_required()
    return meeting, member, revision, pinned_origin(connection, user_id, ENDPOINT_ADAPTER.validate_python(raw_origin))


def choose_candidate(journey_row, candidates):
    """Stored journey candidate first; otherwise the provider's top transit candidate."""
    stored = journey_row['candidate_id']
    if stored is not None:
        match = next((c for c in candidates if str(c['candidate_id']) == str(stored)), None)
        if match is not None:
            return match, journey_row['candidate_signature']
    selected = next((c for c in candidates if any(leg['type'] != 'WALKING' for leg in c['ordered_legs'])), None)
    if selected is None and candidates:
        selected = candidates[0]
    return selected, (None if selected is None else route_signature(selected))


def insufficient_guidance(search, basis, profile):
    now = datetime.now(timezone.utc)
    nil = UUID(int=0)
    return Departure.model_validate({
        'search_id': str(search['id']), 'candidate_id': str(nil), 'first_leg_id': str(nil),
        'status': 'insufficient_data', 'departure_basis': basis, 'calculated_at': now,
        'valid_until': search['expires_at'], 'profile_version': profile['version'],
        'buffer_seconds': profile['buffer'], 'reasons': ['ROUTE_UNAVAILABLE'],
        'arrival_evidence': {'search_id': str(search['id']), 'candidate_id': str(nil), 'first_leg_id': str(nil),
                             'status': 'insufficient_data', 'expires_at': search['expires_at'],
                             'reasons': ['ROUTE_UNAVAILABLE']}})


def arrival_slack_seconds(route, value, target_arrival_at, profile):
    """target − estimated arrival at the meeting place; None when the basis is insufficient."""
    if value is None or not value.valid_for_guidance or value.connection_status != 'estimated_feasible':
        return None
    if value.estimated_final_alighting_at is None:
        return None
    base_egress = egress_seconds(route, value)
    if base_egress is None:
        return None
    egress = int((Decimal(base_egress) * Decimal(str(profile['factor']))).to_integral_value(rounding=ROUND_CEILING))
    arrival = value.estimated_final_alighting_at + timedelta(seconds=egress)
    return math.floor((target_arrival_at - arrival).total_seconds())


def obtain_journey(request, repo, user_id, meeting, member, revision, origin):
    """Reuse the member's live journey for this revision, otherwise search and link a new one."""
    with database() as connection:
        journey = repo.find_reusable_journey(connection, member['id'], revision['id'])
    if journey is not None:
        return journey, load_search(user_id, journey['journey_search_id'])
    query = SearchInput.model_validate({
        'origin': origin,
        'destination': {'type': 'map_pin', 'latitude': float(revision['destination_snapshot']['latitude']),
                        'longitude': float(revision['destination_snapshot']['longitude'])},
        'timing': {'mode': 'depart_now', 'timezone': 'Asia/Seoul'}})
    # A fresh inner key keeps journey search idempotency independent of the meeting request key.
    outcome = journeys.search(_InnerRequest(request, 'mg-' + uuid4().hex), query,
                              context={'meeting_id': str(meeting['id']), 'revision_id': str(revision['id'])})
    replay = outcome[0] == 'replay'
    data = json.loads(outcome[1].body)['data'] if replay else outcome[1]
    search_id = parsed_id(data['search_id'])
    if not replay:
        journeys.execute(*outcome[2])
    with database() as connection:
        search = routine_repository.find_journey_search(connection, search_id, user_id)
        if search is None:
            journeys.missing()
        current_member = repo.find_member(connection, meeting['id'], user_id)
        if not current_member or current_member['participation_status'] != 'active' or current_member['id'] != member['id']:
            missing_meeting()
        repo.supersede_meeting_journeys(connection, member['id'], revision['id'])
        journey = repo.insert_meeting_journey(connection, (uuid4(), member['id'], revision['id'], search_id,
                                                           origin_fingerprint(origin)))
        if journey is None:
            journey = repo.find_reusable_journey(connection, member['id'], revision['id'])
    return journey, search


def load_search(user_id, search_id):
    with database() as connection:
        return routine_repository.find_journey_search(connection, search_id, user_id)


def guidance_query(request: Request, raw_meeting_id, body):
    key = checked_idempotency_key(request)
    fingerprint = digest(json.dumps(body.model_dump(mode='json'), sort_keys=True))
    meeting_id = meeting_id_value(raw_meeting_id)
    repo = PostgresMeetingRepository()
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repo.delete_expired_keys(connection)
        repo.delete_expired_replays(connection)
        repo.advisory_lock(connection, 'meeting-guidance:' + str(user_id) + ':' + key)
        previous = repo.find_idempotency_key(connection, user_id, 'meeting-guidance', key)
        if previous:
            if previous['body_hash'] != fingerprint:
                raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 안내 요청이에요. 다시 확인해주세요.')
            if previous['meeting_id'] is None:
                missing_meeting()
            meeting_id = previous['meeting_id']
        meeting, member, revision, origin = prepare(connection, repo, meeting_id, user_id, body)
    journey, search = obtain_journey(request, repo, user_id, meeting, member, revision, origin)
    if body.trip_id is not None:
        from app.trips import repository as trip_repository
        with database() as connection:
            linked = trip_repository.find_meeting_trip(connection, user_id, parsed_id(body.trip_id), journey['id'])
        if linked is None:
            raise AuthError(404, 'RESOURCE_NOT_FOUND', '이동 기록이나 안내를 찾을 수 없어요.')
    if search['status'] == 'failed':
        error = search['error'] or {}
        raise AuthError(503, error.get('code', 'PROVIDER_UNAVAILABLE'),
                        '최신 경로를 확인하지 못했어요. 다시 확인해주세요.')
    profile = departure.settings(user_id)
    candidates = [common_candidate(c) for c in search['candidates']] if isinstance(search['candidates'], list) else []
    candidate, candidate_signature = choose_candidate(journey, candidates)
    place_refs = tuple((r['place_id'], r['location_version']) for r in search['place_refs'])
    slack = None
    published = None
    if candidate is None:
        value = insufficient_guidance(search, body.departure_basis, profile)
    else:
        access_ref = place_refs[0] if place_refs else None
        value = departure.first_departure(user_id, search['id'], parsed_id(candidate['candidate_id']),
                                          basis=body.departure_basis, include_connections=True,
                                          access_origin_ref=access_ref, destination_ref=None)
        if (profile['version'] != value.profile_version
                or (value.applied_duration_factor is not None and profile['factor'] != value.applied_duration_factor)
                or profile['buffer'] != value.buffer_seconds):
            raise AuthError(409, 'VERSION_CONFLICT', '개인 설정이 변경됐어요.')
        slack = arrival_slack_seconds(candidate, value, revision['target_arrival_at'], profile)
    # A meeting changed mid-calculation must never succeed with stale guidance.
    with database() as connection:
        current_meeting = repo.find_meeting(connection, meeting['id'])
        if not current_meeting:
            missing_meeting()
        if current_meeting['version'] != meeting['version']:
            raise AuthError(409, 'VERSION_CONFLICT', '약속이 변경됐어요. 약속을 다시 확인해주세요.')
        latest = repo.latest_revision(connection, meeting['id'])
        if latest is None or latest['id'] != revision['id']:
            missing_revision()
        current_member = repo.find_member(connection, meeting['id'], user_id)
        if not current_member or current_member['participation_status'] != 'active' or current_member['id'] != member['id']:
            missing_meeting()
        if candidate is not None:
            repo.update_journey_candidate(connection, journey['id'], str(candidate['candidate_id']),
                                          candidate_signature)
            binding = MeetingBinding(user_id=user_id, meeting_id=meeting['id'], meeting_revision_id=revision['id'],
                                     meeting_journey_id=journey['id'], member_id=member['id'],
                                     version=meeting['version'], signature=candidate_signature,
                                     expires_at=search['expires_at'], place_refs=place_refs)
            published = issued.publish(binding, candidate, value, profile)
        repo.insert_idempotency_key(connection, (user_id, 'meeting-guidance', key, fingerprint, meeting['id']))
    if published is not None:
        value.guidance_id = published
    dump = value.model_dump(mode='json')
    valid_until = datetime.fromisoformat(dump['valid_until'].replace('Z', '+00:00'))
    return {'model_version': 'meeting.departure.v1', 'meeting_id': str(meeting['id']),
            'meeting_revision_id': str(revision['id']), 'meeting_journey_id': str(journey['id']),
            'meeting_version': meeting['version'], 'guidance': dump,
            'meeting_arrival_slack_seconds': slack,
            'expires_at': iso(min(search['expires_at'], valid_until))}
