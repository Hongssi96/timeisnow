"""Conservative GBIS mapping of in-memory first BUS evidence, fixed HTTPS only."""
from datetime import datetime,timezone
import json,os,time,urllib.request,urllib.parse,urllib.error
from uuid import UUID
from dotenv import dotenv_values
from app.common.database import ROOT
from app.common.http import NoRedirect
from app.common.errors import AuthError
from app.arrivals import provider,cache
from app.arrivals.dto import Mapping
from app.arrivals.matching import boarding_candidates,station_route_scopes,match_route,scoped_matches,direction_candidate,diagnose_match

OPERATIONS={
 'stations':('busstationservice','getBusStationListv2','busStationList'),
 'via':('busstationservice','getBusStationViaRouteListv2','busRouteList'),
 'stops':('busrouteservice','getBusRouteStationListv2','busRouteStationList'),
 'info':('busrouteservice','getBusRouteInfoItemv2','busRouteInfoItem'),
 'locations':('buslocationservice','getBusLocationListv2','busLocationList')}

PUBLIC_FAILURE_REASONS=frozenset({
    'STATION_CANDIDATES_UNCONFIRMED','NO_ROUTE_AT_BOARDING_STOP','ROUTE_CANDIDATE_LIMIT',
    'VISIT_CANDIDATE_LIMIT','ROUTE_SEQUENCE_UNCONFIRMED','ROUTE_MATCH_AMBIGUOUS',
    'ROUTE_INFO_UNCONFIRMED','TURNAROUND_UNCONFIRMED','DIRECTION_MATCH_AMBIGUOUS'})

def safe_failure_reason(diagnostics):
    reason=diagnostics.get('reason')
    return reason if isinstance(reason,str) and reason in PUBLIC_FAILURE_REASONS else None

def timeout(): raise AuthError(504,'PROVIDER_TIMEOUT','교통 정보 응답이 늦어요.')

def query(kind,params,deadline):
    left=deadline-time.monotonic()
    if left<=0: timeout()
    key={**dotenv_values(ROOT/'.env'),**os.environ}.get('DATA_GO_KR_SERVICE_KEY')
    if not key: raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보 설정을 확인해주세요.')
    service,operation,field=OPERATIONS[kind]
    values={**params,'serviceKey':urllib.parse.unquote(key),'format':'json'}
    url='https://apis.data.go.kr/6410000/'+service+'/v2/'+operation+'?'+urllib.parse.urlencode(values)
    try:
        with urllib.request.build_opener(NoRedirect).open(url,timeout=min(3,left)) as response:
            raw=response.read(1048577)
        if time.monotonic()>deadline: timeout()
        if len(raw)>1048576: provider.invalid()
        data=json.loads(raw,object_pairs_hook=provider.unique_object,parse_constant=provider.reject_constant)['response']
        code=str(data['msgHeader']['resultCode'])
        if code=='4': return []
        if code!='0': raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보에 연결할 수 없어요.')
        rows=(data.get('msgBody') or {}).get(field) or []
        if isinstance(rows,dict): rows=[rows]
        if not isinstance(rows,list) or len(rows)>2000 or any(not isinstance(r,dict) for r in rows): provider.invalid()
        if kind=='info' and not rows:provider.invalid()
        return rows
    except TimeoutError: timeout()
    except urllib.error.URLError as error:
        if isinstance(error.reason,TimeoutError): timeout()
        raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보에 연결할 수 없어요.') from None
    except OSError: raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보에 연결할 수 없어요.') from None
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError,RecursionError): provider.invalid()

def resolve(context,expires_at,*,diagnostics=None,deadline=None,boarding_endpoint=None):
    def record(**values):
        if diagnostics is not None:diagnostics.update(values)
    if diagnostics is not None:diagnostics.clear()
    if boarding_endpoint is not None:boarding_endpoint.clear()
    record(stage='station_search',reason='MAPPING_PENDING')
    deadline=min(time.monotonic()+5,deadline) if deadline is not None else time.monotonic()+5
    stops=context['stops'];points=context['points']
    stations=query('stations',{'keyword':stops[0]['name']},deadline)
    nearby=boarding_candidates(stops[0]['name'],points[0],stations,30)
    record(station_count=nearby.get('candidate_count',0))
    if nearby['status']!='station_candidates':
        record(reason='STATION_CANDIDATES_UNCONFIRMED');return None
    record(stage='station_routes')
    via=[(sid,query('via',{'stationId':sid},deadline)) for sid in nearby['station_ids']]
    try: scopes=station_route_scopes(context['vehicle'],via)
    except ValueError: provider.invalid()
    ids=sorted({s['route_id'] for s in scopes})
    record(route_count=len(ids))
    if not ids:
        record(reason='NO_ROUTE_AT_BOARDING_STOP');return None
    if len(ids)>2:
        record(reason='ROUTE_CANDIDATE_LIMIT');return None
    record(stage='route_stations')
    routes=[(rid,query('stops',{'routeId':rid},deadline)) for rid in ids]
    raw=match_route(stops,points,routes,30,max_matches=32)
    if raw['status']=='candidate_limit':
        record(reason='VISIT_CANDIDATE_LIMIT');return None
    result=scoped_matches(raw,scopes)
    record(matched_count=len(result['matches']))
    if not result['matches']:
        if diagnostics is not None:record(match_checks=diagnose_match(stops,points,routes,scopes,30,require_contiguous=False))
        record(reason='ROUTE_SEQUENCE_UNCONFIRMED');return None
    route_ids={match['route_id'] for match in result['matches']}
    if len(route_ids)!=1:
        record(reason='ROUTE_MATCH_AMBIGUOUS');return None
    record(stage='route_info')
    rid=next(iter(route_ids))
    info=query('info',{'routeId':rid},deadline)
    if len(info)>1:
        record(reason='ROUTE_INFO_UNCONFIRMED');return None
    verified=[]
    for match in result['matches']:
        direction=direction_candidate(match,dict(routes)[rid],info[0] if info else None,match)
        if direction['status']=='direction_candidate':
            verified.append((match,direction))
    if len(verified)!=1:
        record(reason='DIRECTION_MATCH_AMBIGUOUS' if verified else 'TURNAROUND_UNCONFIRMED');return None
    match,direction=verified[0]
    at=datetime.now(timezone.utc)
    if at>=expires_at:
        record(reason='SEARCH_EXPIRED');return None
    record(stage='complete',reason='MAPPING_CONFIRMED')
    value=Mapping(provider='gyeonggi-bus',first_leg_id=UUID(context['first_leg_id']),station_id=match['board_station_id'],
                   route_id=match['route_id'],sta_order=match['board_order'],route_dest_id=direction['route_dest_id'],
                   mapping_version='gbis.station-scope.v3.30m.ordered',verified_at=at,valid_until=expires_at)
    if boarding_endpoint is not None:
        row=next(row for row in dict(routes)[rid] if str(row['stationId'])==value.station_id and int(row['stationSeq'])==value.sta_order)
        alight=next(row for row in dict(routes)[rid] if str(row['stationId'])==match['alight_station_id'] and int(row['stationSeq'])==match['alight_order'])
        boarding_endpoint.update(point=(float(row['x']),float(row['y'])),alighting_point=(float(alight['x']),float(alight['y'])),
            station_id=value.station_id,alighting_station_id=match['alight_station_id'],alighting_order=match['alight_order'],mapping_identity=cache.mapping_identity(value))
    return value
