"""One public Seoul stop search; fixed official host, safe summaries only."""
import argparse
import json
import math
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from dotenv import dotenv_values
from check_kakao import NoRedirect
from check_public_arrivals import safe_code


def summarize(raw):
    root = ET.fromstring(raw)
    code = safe_code(root.findtext('.//headerCd') or root.findtext('.//returnReasonCode'))
    rows = [{node.tag: node.text for node in item} for item in root.findall('.//itemList')]
    def coordinates_valid(row):
        try:
            x, y = float(row['tmX']), float(row['tmY'])
            return math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90
        except (KeyError, TypeError, ValueError):
            return False
    return {'status': ('response_received' if rows else 'no_stations') if code in {'0', '00'} else 'provider_error',
            'provider_code': code, 'row_count': len(rows),
            'identity_fields_present': bool(rows) and all(
                all(row.get(field) not in (None, '') for field in ('stId', 'stNm', 'arsId')) for row in rows),
            'geographic_coordinate_ranges_valid': bool(rows) and all(coordinates_valid(row) for row in rows),
            'coordinate_reference_system_verified': False,
            'production_mapping_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-http', action='store_true', help='Explicit HTTP diagnostic on ws.bus.go.kr')
    args = parser.parse_args()
    key = dotenv_values(Path(__file__).resolve().parents[1] / '.env').get('DATA_GO_KR_SERVICE_KEY')
    if not key:
        print(json.dumps({'status': 'missing_key'}))
        return 1
    scheme = 'http' if args.official_http else 'https'
    params = {'serviceKey': urllib.parse.unquote(key), 'stSrch': '경성중고사거리'}
    url = scheme + '://ws.bus.go.kr/api/rest/stationinfo/getStationByName?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.build_opener(NoRedirect).open(url, timeout=20) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('response_too_large')
            result = summarize(raw)
            result.update({'http_status': response.status, 'transport': scheme})
            print(json.dumps(result))
            return 0 if result['status'] in {'response_received', 'no_stations'} else 1
    except urllib.error.HTTPError as error:
        print(json.dumps({'status': 'http_error', 'http_status': error.code}))
    except Exception as error:
        print(json.dumps({'status': 'request_or_parse_failed', 'exception_type': type(error).__name__}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
