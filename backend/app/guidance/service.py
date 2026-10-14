"""Owned first BUS departure approximation, never a complete journey guarantee."""
from datetime import timedelta
from decimal import Decimal,ROUND_CEILING
import math
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
    return {'version':row['version'],'factor':float(factor),'buffer':buffer}


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


def calculate(evidence,base,walking,profile,at,basis='recommended'):
    evidence=arrivals.project(evidence,at)
    data=Departure(search_id=evidence.search_id,candidate_id=evidence.candidate_id,first_leg_id=evidence.first_leg_id,
        status='insufficient_data',departure_basis=basis,calculated_at=at,
        valid_until=min(evidence.expires_at,at+timedelta(seconds=120)),profile_version=profile['version'],buffer_seconds=profile['buffer'],
        timing_basis=evidence.timing_basis,reasons=[],arrival_evidence=evidence)
    if evidence.status=='unsupported':data.status='unsupported';data.reasons=['PROVIDER_UNSUPPORTED'];return data
    if at>evidence.expires_at:data.status='stale';data.reasons=['ARRIVAL_EXPIRED'];return data
    if base is None or walking is None:data.reasons=['ACCESS_TIME_UNCONFIRMED'];return data
    data.provider_approach_seconds=base;data.approach_seconds=walking
    data.applied_duration_factor=profile['factor'];data.approach_basis='provider_personalized'
    approved=(evidence.status=='estimated' and evidence.timing_basis=='receipt_estimate' and evidence.source_status=='unknown' and evidence.generated_at is None) or (evidence.status=='fresh' and evidence.timing_basis=='source_generation' and evidence.source_status=='fresh' and evidence.generated_at is not None)
    if not approved or not evidence.valid_for_guidance or not evidence.candidates:
        data.reasons=['ARRIVAL_UNAVAILABLE'];return data
    candidate=min(evidence.candidates,key=lambda item:(item.predicted_arrival_at,str(item.candidate_id)))
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
    if data.slack_status=='below_buffer':data.reasons.append('BUFFER_NOT_MET')
    return data


def first_departure(user_id,search_id,candidate_id,basis='recommended'):
    if basis not in ('recommended','now'):raise AuthError(422,'VALIDATION_ERROR','출발 기준을 확인해주세요.')
    user_id=arrivals.parsed_id(str(user_id));search_id=arrivals.parsed_id(str(search_id));candidate_id=arrivals.parsed_id(str(candidate_id))
    before,route,first,fingerprint=arrivals.owned(user_id,search_id,candidate_id)
    profile=settings(user_id);base,walking=approach(route,profile['factor'])
    evidence=arrivals.first_arrivals(user_id,search_id,candidate_id)
    current,_,_,current_fingerprint=arrivals.owned(user_id,search_id,candidate_id)
    if current_fingerprint!=fingerprint or settings(user_id)!=profile:
        raise AuthError(409,'VERSION_CONFLICT','경로 또는 개인 설정이 변경됐어요. 다시 확인해주세요.')
    evidence=evidence.model_copy(deep=True);evidence.expires_at=min(evidence.expires_at,current['expires_at'])
    return calculate(evidence,base,walking,profile,arrivals.now(),basis)


def result(request:Request,search_id,candidate_id,basis):
    with database() as connection:user_id=security.authenticated(connection,request)
    return answer(request,first_departure(user_id,search_id,candidate_id,basis).model_dump(mode='json'))
