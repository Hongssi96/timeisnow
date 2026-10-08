"""Kakao place search adapter. Never log queries, coordinates or provider payloads."""
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


def provider_search(kind, query, key):
    url = 'https://dapi.kakao.com/v2/local/search/' + kind + '.json?'
    return provider_documents(url, {'query': query, 'size': 10}, key)


def provider_documents(url, params, key):
    request = urllib.request.Request(url + urllib.parse.urlencode(params),
                                     headers={'Authorization': 'KakaoAK ' + key})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=3) as response:
            # Bound provider data even when the upstream response is unexpected.
            raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError()
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('documents'), list):
                raise ValueError()
            return data['documents']
    except (ValueError, TypeError, UnicodeError):
        raise AuthError(502, 'PROVIDER_RESPONSE_INVALID', '검색 결과를 확인할 수 없어요.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '장소 검색에 연결할 수 없어요.') from None


def rest_key():
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    return values.get('KAKAO_REST_API_KEY')


def javascript_key():
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    return values.get('KAKAO_JAVASCRIPT_KEY')


def region_for_location(location):
    key = rest_key()
    if not key:
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '선택한 위치를 확인할 수 없어요.')
    documents = provider_documents('https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?',
        {'x': location.longitude, 'y': location.latitude, 'input_coord': 'WGS84'}, key)
    try:
        for document in documents:
            if not isinstance(document, dict) or document.get('region_type') not in ('B', 'H'):
                raise ValueError()
            if document['region_type'] != 'B':
                continue
            region, address = document['region_1depth_name'], document['address_name']
            if not isinstance(region, str) or not isinstance(address, str) or not address:
                raise ValueError()
            if region in ('서울', '서울특별시', '경기', '경기도'):
                return address
    except (ValueError, KeyError, TypeError):
        raise AuthError(502, 'PROVIDER_RESPONSE_INVALID', '선택한 위치를 확인할 수 없어요.') from None
    raise AuthError(422, 'UNSUPPORTED_REGION', '서울·경기 안에서 위치를 선택해주세요.')


def search_candidates(query):
    key = rest_key()
    if not key:
        raise AuthError(503, 'PROVIDER_UNAVAILABLE', '장소 검색에 연결할 수 없어요.')
    candidates, seen = [], set()
    for kind in ('address', 'keyword'):
        for doc in provider_search(kind, query, key):
            try:
                address = doc['address_name']
                lat, lon = float(doc['y']), float(doc['x'])
                if (not isinstance(address, str) or not address or not math.isfinite(lat)
                        or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180):
                    raise ValueError()
                # Administrative address from the provider, not a guessed bounding box.
                if address.split()[0] not in ('서울', '서울특별시', '경기', '경기도'):
                    continue
                road = doc.get('road_address') or {}
                name = doc.get('place_name') or road.get('building_name') or address
                if not isinstance(name, str) or not name:
                    raise ValueError()
                identity = (address, lat, lon)
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append({'candidate_id': str(uuid4()), 'name': name, 'address': address,
                                   'location': {'latitude': lat, 'longitude': lon}})
            except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                raise AuthError(502, 'PROVIDER_RESPONSE_INVALID', '검색 결과를 확인할 수 없어요.') from None
    return candidates[:20]
