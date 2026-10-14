"""Owned first BUS departure approximation, never a complete journey guarantee."""
from datetime import timedelta
from decimal import Decimal,ROUND_CEILING
import math
import time
from fastapi import Request
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.arrivals import service as arrivals
from app.walking.history_repository import profile as owned_profile
from app.guidance.dto import Departure


def settings(user_id):
    with database() as connection:row=owned_profile(connection,user_id)
    if not row or row['status']!='active':arrivals.missing()
    factor=row['walking_duration_factor'];buffer=row['first_boarding_buffer_seconds']
    if type(factor) not in (int,float) or not math.isfinite(factor) or not .5<=factor<=2 or type(buffer) is not int or not 0<=buffer<=1800:
        raise AuthError(422,'VALIDATION_ERROR','개인 이동 설정을 확인해주세요.')
    transfer=row['transfer_buffer_seconds']
    if type(transfer) is not int or not 0<=transfer<=1800:raise AuthError(422,'VALIDATION_ERROR','환승 여유 설정을 확인해주세요.')
    return {'version':row['version'],'factor':float(factor),'buffer':buffer,'transfer_buffer':transfer}


def approach(candidate,factor):
    prefix=[]
    for leg in candidate['ordered_legs']:
        if leg['type']!='WALKING':break
        prefix.append(leg)
    if not prefix or 'ACCESS_WALK_MISSING' in candidate['missing_segments'] or any(leg['walking_role']!='access' or leg['seconds']<=0 for leg in prefix):
        return None,None
    base=sum(leg['seconds'] for leg in prefix)
    try:return base,int((Decimal(base)*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
    except (ArithmeticError,ValueError):return None,None


def calculate(evidence,base,walking,profile,at,basis='recommended',*,choice=None):
    evidence=arrivals.project(evidence,at)
    data=Departure(search_id=evidence.search_id,candidate_id=evidence.candidate_id,first_leg_id=evidence.first_leg_id,
        status='insufficient_data',departure_basis=basis,calculated_at=at,
        valid_until=min(evidence.expires_at,at+timedelta(seconds=120)),profile_version=profile['version'],buffer_seconds=profile['buffer'],
        timing_basis=evidence.timing_basis,reasons=[],arrival_evidence=evidence)
    if choice and choice.get('reported'):
        data.departure_state='reported_departed';data.reasons=['DEPARTURE_ALREADY_REPORTED'];return data
    if evidence.status=='unsupported':data.status='unsupported';data.reasons=['PROVIDER_UNSUPPORTED'];return data
    if at>evidence.expires_at:data.status='stale';data.reasons=['ARRIVAL_EXPIRED'];return data
    if base is None or walking is None:data.reasons=['ACCESS_TIME_UNCONFIRMED'];return data
    data.provider_approach_seconds=base;data.approach_seconds=walking
    data.provider_approach_source='transit_segment'
    data.applied_duration_factor=profile['factor'];data.approach_basis='provider_personalized'
    approved=(evidence.status=='estimated' and evidence.timing_basis=='receipt_estimate' and evidence.source_status=='unknown' and evidence.generated_at is None) or (evidence.status=='fresh' and evidence.timing_basis=='source_generation' and evidence.source_status=='fresh' and evidence.generated_at is not None)
    if not approved or not evidence.valid_for_guidance or not evidence.candidates:
        data.reasons=['ARRIVAL_UNAVAILABLE'];return data
    if choice and choice.get('blocked'):
        data.reasons=[choice['reason']];return data
    ordered=sorted(evidence.candidates,key=lambda item:(item.predicted_arrival_at,str(item.candidate_id)))
    candidate=next((item for item in ordered if (item.predicted_arrival_at-at).total_seconds()>=walking),ordered[0])
    if choice and choice.get('candidate_id') is not None:
        candidate=next((item for item in ordered if str(item.candidate_id)==choice['candidate_id']),None)
        if candidate is None:data.reasons=['SELECTION_IDENTITY_UNCONFIRMED'];return data
    vehicle=candidate.predicted_arrival_at
    try:
        recommended=vehicle-timedelta(seconds=walking+profile['buffer'])
        selected=at if basis=='now' or recommended<at else recommended
        slack=math.floor((vehicle-selected).total_seconds()-walking)
    except (OverflowError,TypeError,ValueError):
        data.approach_seconds=None;data.provider_approach_seconds=None;data.applied_duration_factor=None;data.approach_basis=None
        data.reasons=['ACCESS_TIME_UNCONFIRMED'];return data
    data.recommended_departure_at=recommended;data.selected_departure_at=selected
    data.vehicle_arrival_at=vehicle;data.arrival_candidate_id=candidate.candidate_id;data.slack_seconds=slack
    data.slack_status='unreachable' if slack<0 else 'below_buffer' if slack<profile['buffer'] else 'meets_buffer'
    data.status='not_enough_time' if slack<0 else 'ready';data.valid_for_guidance=slack>=0
    data.reasons=['PROVIDER_ACCESS_ESTIMATE']+(['RECEIPT_BASED_ESTIMATE'] if evidence.timing_basis=='receipt_estimate' else [])
    if candidate.candidate_id!=ordered[0].candidate_id:data.reasons.append('NEXT_REACHABLE_VEHICLE')
    if data.slack_status=='below_buffer':data.reasons.append('BUFFER_NOT_MET')
    if choice and choice.get('reason'):
        data.reasons=[reason for reason in data.reasons if reason!='NEXT_REACHABLE_VEHICLE']+[choice['reason']]
    return data


def first_departure(user_id,search_id,candidate_id,basis='recommended',include_connections=False,*,access_origin_ref=None,selector=None,reported_departure=False):
    deadline=time.monotonic()+20
    if basis not in ('recommended','now'):raise AuthError(422,'VALIDATION_ERROR','출발 기준을 확인해주세요.')
    user_id=arrivals.parsed_id(str(user_id));search_id=arrivals.parsed_id(str(search_id));candidate_id=arrivals.parsed_id(str(candidate_id))
    before,route,first,fingerprint=arrivals.owned(user_id,search_id,candidate_id)
    profile=settings(user_id);base,walking=approach(route,profile['factor'])
    if reported_departure:
        from app.arrivals.dto import Evidence
        at=arrivals.now()
        evidence=Evidence(search_id=search_id,candidate_id=candidate_id,first_leg_id=first['leg_id'],status='insufficient_data',
            expires_at=min(before['expires_at'],at+timedelta(seconds=120)),reasons=['DEPARTURE_ALREADY_REPORTED'])
        return calculate(evidence,None,None,profile,at,basis,choice={'reported':True})
    evidence=arrivals.first_arrivals(user_id,search_id,candidate_id)
    current,_,_,current_fingerprint=arrivals.owned(user_id,search_id,candidate_id)
    if current_fingerprint!=fingerprint or settings(user_id)!=profile:
        raise AuthError(409,'VERSION_CONFLICT','경로 또는 개인 설정이 변경됐어요. 다시 확인해주세요.')
    evidence=evidence.model_copy(deep=True);evidence.expires_at=min(evidence.expires_at,current['expires_at'])
    walk_evidence=None;walk_reason=None
    if base is None and access_origin_ref is not None and first['type']=='BUS' and first['sequence']==0 and 'ACCESS_WALK_MISSING' in route['missing_segments'] and evidence.valid_for_guidance:
        from app.guidance import access
        walk_evidence,walk_reason=access.get(user_id,search_id,candidate_id,first,fingerprint,access_origin_ref,deadline)
        latest,_,_,latest_fingerprint=arrivals.owned(user_id,search_id,candidate_id)
        if latest_fingerprint!=fingerprint or settings(user_id)!=profile:
            raise AuthError(409,'VERSION_CONFLICT','경로 또는 개인 설정이 변경됐어요. 다시 확인해주세요.')
        evidence.expires_at=min(evidence.expires_at,latest['expires_at'])
        if walk_evidence is not None:
            base=walk_evidence['seconds']
            walking=int((Decimal(base)*Decimal(str(profile['factor']))).to_integral_value(rounding=ROUND_CEILING))
    at=arrivals.now()
    choice=selector(evidence,walking,profile,at,fingerprint) if selector is not None else None
    data=calculate(evidence,base,walking,profile,at,basis,choice=choice)
    if walk_evidence is not None:
        data.provider_approach_source='boarding_walk'
        data.approach_fetched_at=walk_evidence['fetched_at'];data.approach_valid_until=walk_evidence['expires_at']
        data.valid_until=min(data.valid_until,walk_evidence['expires_at'])
        data.reasons.append('BOARDING_WALK_ESTIMATE')
    elif walk_reason:data.reasons.append(walk_reason)
    if include_connections:
        from app.guidance.connections import evaluate,following_arrivals
        data=evaluate(route,data,profile,arrivals.now(),lambda leg:following_arrivals(user_id,search_id,candidate_id,leg,fingerprint,deadline))
        latest,_,_,latest_fingerprint=arrivals.owned(user_id,search_id,candidate_id)
        if latest_fingerprint!=fingerprint or settings(user_id)!=profile:
            raise AuthError(409,'VERSION_CONFLICT','경로 또는 개인 설정이 변경됐어요. 다시 확인해주세요.')
        data.valid_until=min(data.valid_until,latest['expires_at'])
        if time.monotonic()>deadline:
            data.connection_status='unknown';data.transfers=[];data.estimated_final_alighting_at=None;data.reasons.append('CONNECTION_TIME_LIMIT')
        if arrivals.now()>data.valid_until or (data.vehicle_arrival_at is not None and arrivals.now()>=data.vehicle_arrival_at):
            data.connection_status='stale';data.transfers=[];data.estimated_final_alighting_at=None
            data.valid_for_guidance=False;data.status='stale'
    return data


def result(request:Request,search_id,candidate_id,basis,include_connections=False):
    with database() as connection:user_id=security.authenticated(connection,request)
    return answer(request,first_departure(user_id,search_id,candidate_id,basis,include_connections).model_dump(mode='json'))
