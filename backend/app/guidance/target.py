"""Today's goal for the selected routine timeline; no timetable or extra lookup."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING
import math
from app.guidance.dto import TargetEvaluation
KST=timezone(timedelta(hours=9))


def evaluate(route,departure,target_time,profile,at):
    result=TargetEvaluation(status='not_configured',evaluated_at=at,reasons=['TARGET_NOT_SET'])
    if target_time is None:return result
    target=datetime.combine(at.astimezone(KST).date(),target_time,tzinfo=KST).astimezone(timezone.utc)
    result.target_arrival_at=target;result.reasons=[]
    def unknown(reason):
        result.status='unknown';result.reasons=[reason];return result
    if at>target:result.status='target_passed';result.reasons=['TODAY_TARGET_PASSED'];return result
    if departure.status=='stale' or at>departure.valid_until:
        result.status='stale';result.reasons=['GUIDANCE_EXPIRED'];return result
    if not departure.valid_for_guidance or departure.vehicle_arrival_at is None:return unknown('FIRST_BOARDING_UNCONFIRMED')
    if departure.vehicle_arrival_at<=at or (departure.vehicle_arrival_at-at).total_seconds()<departure.approach_seconds:
        return unknown('FIRST_BOARDING_UNREACHABLE')
    if departure.connection_status!='estimated_feasible':return unknown('CONNECTIONS_UNCONFIRMED')
    legs=route['ordered_legs'];transit=[leg for leg in legs if leg['type']!='WALKING']
    if not transit or any(leg['type']!='BUS' or leg['seconds']<=0 for leg in transit):return unknown('TRANSIT_TIME_UNCONFIRMED')
    if route.get('timing_breakdown',{}).get('status')=='inconsistent':return unknown('DURATION_TOTAL_MISMATCH')
    connections=route['connections']
    if len(departure.transfers)!=len(connections) or len(connections)!=len(transit)-1:return unknown('CONNECTIONS_UNCONFIRMED')
    try:
        board=departure.vehicle_arrival_at
        for index,(connection,check) in enumerate(zip(connections,departure.transfers)):
            if check.feasibility!='estimated_feasible' or str(check.connection_id)!=connection['connection_id'] or str(check.from_leg_id)!=transit[index]['leg_id'] or str(check.to_leg_id)!=transit[index+1]['leg_id']:
                return unknown('CONNECTIONS_UNCONFIRMED')
            from app.guidance.route_walks import adjusted_transfer
            walk=adjusted_transfer(connection,departure,profile['factor'])
            if walk is None:return unknown('TRANSFER_TIME_UNCONFIRMED')
            alight=board+timedelta(seconds=transit[index]['seconds']);minimum=alight+timedelta(seconds=walk+profile['transfer_buffer'])
            if check.transfer_walk_seconds!=walk or check.transfer_buffer_seconds!=profile['transfer_buffer'] or check.estimated_alighting_at!=alight or check.minimum_boarding_at!=minimum or check.next_boarding_at is None or check.next_boarding_at<minimum:
                return unknown('CONNECTION_TIMELINE_UNCONFIRMED')
            board=check.next_boarding_at
        alight=board+timedelta(seconds=transit[-1]['seconds'])
        if alight!=departure.estimated_final_alighting_at:return unknown('FINAL_ALIGHTING_UNCONFIRMED')
        from app.guidance.route_walks import egress_seconds
        base_egress=egress_seconds(route,departure)
        if base_egress is None:return unknown('EGRESS_TIME_UNCONFIRMED')
        egress=int((Decimal(base_egress)*Decimal(str(profile['factor']))).to_integral_value(rounding=ROUND_CEILING))
        arrival=alight+timedelta(seconds=egress)
        if arrival<at:return unknown('DESTINATION_TIME_UNCONFIRMED')
        result.status='estimated_meets' if arrival<=target else 'estimated_late'
        result.estimated_destination_arrival_at=arrival;result.margin_seconds=math.floor((target-arrival).total_seconds())
        result.egress_seconds=egress;result.timing_basis='provider_timeline';result.reasons=['PROVIDER_TIMELINE_ESTIMATE','PROVIDER_PERSONALIZED_EGRESS']
        if any(w.role=='egress' for w in departure.supplemental_walks):result.reasons.append('SUPPLEMENTAL_EGRESS_WALK')
        if route.get('timing_breakdown',{}).get('status')=='unallocated':result.reasons.append('PROVIDER_UNALLOCATED_TIME_NOT_USED')
        return result
    except (ArithmeticError,ValueError,TypeError,OverflowError):return unknown('DESTINATION_TIME_UNCONFIRMED')
