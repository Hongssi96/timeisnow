"""Fixed Kakao walking endpoint, ephemeral parsing; never persist geometry."""
import json,math,os,time,urllib.request,urllib.parse,urllib.error
from dotenv import dotenv_values
from app.common.database import ROOT
from app.common.http import NoRedirect
from app.common.errors import AuthError
from app.arrivals.provider import unique_object,reject_constant
from app.arrivals.matching import distance_meters

NO_ROUTE={'SAME_POINT','START_LINK_NOT_FOUND','END_LINK_NOT_FOUND','TOO_MANY_SEARCH_LINK','TOO_FAR_AWAY','ROUTE_RESULT_NOT_FOUND'}
def invalid():raise AuthError(502,'PROVIDER_RESPONSE_INVALID','접근 도보 경로를 확인할 수 없어요.')
def number(value,maximum):
    if type(value) is not int or not 0<=value<=maximum:invalid()
    return value

def parse(data,start,end):
    if not isinstance(data,dict):invalid()
    status=data.get('status')
    if isinstance(status,str) and status in NO_ROUTE:return None
    if status!='OK':invalid()
    try:
        route=data['route'];props=route['properties'];seconds=number(props['totalTime'],86400);meters=number(props['totalDistance'],100000)
        if seconds==0 or meters==0:return None
        legs=route['legs']
        if not isinstance(legs,list) or not 1<=len(legs)<=20:invalid()
        points=[];steps_count=0;leg_time=leg_distance=0
        for leg in legs:
            lp=leg['properties'];lt=number(lp['time'],86400);ld=number(lp['distance'],100000)
            leg_time+=lt;leg_distance+=ld;steps=leg['steps']
            if not isinstance(steps,list) or not steps:invalid()
            steps_count+=len(steps)
            if steps_count>500:invalid()
            st=sd=0
            for step in steps:
                sp=step['properties'];st+=number(sp['time'],86400);sd+=number(sp['distance'],100000)
                path=step['path']['points']
                if not isinstance(path,list) or not path or len(points)+len(path)>20000:invalid()
                for point in path:
                    if not isinstance(point,list) or len(point)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in point) or distance_meters(point,point) is None:invalid()
                if points and distance_meters(points[-1],path[0])>30:invalid()
                points.extend(path)
            if (st,sd)!=(lt,ld):invalid()
        if (leg_time,leg_distance)!=(seconds,meters):invalid()
        if distance_meters(start,points[0])>30 or distance_meters(end,points[-1])>30:invalid()
        return seconds
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):invalid()


def fetch(start,end,deadline):
    left=deadline-time.monotonic()
    if left<=0:raise AuthError(504,'PROVIDER_TIMEOUT','접근 도보 조회 시간이 지났어요.')
    key={**dotenv_values(ROOT/'.env'),**os.environ}.get('KAKAO_REST_API_KEY')
    if not key:raise AuthError(503,'PROVIDER_UNAVAILABLE','도보 경로 설정을 확인해주세요.')
    params={'start_x':start[0],'start_y':start[1],'end_x':end[0],'end_y':end[1],
        'input_coord':'WGS84','output_coord':'WGS84','route_mode':'SHORTEST'}
    request=urllib.request.Request('https://dapi.kakao.com/v2/routing/walk?'+urllib.parse.urlencode(params),headers={'Authorization':'KakaoAK '+key})
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=min(3,left)) as response:raw=response.read(1048577)
        if time.monotonic()>deadline:raise TimeoutError()
        if len(raw)>1048576:invalid()
        data=json.loads(raw,object_pairs_hook=unique_object,parse_constant=reject_constant)
        return parse(data,start,end)
    except urllib.error.HTTPError:raise AuthError(503,'PROVIDER_UNAVAILABLE','도보 경로에 연결할 수 없어요.') from None
    except (TimeoutError,urllib.error.URLError) as error:
        timed=isinstance(error,TimeoutError) or isinstance(getattr(error,'reason',None),TimeoutError)
        raise AuthError(504 if timed else 503,'PROVIDER_TIMEOUT' if timed else 'PROVIDER_UNAVAILABLE','도보 경로에 연결할 수 없어요.') from None
    except OSError:raise AuthError(503,'PROVIDER_UNAVAILABLE','도보 경로에 연결할 수 없어요.') from None
    except (ValueError,TypeError,UnicodeError,RecursionError):invalid()
