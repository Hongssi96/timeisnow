"""Kakao transit adapter. Persist only normalized, coordinate-free candidates."""
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from dotenv import dotenv_values

from app.common.database import ROOT
from app.common.errors import AuthError
from app.common.http import NoRedirect
from app.journeys.models import common_candidate


def invalid():
    raise AuthError(502, 'PROVIDER_RESPONSE_INVALID', '경로 응답을 확인할 수 없어요.')


def fetch_routes(origin, destination):
    key = {**dotenv_values(ROOT / '.env'), **os.environ}.get('KAKAO_REST_API_KEY')
    if not key:
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '경로 서비스에 연결할 수 없어요.')
    params = {'start_x':origin.longitude,'start_y':origin.latitude,
              'end_x':destination.longitude,'end_y':destination.latitude,
              'input_coord':'WGS84','output_coord':'WGS84'}
    request = urllib.request.Request('https://dapi.kakao.com/v2/routing/publictraffic?' + urllib.parse.urlencode(params),
        headers={'Authorization':'KakaoAK ' + key})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
            raw = response.read(2097153)
            if len(raw) > 2097152:
                invalid()
            return json.loads(raw)
    except urllib.error.HTTPError:
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '경로 서비스에 연결할 수 없어요.') from None
    except (TimeoutError, urllib.error.URLError) as error:
        timed_out = isinstance(error, TimeoutError) or isinstance(getattr(error, 'reason', None), TimeoutError)
        raise AuthError(504 if timed_out else 503, 'PROVIDER_TIMEOUT' if timed_out else 'PROVIDER_UNAVAILABLE',
                             '경로 서비스 응답을 기다릴 수 없어요.') from None
    except OSError:
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '경로 서비스에 연결할 수 없어요.') from None
    except (ValueError, TypeError, UnicodeError):
        invalid()


def number(value):
    if type(value) is not int or value < 0:
        invalid()
    return value


def names(values):
    if not isinstance(values, list) or len(values) > 500:
        invalid()
    result = []
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not 1 <= len(item['name']) <= 200:
            invalid()
        result.append(item['name'])
    return result


def normalize(data, preference, *, mapping_contexts=None):
    if mapping_contexts is not None: mapping_contexts.clear()
    if not isinstance(data, dict):
        invalid()
    status = data.get('status')
    if status in ('NO_RESULTS', 'EQUAL_POINTS'):
        return [], ['NO_ROUTE']
    if status in ('STARTNODES_NULL', 'ENDNODES_NULL'):
        return [], ['ENDPOINT_UNRESOLVED']
    if status != 'OK' or not isinstance(data.get('routes'), list) or len(data['routes']) > 100:
        invalid()
    candidates, reasons = [], []
    missing = ['LIVE_ARRIVALS_PENDING','AI_WALK_PENDING','ENTRANCE_PLATFORM_UNCONFIRMED','REGION_PATH_UNVERIFIED']
    for route in data['routes']:
        if not isinstance(route, dict) or not isinstance(route.get('properties'), dict):
            invalid()
        props = route['properties']
        if props.get('type') not in ('BUS','SUBWAY','BUS_AND_SUBWAY'):
            invalid()
        seconds, meters, transfers = (number(props.get(key)) for key in ('totalTime','totalDistance','transfers'))
        steps = route.get('steps')
        if not isinstance(steps, list) or not 1 <= len(steps) <= 500:
            invalid()
        legs, walking, vehicle_options, bus_contexts = [], 0, {}, {}
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or not isinstance(step.get('properties'), dict):
                invalid()
            sp = step['properties']; kind = sp.get('type')
            if kind not in ('WALKING','BUS','SUBWAY'):
                invalid()
            leg_seconds, leg_meters = number(sp.get('time')), number(sp.get('distance'))
            # Validate geometry before discarding it, never store endpoint/device points.
            path = step.get('path')
            points = path.get('points') if isinstance(path, dict) else None
            if not isinstance(points, list) or not 1 <= len(points) <= 20000:
                invalid()
            for point in points:
                if (not isinstance(point, list) or len(point) != 2
                    or any(type(v) not in (int,float) or not math.isfinite(v) for v in point)
                    or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90):
                    invalid()
            stops = names(sp.get('stops', [])) if kind != 'WALKING' else []
            vehicles = names(sp.get('vehicles', [])) if kind != 'WALKING' else []
            if kind != 'WALKING' and (len(stops) < 2 or not vehicles):
                invalid()
            if kind == 'WALKING': walking += leg_seconds
            leg_id = str(uuid4())
            if kind == 'BUS' and len(vehicles)==1:
                bus_contexts[leg_id]={'first_leg_id':leg_id,'stops':[{'name':n} for n in stops],
                                      'points':[points[0][:],points[-1][:]],'vehicle':vehicles[0]}
            if kind != 'WALKING':
                vehicle_options[leg_id] = [{'name':item['name'],'provider_type':item.get('type')} for item in sp['vehicles']]
            legs.append({'leg_id':leg_id,'sequence':index,'type':kind,'seconds':leg_seconds,
                         'distance_meters':leg_meters,'stops':stops,'vehicles':vehicles,'time_source':'provider_estimate'})
        if not any(leg['type'] != 'WALKING' for leg in legs):
            invalid()
        if transfers > 2 or sum(leg['type'] != 'WALKING' for leg in legs) > 3:
            reasons.append('TRANSFER_LIMIT'); continue
        candidates.append(common_candidate({'candidate_id':str(uuid4()),'type':props['type'],'validity':'insufficient_data',
            'ordered_legs':legs,'transfer_count':transfers,'total_seconds':seconds,'total_distance_meters':meters,
            'walking_seconds':walking,'estimated_arrival_at':None,'time_sources':['provider_estimate'],
            'missing_segments':missing[:]},vehicle_options))
        first=next(leg for leg in legs if leg['type']!='WALKING')
        if mapping_contexts is not None and first['leg_id'] in bus_contexts:
            context=bus_contexts[first['leg_id']]
            following=[bus_contexts[leg['leg_id']] for leg in legs if leg['type']=='BUS' and leg['leg_id']!=first['leg_id'] and leg['leg_id'] in bus_contexts]
            mapping_contexts[candidates[-1]['candidate_id']]=dict(context,following=following) if following else context
    candidates.sort(key=lambda c: ((c['transfer_count'] if preference == 'fewer_transfers' else c['walking_seconds'] if preference == 'less_walking' else c['total_seconds']), c['total_seconds'],c['transfer_count'],c['walking_seconds']))
    candidates = candidates[:20]
    if mapping_contexts is not None:
        kept={c['candidate_id'] for c in candidates}
        for identifier in list(mapping_contexts):
            if identifier not in kept: del mapping_contexts[identifier]
    if not candidates and not reasons:
        reasons.append('NO_ROUTE')
    return candidates, list(dict.fromkeys(reasons + [reason for candidate in candidates for reason in candidate['missing_segments']]))
