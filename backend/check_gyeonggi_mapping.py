"""Bounded live public-route comparison; raw responses remain in memory only."""
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values
from check_kakao import NoRedirect
from route_mapping_probe import (match_route, direction_candidate, arrival_direction_matches,
                                 boarding_candidates, station_route_scopes, scoped_matches)


class ProbeError(Exception):
    def __init__(self, stage, code=None):
        self.stage, self.code = stage, code


def fetch(url, stage, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProbeError(stage)
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        raise ProbeError(stage, error.code) from None
    except (ValueError, OSError):
        raise ProbeError(stage) from None


def main(max_requests=10):
    if type(max_requests) is not int or not 1 <= max_requests <= 10:
        raise ValueError("Request budget must be 1 to 10")
    settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    kakao_key, public_key = settings.get("KAKAO_REST_API_KEY"), settings.get("DATA_GO_KR_SERVICE_KEY")
    if not kakao_key or not public_key:
        print(json.dumps({"status": "missing_keys"}))
        return 1
    query_time_present = [False]
    calls = [0]
    def bounded_fetch(url, stage, headers=None):
        if calls[0] >= max_requests:
            raise ProbeError('request_budget_exhausted')
        calls[0] += 1
        return fetch(url, stage, headers)
    def gg(service, operation, params, field):
        query = {**params, "serviceKey": urllib.parse.unquote(public_key), "format": "json"}
        data = bounded_fetch("https://apis.data.go.kr/6410000/" + service + "/v2/" + operation + "?"
                     + urllib.parse.urlencode(query), operation).get("response", {})
        code = str((data.get("msgHeader") or {}).get("resultCode"))
        if code == "4":
            return []
        if code != "0":
            raise ProbeError(operation)
        if operation == "getBusArrivalItemv2":
            query_time_present[0] = bool((data.get("msgHeader") or {}).get("queryTime"))
        rows = (data.get("msgBody") or {}).get(field) or []
        rows = [rows] if isinstance(rows, dict) else rows
        if not isinstance(rows, list) or len(rows) > 2000 or any(not isinstance(row, dict) for row in rows):
            raise ProbeError(operation)
        return rows
    try:
        params = {"start_x": "127.11119217", "start_y": "37.39477123",
                  "end_x": "127.12628814", "end_y": "37.41993056",
                  "input_coord": "WGS84", "output_coord": "WGS84"}
        data = bounded_fetch("https://dapi.kakao.com/v2/routing/publictraffic?" + urllib.parse.urlencode(params),
                     "kakao_route", {"Authorization": "KakaoAK " + kakao_key})
        steps = [step for route in data.get("routes", [])
                 if route.get("properties", {}).get("type") == "BUS" and route.get("properties", {}).get("transfers") == 0
                 for step in route.get("steps", [])
                 if step.get("properties", {}).get("type") == "BUS"]
        if data.get("status") != "OK" or not steps:
            raise ProbeError("kakao_bus_candidate")
        step = steps[0]
        props = step.get("properties", {})
        vehicles = props.get("vehicles") or []
        if not vehicles or not vehicles[0].get("name"):
            raise ProbeError("vehicle_missing")
        vehicle = vehicles[0]["name"]
        stops, points = props.get("stops") or [], step.get("path", {}).get("points") or []
        if len(stops) < 2 or not points:
            raise ProbeError("boarding_geometry_missing")
        stations = gg("busstationservice", "getBusStationListv2",
                      {"keyword": stops[0].get("name")}, "busStationList")
        selection = boarding_candidates(stops[0].get("name"), points[0], stations, 100)
        if selection["status"] != "station_candidates":
            print(json.dumps({"status": selection["status"], "candidate_count": selection.get("candidate_count"),
                              "request_count": calls[0], "production_mapping_validated": False}))
            return 1
        via = [(sid, gg("busstationservice", "getBusStationViaRouteListv2",
                       {"stationId": sid}, "busRouteList")) for sid in selection["station_ids"]]
        scopes = station_route_scopes(vehicle, via)
        route_ids = sorted({scope["route_id"] for scope in scopes})
        # Reserve one route-info and one arrival request; no partial candidate sampling.
        if not route_ids or len(route_ids) > max_requests - calls[0] - 2:
            print(json.dumps({"status": "route_disambiguation_required", "candidate_count": len(route_ids),
                              "request_count": calls[0], "production_mapping_validated": False}))
            return 1
        routes = [(rid, gg("busrouteservice", "getBusRouteStationListv2",
                          {"routeId": rid}, "busRouteStationList")) for rid in route_ids]
        result = scoped_matches(match_route(stops, points, routes, 100), scopes)
        summary = {"mapping_status": result["status"], "candidate_route_count": len(route_ids),
                   "boarding_station_count": selection["candidate_count"], "matched_pair_count": len(result["matches"]),
                   "diagnostic_endpoint_tolerance_meters": 100, "kakao_stop_count": len(stops),
                   "production_mapping_validated": False}
        if result["status"] == "candidate_unique":
            match = result["matches"][0]
            summary.update({"start_distance_meters": match["start_distance_meters"],
                            "end_distance_meters": match["end_distance_meters"],
                            "board_order": match["board_order"], "alight_order": match["alight_order"]})
            info = gg("busrouteservice", "getBusRouteInfoItemv2",
                      {"routeId": match["route_id"]}, "busRouteInfoItem")
            route_rows = dict(routes)[match["route_id"]]
            direction = direction_candidate(match, route_rows, info[0] if len(info) == 1 else {})
            if direction['status'] == 'direction_candidate' and direction['route_dest_id'] != match['route_dest_id']:
                direction = {'status': 'direction_unresolved', 'route_dest_id': None,
                             'reason': 'STATION_ROUTE_DESTINATION_CONFLICT'}
            summary["direction_status"] = direction["status"]
            summary["direction_reason"] = direction.get("reason")
            rows = gg("busarrivalservice", "getBusArrivalItemv2",
                      {"stationId": match["board_station_id"], "routeId": match["route_id"],
                       "staOrder": str(match["board_order"])}, "busArrivalItem")
            summary["arrival_rows"] = len(rows)
            summary["arrival_identity_matches"] = bool(rows) and all(
                str(row.get("stationId")) == match["board_station_id"]
                and str(row.get("routeId")) == match["route_id"]
                and str(row.get("staOrder")) == str(match["board_order"]) for row in rows)
            summary["arrival_direction_matches"] = arrival_direction_matches(match, direction, rows)
            summary["query_time_present"] = query_time_present[0]
            summary["verified_generation_time_available"] = False
            summary["valid_for_guidance"] = False
        summary["request_count"] = calls[0]
        print(json.dumps(summary))
        return 0 if summary.get("arrival_identity_matches") and summary.get("arrival_direction_matches") else 1
    except ProbeError as error:
        print(json.dumps({"status": "probe_failed", "stage": error.stage, "http_status": error.code, "request_count": calls[0]}))
    except Exception as error:
        print(json.dumps({"status": "probe_failed", "exception_type": type(error).__name__, "request_count": calls[0]}))
    return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bounded public-route diagnostic")
    parser.add_argument("--max-requests", type=int, choices=range(1, 11), default=10)
    raise SystemExit(main(parser.parse_args().max_requests))
