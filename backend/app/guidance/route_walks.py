"""Owned routine walk gaps; official mapped endpoints and ephemeral seconds only."""
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
import time

from app.arrivals import cache, service as arrivals
from app.common.errors import AuthError
from app.guidance import access, walk_provider
from app.guidance.dto import SupplementalWalk

PROVIDER_ERRORS={'PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE','PROVIDER_RESPONSE_INVALID'}


def personalized(seconds,factor):
    return int((Decimal(seconds)*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))


def transfer_seconds(connection,departure):
    if connection['walking_seconds'] is not None:return connection['walking_seconds']
    if connection['walking_leg_ids']:return None
    matches=[w for w in departure.supplemental_walks if w.role=='transfer'
        and str(w.connection_id)==connection['connection_id']
        and str(w.from_leg_id)==connection['from_leg_id'] and str(w.to_leg_id)==connection['to_leg_id']
        and w.valid_until>=departure.calculated_at]
    return matches[0].provider_seconds if len(matches)==1 else None


def egress_seconds(route,departure):
    legs=route['ordered_legs'];last=next(l for l in reversed(legs) if l['type']!='WALKING')
    tail=legs[last['sequence']+1:]
    if tail:
        if 'EGRESS_WALK_MISSING' in route['missing_segments']:return None
        if any(l['type']!='WALKING' or l['walking_role']!='egress' or l['seconds']<=0 for l in tail):return None
        return sum(l['seconds'] for l in tail)
    if 'EGRESS_WALK_MISSING' not in route['missing_segments']:return None
    matches=[w for w in departure.supplemental_walks if w.role=='egress'
        and str(w.from_leg_id)==last['leg_id'] and w.connection_id is None and w.to_leg_id is None
        and w.valid_until>=departure.calculated_at]
    return matches[0].provider_seconds if len(matches)==1 else None


def get(user_id,search_id,candidate_id,route,snapshot,destination_ref,factor,deadline):
    root=cache.lookup(user_id,search_id,candidate_id,snapshot,arrivals.now())
    if root is None:return [],[]
    if not root.lock.acquire(blocking=False):
        raise AuthError(429,'RATE_LIMITED','도보 정보를 확인 중이에요.',{'Retry-After':'2'})
    try:
        def owned():
            row,_,_,fp=arrivals.owned(user_id,search_id,candidate_id)
            if fp!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요.')
            if len(row['place_refs'])!=2 or (row['place_refs'][1]['place_id'],row['place_refs'][1]['location_version'])!=destination_ref:
                raise AuthError(409,'VERSION_CONFLICT','도착 장소가 검색과 일치하지 않아요.')
            return row

        row=owned();expiry=min(row['expires_at'],root.expires_at)
        legs=route['ordered_legs'];by_id={l['leg_id']:l for l in legs}
        first=next(l for l in legs if l['type']!='WALKING')

        def endpoint(leg):
            if leg['type']!='BUS' or len(leg['vehicles'])!=1:return None
            entry=root if leg['leg_id']==first['leg_id'] else cache.following_entry(root,leg['leg_id'])
            if entry is None:return None
            # The root is already locked for the complete walk transaction.
            locked=entry is not root
            if locked and not entry.lock.acquire(blocking=False):
                raise AuthError(429,'RATE_LIMITED','연결 정보를 확인 중이에요.',{'Retry-After':'2'})
            try:
                at=arrivals.now()
                if entry.mapping is None:
                    if entry.mapping_attempted_at and at-entry.mapping_attempted_at<timedelta(seconds=60):return None
                    if deadline-time.monotonic()<3:return None
                    arrivals.reserve_refresh(user_id);entry.mapping_attempted_at=at
                    sink={}
                    value=arrivals.public_mapping.resolve(entry.context,expiry,deadline=deadline,boarding_endpoint=sink)
                    owned()
                    if value is None:return None
                    arrivals.checked_mapping(value,leg,arrivals.now())
                    entry.mapping=value;entry.boarding_endpoint=sink or None
                if entry.mapping.valid_until<=arrivals.now():return None
                value=arrivals.checked_mapping(entry.mapping,leg,arrivals.now())
                point=entry.boarding_endpoint
                if point is None or point.get('mapping_identity')!=cache.mapping_identity(value) or 'alighting_point' not in point:return None
                return point,min(expiry,value.valid_until)
            finally:
                if locked:entry.lock.release()

        requests=[]
        for connection in route['connections']:
            before=by_id[connection['from_leg_id']];after=by_id[connection['to_leg_id']]
            if connection['walking_seconds'] is None and not connection['walking_leg_ids'] and after['sequence']==before['sequence']+1:
                requests.append(('transfer',connection['connection_id'],before,after))
        last=next(l for l in reversed(legs) if l['type']!='WALKING')
        if last['sequence']==len(legs)-1 and 'EGRESS_WALK_MISSING' in route['missing_segments']:
            requests.append(('egress',None,last,None))
        successes=[];reasons=[]
        for role,identifier,before,after in requests[:3]:
            reason_prefix='TRANSFER_WALK' if role=='transfer' else 'EGRESS_WALK'
            key=identifier or 'egress';at=arrivals.now();identity=None
            try:
                start=endpoint(before)
                end=endpoint(after) if after else None
                if start is None or (after is not None and end is None):
                    reasons.append(reason_prefix+'_MAPPING_REQUIRED');continue
                destination=access.place(user_id,destination_ref) if after is None else None
                identity=(start[0]['mapping_identity'],end[0]['mapping_identity'] if end else destination_ref)
                valid_until=min(start[1],end[1] if end else expiry)
                same_stop=bool(end and start[0].get('alighting_station_id') and start[0].get('alighting_station_id')==end[0].get('station_id')
                    and start[0]['alighting_point']==end[0]['point'])
                source='same_stop' if same_stop else 'walking_route'
                cached=root.supplemental_walks.get(key)
                if cached and cached['identity']==identity and cached['fetched_at']<=at<=cached['valid_until']:
                    if cached['seconds'] is None and at-cached['fetched_at']<timedelta(seconds=60):
                        reasons.append(cached['reason']);continue
                    if cached['seconds'] is not None:
                        seconds=cached['seconds'];fetched=cached['fetched_at'];valid_until=min(valid_until,cached['valid_until'])
                    else:cached=None
                else:cached=None
                if cached is None:
                    if not same_stop and deadline-time.monotonic()<3:
                        reasons.append(reason_prefix+'_TIME_LIMIT');continue
                    if not same_stop:arrivals.reserve_refresh(user_id)
                    origin=start[0]['alighting_point']
                    finish=end[0]['point'] if end else (destination['longitude'],destination['latitude'])
                    seconds=0 if same_stop else walk_provider.fetch(origin,finish,deadline)
                    owned()
                    # Validate mapping identities and place coordinates again after external I/O.
                    latest_start=endpoint(before);latest_end=endpoint(after) if after else None
                    if latest_start is None or (after is not None and latest_end is None):
                        raise AuthError(409,'VERSION_CONFLICT','정류소 근거가 변경됐어요.')
                    latest_identity=(latest_start[0]['mapping_identity'],latest_end[0]['mapping_identity'] if latest_end else destination_ref)
                    if identity!=latest_identity:raise AuthError(409,'VERSION_CONFLICT','정류소 근거가 변경됐어요.')
                    if destination is not None:
                        latest_place=access.place(user_id,destination_ref)
                        if any(latest_place[k]!=destination[k] for k in ('latitude','longitude')):
                            raise AuthError(409,'VERSION_CONFLICT','도착 장소가 변경됐어요.')
                    fetched=arrivals.now();valid_until=min(valid_until,fetched+timedelta(seconds=300))
                    if time.monotonic()>deadline:seconds=None
                    if type(seconds) is not int or not (0 if same_stop else 1)<=seconds<=86400:seconds=None
                    root.supplemental_walks[key]={'identity':identity,'seconds':seconds,'fetched_at':fetched,
                        'valid_until':valid_until,'reason':reason_prefix+'_UNAVAILABLE'}
                if seconds is None or arrivals.now()>valid_until:
                    reasons.append(reason_prefix+'_UNAVAILABLE');continue
                successes.append(SupplementalWalk(role=role,connection_id=identifier,from_leg_id=before['leg_id'],
                    to_leg_id=after['leg_id'] if after else None,provider_seconds=seconds,
                    walking_seconds=personalized(seconds,factor),applied_duration_factor=factor,
                    source=source,fetched_at=fetched,valid_until=valid_until))
            except AuthError as error:
                if error.code not in PROVIDER_ERRORS:raise
                reason=reason_prefix+('_TIME_LIMIT' if error.code=='PROVIDER_TIMEOUT' else '_UNAVAILABLE')
                # Persist a bounded failure only when its endpoint identity was established.
                if identity is not None:
                    root.supplemental_walks[key]={'identity':identity,'seconds':None,'fetched_at':arrivals.now(),
                        'valid_until':expiry,'reason':reason}
                reasons.append(reason)
        owned()
        return successes,list(dict.fromkeys(reasons))
    finally:root.lock.release()
