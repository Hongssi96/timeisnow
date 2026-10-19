"""Sequential connection checks on mapped current predictions; no invented timetable."""
from datetime import timedelta
from decimal import Decimal,ROUND_CEILING
import time
from app.arrivals import cache,provider,service as arrivals
from app.arrivals.dto import Evidence
from app.common.errors import AuthError
from app.guidance.dto import TransferCheck


def unconfirmed(search_id,candidate_id,leg,expiry,reason):
    return Evidence(search_id=search_id,candidate_id=candidate_id,first_leg_id=leg['leg_id'],status='mapping_required',
        expires_at=expiry,reasons=[reason])


def following_arrivals(user_id,search_id,candidate_id,leg,snapshot,deadline):
    row,_,_,current=arrivals.owned(user_id,search_id,candidate_id)
    if current!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요.')
    root=cache.lookup(user_id,search_id,candidate_id,snapshot,arrivals.now())
    entry=cache.following_entry(root,leg['leg_id']) if root else None
    if entry is None:return unconfirmed(search_id,candidate_id,leg,row['expires_at'],'LEG_MAPPING_UNCONFIRMED')
    if not entry.lock.acquire(blocking=False):raise AuthError(429,'RATE_LIMITED','연결 정보를 조회 중이에요.',{'Retry-After':'2'})
    try:
        at=arrivals.now();expiry=min(entry.expires_at,row['expires_at'])
        if entry.evidence is not None and entry.attempted_at is not None and at-entry.attempted_at<timedelta(seconds=60) and at<=entry.evidence.expires_at:
            evidence=entry.evidence.model_copy(deep=True);evidence.expires_at=min(evidence.expires_at,expiry)
            return arrivals.project(evidence,at)
        if entry.mapping is None and entry.mapping_attempted_at is not None and at-entry.mapping_attempted_at<timedelta(seconds=60):
            return unconfirmed(search_id,candidate_id,leg,expiry,'LEG_MAPPING_UNCONFIRMED')
        if deadline-time.monotonic()<=3:return unconfirmed(search_id,candidate_id,leg,expiry,'CONNECTION_TIME_LIMIT')
        arrivals.reserve_refresh(user_id)
        diagnostics={}
        endpoint={}
        value=entry.mapping or arrivals.public_mapping.resolve(entry.context,expiry,deadline=deadline,diagnostics=diagnostics,boarding_endpoint=endpoint)
        updated,_,_,after=arrivals.owned(user_id,search_id,candidate_id)
        if after!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요.')
        expiry=min(expiry,updated['expires_at'])
        if value is None:
            evidence=unconfirmed(search_id,candidate_id,leg,expiry,'LEG_MAPPING_UNCONFIRMED')
            reason=arrivals.public_mapping.safe_failure_reason(diagnostics)
            if reason:evidence.reasons.append(reason)
        else:
            mapping=arrivals.checked_mapping(value,leg,arrivals.now())
            if deadline-time.monotonic()<=3:return unconfirmed(search_id,candidate_id,leg,expiry,'CONNECTION_TIME_LIMIT')
            values=provider.fetch(mapping);received=arrivals.now()
            if time.monotonic()>deadline:return unconfirmed(search_id,candidate_id,leg,expiry,'CONNECTION_TIME_LIMIT')
            updated,_,_,after=arrivals.owned(user_id,search_id,candidate_id)
            if after!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요.')
            arrivals.checked_mapping(mapping,leg,arrivals.now())
            evidence=arrivals.normalize(mapping,values,received,arrivals.now(),search_id,candidate_id,min(expiry,updated['expires_at']))
            entry.mapping=mapping
            if endpoint:entry.boarding_endpoint=endpoint
        entry.evidence=evidence.model_copy(deep=True);entry.attempted_at=evidence.received_at or arrivals.now()
        return evidence
    finally:entry.lock.release()


def evaluate(route,departure,profile,at,fetch):
    if len(route['connections'])>2:
        departure.connection_status='unknown';departure.reasons.append('TRANSFER_LIMIT');return departure
    legs={leg['leg_id']:leg for leg in route['ordered_legs']}
    transit=[leg for leg in route['ordered_legs'] if leg['type']!='WALKING']
    checks=[];board=departure.vehicle_arrival_at if departure.valid_for_guidance else None
    overall='estimated_feasible' if board is not None else 'unknown'
    for connection in route['connections']:
        check=TransferCheck(connection_id=connection['connection_id'],from_leg_id=connection['from_leg_id'],
            to_leg_id=connection['to_leg_id'],transfer_buffer_seconds=profile['transfer_buffer'])
        previous=legs[connection['from_leg_id']];following=legs[connection['to_leg_id']]
        if board is None:
            check.reasons=['PREVIOUS_BOARDING_UNCONFIRMED'];checks.append(check);continue
        from app.guidance.route_walks import adjusted_transfer
        walk=adjusted_transfer(connection,departure,profile['factor'])
        if previous['seconds']<=0 or walk is None:
            check.reasons=['TRANSFER_TIME_UNCONFIRMED'];board=None;overall='unknown';checks.append(check);continue
        try:
            alight=board+timedelta(seconds=previous['seconds']);minimum=alight+timedelta(seconds=walk+profile['transfer_buffer'])
        except (ArithmeticError,ValueError,OverflowError):
            check.reasons=['TRANSFER_TIME_UNCONFIRMED'];board=None;overall='unknown';checks.append(check);continue
        check.estimated_alighting_at=alight;check.minimum_boarding_at=minimum;check.transfer_walk_seconds=walk
        manual=any(w.kind=='transfer' and str(w.leg_id)==connection['to_leg_id'] for w in departure.personal_segment_walks)
        if connection['walking_seconds'] is None and not manual:check.reasons.append('SUPPLEMENTAL_TRANSFER_WALK')
        if walk==0:check.reasons.append('SAME_STOP_TRANSFER')
        if manual:check.reasons.append('MANUAL_HISTORY_WALK')
        if previous['type']!='BUS' or following['type']!='BUS':
            check.reasons=['TRANSFER_PROVIDER_UNSUPPORTED'];board=None;overall='unknown';checks.append(check);continue
        evidence=fetch(following)
        approved=(evidence.status=='estimated' and evidence.timing_basis=='receipt_estimate' and evidence.source_status=='unknown' and evidence.generated_at is None) or (evidence.status=='fresh' and evidence.timing_basis=='source_generation' and evidence.source_status=='fresh' and evidence.generated_at is not None)
        departure.valid_until=min(departure.valid_until,evidence.expires_at)
        if not approved or not evidence.valid_for_guidance or at>evidence.expires_at:
            check.reasons=evidence.reasons or ['TRANSFER_ARRIVAL_UNCONFIRMED'];board=None;overall='unknown';checks.append(check);continue
        options=[item for item in evidence.candidates if item.predicted_arrival_at is not None and item.predicted_arrival_at>=minimum]
        check.time_source=evidence.timing_basis
        if not options:
            check.feasibility='unavailable';check.reasons=['NO_SUPPLIED_VEHICLE_AFTER_MINIMUM'];board=None;overall='unavailable';checks.append(check);continue
        chosen=min(options,key=lambda item:(item.predicted_arrival_at,str(item.candidate_id)))
        board=chosen.predicted_arrival_at;check.next_boarding_at=board;check.feasibility='estimated_feasible'
        check.reasons.append('PROVIDER_TRANSFER_ESTIMATE');checks.append(check)
    departure.transfers=checks;departure.connection_status=overall
    if board is not None and transit[-1]['seconds']>0:
        try:departure.estimated_final_alighting_at=board+timedelta(seconds=transit[-1]['seconds'])
        except OverflowError:departure.connection_status='unknown'
    return departure
