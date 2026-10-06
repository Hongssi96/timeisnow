"""Bounded endpoint/route intersection diagnostic, not full direction mapping."""
import argparse
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from dotenv import dotenv_values
from check_kakao import NoRedirect
from check_gyeonggi_mapping import fetch, ProbeError
from check_public_arrivals import safe_code
from route_mapping_probe import normalize_name, distance_meters


def candidates(rows, name, point, tolerance=100):
    result = {}
    for row in rows:
        distance = distance_meters(point, (row.get('tmX'), row.get('tmY')))
        if (normalize_name(row.get('stNm')) == normalize_name(name)
                and row.get('stId') and row.get('arsId') not in (None, '', '0', '00000')
                and distance is not None and distance <= tolerance):
            result[(row['stId'], row['arsId'])] = (row, distance)
    return list(result.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-http', action='store_true')
    args = parser.parse_args()
    settings = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
    kakao, key = settings.get('KAKAO_REST_API_KEY'), settings.get('DATA_GO_KR_SERVICE_KEY')
    if not kakao or not key:
        print(json.dumps({'status': 'missing_keys'}))
        return 1
    def seoul(operation, params):
        scheme = 'http' if args.official_http else 'https'
        url = scheme + '://ws.bus.go.kr/api/rest/stationinfo/' + operation + '?' + urllib.parse.urlencode(
            {**params, 'serviceKey': urllib.parse.unquote(key)})
        try:
            with urllib.request.build_opener(NoRedirect).open(url, timeout=20) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ProbeError(operation)
            root = ET.fromstring(raw)
            if root.findtext('.//headerCd') not in ('0', '00'):
                error = ProbeError(operation)
                error.provider_code = safe_code(root.findtext('.//headerCd'))
                raise error
            return [{node.tag: node.text for node in item} for item in root.findall('.//itemList')]
        except urllib.error.HTTPError as error:
            raise ProbeError(operation, error.code) from None
    try:
        params = {'start_x': '127.0276', 'start_y': '37.4979', 'end_x': '126.9726', 'end_y': '37.5547',
                  'input_coord': 'WGS84', 'output_coord': 'WGS84'}
        data = fetch('https://dapi.kakao.com/v2/routing/publictraffic?' + urllib.parse.urlencode(params),
                     'kakao_route', {'Authorization': 'KakaoAK ' + kakao})
        steps = [step for route in data.get('routes', [])
                 if route.get('properties', {}).get('type') == 'BUS' and route.get('properties', {}).get('transfers') == 0
                 for step in route.get('steps', []) if step.get('properties', {}).get('type') == 'BUS']
        if data.get('status') != 'OK' or not steps:
            raise ProbeError('no_direct_bus')
        step = steps[0]
        stops = step.get('properties', {}).get('stops') or []
        points = step.get('path', {}).get('points') or []
        vehicles = step.get('properties', {}).get('vehicles') or []
        if len(stops) < 2 or not points or not vehicles or not vehicles[0].get('name'):
            raise ProbeError('missing_kakao_fields')
        vehicle = normalize_name(vehicles[0]['name'])
        nearby = [seoul('getStationByPos', {'tmX': str(point[0]), 'tmY': str(point[1]), 'radius': '100'})
                  for point in (points[0], points[-1])]
        converted = [[{'stId': r.get('stationId'), 'stNm': r.get('stationNm'), 'arsId': r.get('arsId'),
                       'tmX': r.get('gpsX'), 'tmY': r.get('gpsY')} for r in group] for group in nearby]
        endpoints = [candidates(rows, stop['name'], point)
                     for rows, stop, point in zip(converted, (stops[0], stops[-1]), (points[0], points[-1]))]
        route_cache = {}
        for group in endpoints:
            if len(group) <= 3:
                for row, _ in group:
                    route_cache[row['arsId']] = seoul('getRouteByStation', {'arsId': row['arsId']})
        if any(not group or len(group) > 3 for group in endpoints):
            print(json.dumps({'status': 'endpoint_unresolved', 'candidate_counts': list(map(len, endpoints)),
                              'nearby_counts': list(map(len, nearby)), 'diagnostic_tolerance_meters': 100,
                              'verified_station_route_row_counts': [len(rows) for rows in route_cache.values()],
                              'production_mapping_validated': False}))
            return 1
        enriched = [[(row, distance, {r['busRouteId'] for r in route_cache[row['arsId']]
                                     if r.get('busRouteId') and vehicle in
                                     (normalize_name(r.get('busRouteNm')), normalize_name(r.get('busRouteAbrv')))})
                     for row, distance in group] for group in endpoints]
        matches = [(a, b, rid) for a in enriched[0] for b in enriched[1]
                   if a[0]['stId'] != b[0]['stId'] for rid in a[2] & b[2]]
        summary = {'status': 'endpoint_route_candidate_unique' if len(matches) == 1 else 'ambiguous' if matches else 'no_match',
                   'endpoint_candidate_counts': list(map(len, endpoints)), 'matched_pair_count': len(matches),
                   'diagnostic_tolerance_meters': 100, 'direction_validated': False,
                   'full_stop_order_validated': False, 'production_mapping_validated': False}
        if len(matches) == 1:
            summary.update({'board_distance_meters': round(matches[0][0][1], 2),
                            'alight_distance_meters': round(matches[0][1][1], 2)})
        print(json.dumps(summary))
        return 0 if len(matches) == 1 else 1
    except ProbeError as error:
        print(json.dumps({'status': 'probe_failed', 'stage': error.stage, 'http_status': error.code,
                          'provider_code': getattr(error, 'provider_code', None)}))
    except Exception as error:
        print(json.dumps({'status': 'probe_failed', 'exception_type': type(error).__name__}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
