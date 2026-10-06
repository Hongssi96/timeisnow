"""Bounded live public-route comparison; raw responses remain in memory only."""
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values
from check_kakao import NoRedirect
from route_mapping_probe import match_route, normalize_name


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


def main():
    settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    kakao_key, public_key = settings.get("KAKAO_REST_API_KEY"), settings.get("DATA_GO_KR_SERVICE_KEY")
    if not kakao_key or not public_key:
        print(json.dumps({"status": "missing_keys"}))
        return 1
    def gg(service, operation, params, field):
        query = {**params, "serviceKey": urllib.parse.unquote(public_key), "format": "json"}
        data = fetch("https://apis.data.go.kr/6410000/" + service + "/v2/" + operation + "?"
                     + urllib.parse.urlencode(query), operation).get("response", {})
        if str((data.get("msgHeader") or {}).get("resultCode")) != "0":
            raise ProbeError(operation)
        rows = (data.get("msgBody") or {}).get(field) or []
        return [rows] if isinstance(rows, dict) else rows
    try:
        params = {"start_x": "127.11119217", "start_y": "37.39477123",
                  "end_x": "127.12628814", "end_y": "37.41993056",
                  "input_coord": "WGS84", "output_coord": "WGS84"}
        data = fetch("https://dapi.kakao.com/v2/routing/publictraffic?" + urllib.parse.urlencode(params),
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
        candidates = gg("busrouteservice", "getBusRouteListv2", {"keyword": vehicle}, "busRouteList")
        candidates = {str(row["routeId"]): row for row in candidates
                      if row.get("routeId") and normalize_name(row.get("routeName")) == normalize_name(vehicle)}
        if len(candidates) > 6 or not candidates:
            print(json.dumps({"status": "route_disambiguation_required", "candidate_count": len(candidates)}))
            return 1
        routes = [(rid, gg("busrouteservice", "getBusRouteStationListv2", {"routeId": rid}, "busRouteStationList"))
                  for rid in candidates]
        result = match_route(props.get("stops") or [], step.get("path", {}).get("points") or [], routes, 100)
        summary = {"mapping_status": result["status"], "candidate_route_count": len(candidates),
                   "matched_pair_count": len(result["matches"]), "diagnostic_endpoint_tolerance_meters": 100,
                   "kakao_stop_count": len(props.get("stops") or []), "production_mapping_validated": False}
        if result["status"] == "candidate_unique":
            match = result["matches"][0]
            summary.update({"start_distance_meters": match["start_distance_meters"],
                            "end_distance_meters": match["end_distance_meters"],
                            "board_order": match["board_order"], "alight_order": match["alight_order"]})
            rows = gg("busarrivalservice", "getBusArrivalItemv2",
                      {"stationId": match["board_station_id"], "routeId": match["route_id"],
                       "staOrder": str(match["board_order"])}, "busArrivalItem")
            summary["arrival_rows"] = len(rows)
            summary["arrival_identity_matches"] = bool(rows) and all(
                str(row.get("stationId")) == match["board_station_id"]
                and str(row.get("routeId")) == match["route_id"]
                and str(row.get("staOrder")) == str(match["board_order"]) for row in rows)
        print(json.dumps(summary))
        return 0 if summary.get("arrival_identity_matches") else 1
    except ProbeError as error:
        print(json.dumps({"status": "probe_failed", "stage": error.stage, "http_status": error.code}))
    except Exception as error:
        print(json.dumps({"status": "probe_failed", "exception_type": type(error).__name__}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
