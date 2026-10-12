"""Collect provided walking values; never infer physical scope or missing time."""
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.journeys.models import common_candidate
from app.journeys.service import check_refs, missing
from app.places.service import parsed_id
from app.walking import repository
from app.walking.dto import Evidence, Segment


def stop(leg, endpoint):
    return {'type': 'transit_stop', 'leg_id': leg['leg_id'], 'stop_name': leg[endpoint]['name']}


def collect(search_id, candidate):
    legs = candidate['ordered_legs']
    transit = [leg for leg in legs if leg['type'] != 'WALKING']
    by_id = {leg['leg_id']: leg for leg in legs}
    groups = [('access', None, [leg for leg in legs if leg['walking_role'] == 'access'],
               {'type': 'search_origin'}, stop(transit[0], 'boarding'), [transit[0]])]
    for connection in candidate['connections']:
        before, after = by_id[connection['from_leg_id']], by_id[connection['to_leg_id']]
        groups.append(('transfer', connection['connection_id'],
                       [by_id[identifier] for identifier in connection['walking_leg_ids']],
                       stop(before, 'alighting'), stop(after, 'boarding'), [before, after]))
    groups.append(('egress', None, [leg for leg in legs if leg['walking_role'] == 'egress'],
                   stop(transit[-1], 'alighting'), {'type': 'search_destination'}, [transit[-1]]))
    segments = []
    for role, connection_id, walking, origin, destination, adjacent in groups:
        seconds = sum(leg['seconds'] for leg in walking) if walking else None
        distance = sum(leg['distance_meters'] for leg in walking) if walking else None
        reasons = ['PHYSICAL_ENDPOINTS_UNCONFIRMED']
        if not walking: reasons.append('PROVIDER_WALK_MISSING')
        elif seconds == 0: reasons.append('WALK_DURATION_ZERO')
        if any(leg['type'] == 'SUBWAY' for leg in adjacent):
            reasons.append('ENTRANCE_PLATFORM_UNCONFIRMED')
        segments.append(Segment(
            segment_id=uuid5(NAMESPACE_URL, f'walking:{search_id}:{candidate["candidate_id"]}:{role}:{connection_id}'),
            role=role, connection_id=connection_id, walking_leg_ids=[leg['leg_id'] for leg in walking],
            from_ref=origin, to_ref=destination, provider_duration_seconds=seconds,
            provider_distance_meters=distance, source='provider_estimate' if walking else 'missing',
            scope='provider_walking_segment' if walking else 'unknown', missing_segments=reasons))
    return segments


def result(request, search_id, candidate_id):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        identifier, candidate_identifier = parsed_id(search_id), parsed_id(candidate_id)
        row = repository.find_search(connection, identifier, user_id)
        if not row or row['status'] != 'succeeded' or row['expires_at'] <= datetime.now(timezone.utc):
            missing()
        check_refs(connection, user_id, row['place_refs'])
    values = row['candidates']
    if not isinstance(values, list) or len(values) > 20:
        raise AuthError(502, 'PROVIDER_RESPONSE_INVALID', '경로 구간을 확인할 수 없어요.')
    candidates = [common_candidate(value) for value in values]
    candidate = next((value for value in candidates if value['candidate_id'] == str(candidate_identifier)), None)
    if candidate is None: missing()
    data = Evidence(search_id=identifier, candidate_id=candidate_identifier, expires_at=row['expires_at'],
                    segments=collect(identifier, candidate))
    return answer(request, data.model_dump(mode='json'))
