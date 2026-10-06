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
