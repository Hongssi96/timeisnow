"""Conservative GBIS mapping of in-memory first BUS evidence, fixed HTTPS only."""
from datetime import datetime,timezone
import json,os,time,urllib.request,urllib.parse,urllib.error
from uuid import UUID
from dotenv import dotenv_values
from app.common.database import ROOT
from app.common.http import NoRedirect
from app.common.errors import AuthError
from app.arrivals import provider
from app.arrivals.dto import Mapping
from app.arrivals.matching import boarding_candidates,station_route_scopes,match_route,scoped_matches,direction_candidate

OPERATIONS={
 'stations':('busstationservice','getBusStationListv2','busStationList'),
 'via':('busstationservice','getBusStationViaRouteListv2','busRouteList'),
 'stops':('busrouteservice','getBusRouteStationListv2','busRouteStationList'),
 'info':('busrouteservice','getBusRouteInfoItemv2','busRouteInfoItem')}

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
        return rows
    except TimeoutError: timeout()
    except urllib.error.URLError as error:
        if isinstance(error.reason,TimeoutError): timeout()
        raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보에 연결할 수 없어요.') from None
    except OSError: raise AuthError(503,'PROVIDER_UNAVAILABLE','교통 정보에 연결할 수 없어요.') from None
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError,RecursionError): provider.invalid()

def resolve(context,expires_at):
    deadline=time.monotonic()+5
    stops=context['stops'];points=context['points']
    stations=query('stations',{'keyword':stops[0]['name']},deadline)
    nearby=boarding_candidates(stops[0]['name'],points[0],stations,30)
    if nearby['status']!='station_candidates': return None
    via=[(sid,query('via',{'stationId':sid},deadline)) for sid in nearby['station_ids']]
    try: scopes=station_route_scopes(context['vehicle'],via)
    except ValueError: provider.invalid()
    ids=sorted({s['route_id'] for s in scopes})
    if not 1<=len(ids)<=2: return None
    routes=[(rid,query('stops',{'routeId':rid},deadline)) for rid in ids]
    result=scoped_matches(match_route(stops,points,routes,30,require_contiguous=True),scopes)
    if result['status']!='candidate_unique': return None
    match=result['matches'][0]
    info=query('info',{'routeId':match['route_id']},deadline)
    if len(info)!=1: return None
    direction=direction_candidate(match,dict(routes)[match['route_id']],info[0],match)
    if direction['status']!='direction_candidate': return None
    at=datetime.now(timezone.utc)
    if at>=expires_at: return None
    return Mapping(provider='gyeonggi-bus',first_leg_id=UUID(context['first_leg_id']),station_id=match['board_station_id'],
                   route_id=match['route_id'],sta_order=match['board_order'],route_dest_id=direction['route_dest_id'],
                   mapping_version='gbis.station-scope.v1.30m.contiguous',verified_at=at,valid_until=expires_at)
