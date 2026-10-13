"""Strict diagnostic matching, not an approved production mapping policy."""
import math
import unicodedata


def normalize_name(value):
    return "".join(unicodedata.normalize("NFKC", str(value or "")).split())


def distance_meters(a, b):
    try:
        ax, ay, bx, by = map(float, (*a, *b))
        if not all(math.isfinite(v) for v in (ax, ay, bx, by)):
            return None
        if not (-180 <= ax <= 180 and -180 <= bx <= 180 and -90 <= ay <= 90 and -90 <= by <= 90):
            return None
        lat1, lat2 = math.radians(ay), math.radians(by)
        dlat, dlon = lat2 - lat1, math.radians(bx - ax)
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))
    except (ValueError, TypeError):
        return None


def match_route(stops, points, routes, max_endpoint_meters):
    if type(max_endpoint_meters) not in (float, int) or not math.isfinite(max_endpoint_meters) or max_endpoint_meters <= 0:
        raise ValueError("Explicit diagnostic coordinate tolerance required")
    names = [normalize_name(stop.get("name")) for stop in stops]
    if len(names) < 2 or not all(names) or not points:
        return {"status": "insufficient_data", "matches": []}
    matches = []
    for route_id, supplied_rows in routes:
        try:
            rows = sorted(supplied_rows, key=lambda row: int(row["stationSeq"]))
            seqs = [int(row["stationSeq"]) for row in rows]
        except (KeyError, TypeError, ValueError):
            continue
        if len(set(seqs)) != len(seqs):
            continue
        normalized = [normalize_name(row.get("stationName")) for row in rows]
        for i, name in enumerate(normalized):
            if name != names[0]:
                continue
            for j in range(i + 1, len(rows)):
                if normalized[j] != names[-1]:
                    continue
                cursor = 0
                for observed in normalized[i:j + 1]:
                    if cursor < len(names) and observed == names[cursor]:
                        cursor += 1
                if cursor != len(names):
                    continue
                start_dist = distance_meters(points[0], (rows[i].get("x"), rows[i].get("y")))
                end_dist = distance_meters(points[-1], (rows[j].get("x"), rows[j].get("y")))
                if start_dist is None or end_dist is None or max(start_dist, end_dist) > max_endpoint_meters:
                    continue
                if not rows[i].get("stationId") or not rows[j].get("stationId"):
                    continue
                matches.append({"route_id": str(route_id), "board_station_id": str(rows[i]["stationId"]),
                                "board_order": seqs[i], "alight_station_id": str(rows[j]["stationId"]),
                                "alight_order": seqs[j], "start_distance_meters": round(start_dist, 2),
                                "end_distance_meters": round(end_dist, 2)})
    # Repeated station visits remain separate because their sequence is different.
    unique = {tuple(sorted(item.items())): item for item in matches}
    matches = list(unique.values())
    return {"status": "candidate_unique" if len(matches) == 1 else "ambiguous" if matches else "no_match",
            "matches": matches}


def direction_candidate(match, supplied_rows, route_info, scoped_direction=None):
    """Diagnostic direction: legacy hypothesis or authoritative station scope, never production approval."""
    import re

    def positive(value):
        if type(value) not in (int, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", str(value)):
            raise ValueError()
        return str(value)

    try:
        rid = positive(match['route_id'])
        if positive(route_info['routeId']) != rid:
            raise ValueError('ROUTE_ID_MISMATCH')
        rows = sorted(supplied_rows, key=lambda row: int(positive(row['stationSeq'])))
        seqs = [int(positive(row['stationSeq'])) for row in rows]
        if len(rows) < 3 or seqs != list(range(1, len(rows) + 1)):
            raise ValueError('STATION_SEQUENCE_INCOMPLETE')
        turns = {int(positive(row['turnSeq'])) for row in rows}
        if len(turns) != 1:
            raise ValueError('TURN_SEQUENCE_CONFLICT')
        turn = turns.pop()
        if not 1 < turn < len(rows):
            raise ValueError('TURN_SEQUENCE_OUT_OF_RANGE')
        marked = [int(positive(row['stationSeq'])) for row in rows if row.get('turnYn') == 'Y']
        if marked != [turn] or any(row.get('turnYn') not in ('Y', 'N') for row in rows):
            raise ValueError('TURN_MARKERS_UNCONFIRMED')
        start, end = positive(route_info['startStationId']), positive(route_info['endStationId'])
        if scoped_direction is None:
            if start == end or positive(rows[0]['stationId']) != start or positive(rows[-1]['stationId']) != start:
                raise ValueError('SIMPLE_RETURN_ENDPOINT_UNCONFIRMED')
            if positive(rows[turn - 1]['stationId']) != end or positive(route_info['turnStID']) != end:
                raise ValueError('TURN_DESTINATION_UNCONFIRMED')
        else:
            if start == end:
                raise ValueError('CIRCULAR_DIRECTION_UNCONFIRMED')
            if positive(route_info['turnStID']) != positive(rows[turn - 1]['stationId']):
                raise ValueError('TURN_DESTINATION_UNCONFIRMED')
            for key in ('route_id', 'board_station_id', 'board_order'):
                if positive(scoped_direction[key]) != positive(match[key]):
                    raise ValueError('STATION_ROUTE_IDENTITY_CONFLICT')
        board, alight = int(positive(match['board_order'])), int(positive(match['alight_order']))
        if not 1 <= board < alight <= len(rows):
            raise ValueError()
        if positive(rows[board - 1]['stationId']) != positive(match['board_station_id']):
            raise ValueError()
        if positive(rows[alight - 1]['stationId']) != positive(match['alight_station_id']):
            raise ValueError()
        if board < turn < alight or board == turn:
            return {'status': 'turnaround_unresolved', 'route_dest_id': None}
        if scoped_direction is None:
            destination = end if alight <= turn else start
            basis = 'simple_return_hypothesis'
        else:
            destination = positive(rows[turn - 1 if alight <= turn else -1]['stationId'])
            if positive(scoped_direction['route_dest_id']) != destination:
                raise ValueError('STATION_ROUTE_DESTINATION_CONFLICT')
            basis = 'station_route_scope'
        return {'status': 'direction_candidate', 'route_dest_id': destination, 'direction_basis': basis,
                'return_endpoint_matches_start': positive(rows[-1]['stationId']) == start}
    except (KeyError, ValueError, TypeError, IndexError, AttributeError) as error:
        safe_reasons = {'ROUTE_ID_MISMATCH', 'STATION_SEQUENCE_INCOMPLETE', 'TURN_SEQUENCE_CONFLICT',
                        'TURN_SEQUENCE_OUT_OF_RANGE', 'TURN_MARKERS_UNCONFIRMED',
                        'SIMPLE_RETURN_ENDPOINT_UNCONFIRMED', 'TURN_DESTINATION_UNCONFIRMED',
                        'CIRCULAR_DIRECTION_UNCONFIRMED', 'STATION_ROUTE_IDENTITY_CONFLICT',
                        'STATION_ROUTE_DESTINATION_CONFLICT'}
        reason = str(error) if isinstance(error, ValueError) and str(error) in safe_reasons else 'DIRECTION_FIELDS_UNCONFIRMED'
        return {'status': 'direction_unresolved', 'route_dest_id': None, 'reason': reason}


def arrival_direction_matches(match, direction, rows):
    """Only one exact identity row may corroborate the diagnostic direction."""
    if direction.get('status') != 'direction_candidate' or len(rows) != 1:
        return False
    row = rows[0]
    expected = {'stationId': match['board_station_id'], 'routeId': match['route_id'],
                'staOrder': str(match['board_order']), 'routeDestId': direction['route_dest_id']}
    return all(type(row.get(key)) in (int, str) and str(row[key]) == str(value)
               for key, value in expected.items())


def boarding_candidates(stop_name, point, rows, tolerance):
    """Keep every same-name nearby stop; never pick the nearest as proof."""
    import re
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Explicit diagnostic tolerance required')
    if not normalize_name(stop_name) or not isinstance(rows, list) or len(rows) > 2000:
        return {'status': 'station_unresolved', 'station_ids': []}
    stations = {}
    for row in rows:
        if not isinstance(row, dict):
            return {'status': 'station_unresolved', 'station_ids': []}
        if normalize_name(row.get('stationName')) != normalize_name(stop_name):
            continue
        sid = row.get('stationId')
        distance = distance_meters(point, (row.get('x'), row.get('y')))
        if type(sid) not in (int, str) or not re.fullmatch(r'[1-9][0-9]{0,19}', str(sid)) or distance is None:
            return {'status': 'station_unresolved', 'station_ids': []}
        identity = (float(row['x']), float(row['y']))
        if str(sid) in stations and stations[str(sid)][0] != identity:
            return {'status': 'station_unresolved', 'station_ids': []}
        stations[str(sid)] = (identity, distance)
    nearby = sorted(sid for sid, (_, distance) in stations.items() if distance <= tolerance)
    if not nearby or len(nearby) > 2:
        return {'status': 'station_disambiguation_required', 'station_ids': [], 'candidate_count': len(nearby)}
    return {'status': 'station_candidates', 'station_ids': nearby, 'candidate_count': len(nearby)}


def station_route_scopes(vehicle_name, station_routes):
    """Authoritative per-stop route order/destination, diagnostic use only."""
    import re
    def positive(value):
        if type(value) not in (int, str) or not re.fullmatch(r'[1-9][0-9]{0,19}', str(value)):
            raise ValueError('Invalid public identity')
        return str(value)
    if not normalize_name(vehicle_name):
        raise ValueError('Missing vehicle name')
    scopes = {}
    for sid, rows in station_routes:
        sid = positive(sid)
        if not isinstance(rows, list) or len(rows) > 2000:
            raise ValueError('Invalid route list')
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Invalid route row')
            if normalize_name(row.get('routeName')) != normalize_name(vehicle_name):
                continue
            rid, order, dest = positive(row.get('routeId')), int(positive(row.get('staOrder'))), positive(row.get('routeDestId'))
            if order > 1000:
                raise ValueError('Invalid station order')
            key = (sid, rid, order)
            if key in scopes and scopes[key]['route_dest_id'] != dest:
                raise ValueError('Conflicting direction')
            scopes[key] = {'board_station_id': sid, 'route_id': rid, 'board_order': order, 'route_dest_id': dest}
    return list(scopes.values())


def scoped_matches(result, scopes):
    matches = []
    for match in result['matches']:
        found = [s for s in scopes if all(match[key] == s[key]
                 for key in ('board_station_id', 'route_id', 'board_order'))]
        if len(found) == 1:
            matches.append(dict(match, route_dest_id=found[0]['route_dest_id']))
    return {'status': 'candidate_unique' if len(matches) == 1 else 'ambiguous' if matches else 'no_match',
            'matches': matches}
