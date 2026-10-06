"""Two public-coordinate route probes; never persist raw provider responses."""
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values
from check_kakao import NoRedirect


def nonnegative_integer(value):
    return type(value) is int and value >= 0


def valid_step(step):
    props = step.get("properties", {})
    points = step.get("path", {}).get("points", [])
    return (nonnegative_integer(props.get("distance"))
            and nonnegative_integer(props.get("time")) and bool(points)
            and all(isinstance(pair, list) and len(pair) == 2
                    and all(type(v) in (float, int) and math.isfinite(v) for v in pair)
                    and -180 <= pair[0] <= 180 and -90 <= pair[1] <= 90
                    for pair in points))


def summarize(data, kind):
    statuses = {"OK", "SAME_POINT", "START_LINK_NOT_FOUND", "END_LINK_NOT_FOUND",
                "TOO_MANY_SEARCH_LINK", "TOO_FAR_AWAY", "ROUTE_RESULT_NOT_FOUND",
                "STARTNODES_NULL", "ENDNODES_NULL", "EQUAL_POINTS", "INVALID_REQUEST", "NO_RESULTS"}
    status = data.get("status")
    if status not in statuses:
        return {"status": "unexpected_provider_status"}
    if status != "OK":
        return {"status": "no_route", "provider_status": status}
    routes = [data.get("route", {})] if kind == "walk" else data.get("routes", [])
    valid = bool(routes)
    route_types = set()
    step_types = set()
    stop_keys = set()
    vehicle_keys = set()
    total_steps = 0
    summaries = []
    for route in routes:
        props = route.get("properties", {})
        valid &= (nonnegative_integer(props.get("totalTime"))
                  and nonnegative_integer(props.get("totalDistance")))
        if kind == "walk":
            legs = route.get("legs", [])
            valid &= bool(legs)
            for leg in legs:
                lp = leg.get("properties", {})
                valid &= nonnegative_integer(lp.get("time")) and nonnegative_integer(lp.get("distance"))
            steps = [step for leg in legs for step in leg.get("steps", [])]
        else:
            steps = route.get("steps", [])
            valid &= nonnegative_integer(props.get("transfers"))
            if props.get("type") in {"BUS", "SUBWAY", "BUS_AND_SUBWAY"}:
                route_types.add(props["type"])
            else:
                valid = False
        valid &= bool(steps) and all(valid_step(step) for step in steps)
        total_steps += len(steps)
        for step in steps:
            sp = step.get("properties", {})
            if kind != "walk":
                if sp.get("type") in {"BUS", "SUBWAY", "WALKING"}:
                    step_types.add(sp["type"])
                else:
                    valid = False
            for stop in sp.get("stops", []):
                stop_keys.update(stop.keys())
            for vehicle in sp.get("vehicles", []):
                vehicle_keys.update(vehicle.keys())
        summaries.append({"seconds": props.get("totalTime"), "meters": props.get("totalDistance"),
                          "transfers": props.get("transfers") if kind != "walk" else None})
    # Only field-presence flags, never raw identifiers/names or provider payloads.
    public_ids = {"stId", "stationId", "busRouteId", "routeId", "arsId", "staOrd"}
    return {"status": "ok" if valid else "schema_validation_failed", "provider_status": "OK",
            "route_count": len(routes), "steps_count": total_steps,
            "route_types": sorted(route_types), "step_types": sorted(step_types),
            "first_route_summary": summaries[0] if summaries else None,
            "time_distance_coordinate_schema_valid": bool(valid),
            "stop_name_present": "name" in stop_keys,
            "vehicle_name_present": "name" in vehicle_keys,
            "public_id_fields_present": bool(public_ids & (stop_keys | vehicle_keys))}


def main():
    key = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get("KAKAO_REST_API_KEY")
    if not key:
        print(json.dumps({"status": "missing_rest_key"}))
        return 1
    # Approximate public station surroundings, not confirmed entrances/platforms.
    cases = [("walk", "gangnam_to_yeoksam", "127.0365", "37.5006"),
             ("publictraffic", "gangnam_to_seoul_station", "126.9726", "37.5547")]
    passed = True
    for kind, case, end_x, end_y in cases:
        params = {"start_x": "127.0276", "start_y": "37.4979", "end_x": end_x,
                  "end_y": end_y, "input_coord": "WGS84", "output_coord": "WGS84"}
        request = urllib.request.Request("https://dapi.kakao.com/v2/routing/" + kind + "?"
                                         + urllib.parse.urlencode(params),
                                         headers={"Authorization": "KakaoAK " + key})
        started = time.monotonic()
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=35) as response:
                result = summarize(json.load(response), kind)
                result["http_status"] = response.status
        except urllib.error.HTTPError as error:
            try:
                code = json.load(error).get("code")
            except Exception:
                code = None
            result = {"status": "http_error", "http_status": error.code,
                      "provider_error_code": code if type(code) is int else None}
        except Exception as error:
            result = {"status": "connection_error", "exception_type": type(error).__name__}
        result.update({"case": case, "endpoint": kind,
                       "elapsed_seconds": round(time.monotonic() - started, 2)})
        print(json.dumps(result))
        passed &= result["status"] == "ok"
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
