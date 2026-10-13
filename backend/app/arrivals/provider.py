"""Fixed HTTPS GBIS adapter; no logging or guessed generation timestamp."""
import json,os,re,urllib.request,urllib.parse,urllib.error
from dotenv import dotenv_values
from app.common.database import ROOT
from app.common.http import NoRedirect
from app.common.errors import AuthError

def invalid():raise AuthError(502,'PROVIDER_RESPONSE_INVALID','도착 정보를 확인할 수 없어요.')

def numeric_id(value):
    if type(value) is int and value>=0:value=str(value)
    return value if isinstance(value,str) and re.fullmatch(r'[0-9]{1,20}',value) else None

def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError()
        result[key]=value
    return result

def reject_constant(value):raise ValueError()

def parse(raw,mapping):
    try:
        data=json.loads(raw,object_pairs_hook=unique_object,parse_constant=reject_constant);response=data['response'];code=str(response['msgHeader']['resultCode'])
        if code=='4':return []
        if code!='0':raise AuthError(503,'PROVIDER_UNAVAILABLE','도착 정보에 연결할 수 없어요.')
        body=response.get('msgBody') or {};rows=body.get('busArrivalItem') or []
        if isinstance(rows,dict):rows=[rows]
        if not isinstance(rows,list) or len(rows)>20 or any(not isinstance(row,dict) for row in rows):invalid()
        if not rows:return []
        expected=[mapping.station_id,mapping.route_id,str(mapping.sta_order),mapping.route_dest_id]
        matched=[row for row in rows if [numeric_id(row.get(key)) for key in ['stationId','routeId','staOrder','routeDestId']]==expected]
        if len(matched)!=1:invalid()
        row=matched[0]
        if row.get('flag')=='STOP':return []
        if row.get('flag')!='RUN':return None
        values=[];vehicles=set()
        for slot in (1,2):
            raw_seconds=row.get('predictTimeSec'+str(slot));vehicle=numeric_id(row.get('vehId'+str(slot)))
            seconds=int(raw_seconds) if type(raw_seconds) is int or isinstance(raw_seconds,str) and re.fullmatch(r'[0-9]{1,6}',raw_seconds) else None
            if seconds is None or not 0<seconds<=86400 or not vehicle or vehicle=='0':continue
            if vehicle in vehicles:invalid()
            vehicles.add(vehicle);values.append((vehicle,seconds))
        return values or None
    except (ValueError,TypeError,KeyError,UnicodeError,AttributeError,RecursionError):invalid()

def fetch(mapping):
    settings={**dotenv_values(ROOT/'.env'),**os.environ};key=settings.get('DATA_GO_KR_SERVICE_KEY')
    if not key:raise AuthError(503,'PROVIDER_UNAVAILABLE','도착 정보 설정을 확인해주세요.')
    params={'serviceKey':urllib.parse.unquote(key),'stationId':mapping.station_id,'routeId':mapping.route_id,'staOrder':str(mapping.sta_order),'format':'json'}
    url='https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2?'+urllib.parse.urlencode(params)
    try:
        with urllib.request.build_opener(NoRedirect).open(url,timeout=3) as response:
            raw=response.read(262145)
            if len(raw)>262144:invalid()
            return parse(raw,mapping)
    except TimeoutError:raise AuthError(504,'PROVIDER_TIMEOUT','도착 정보 응답이 늦어요.') from None
    except urllib.error.URLError as error:
        if isinstance(error.reason,TimeoutError):raise AuthError(504,'PROVIDER_TIMEOUT','도착 정보 응답이 늦어요.') from None
        raise AuthError(503,'PROVIDER_UNAVAILABLE','도착 정보에 연결할 수 없어요.') from None
    except OSError:raise AuthError(503,'PROVIDER_UNAVAILABLE','도착 정보에 연결할 수 없어요.') from None
