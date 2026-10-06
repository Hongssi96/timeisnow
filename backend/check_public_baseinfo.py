"""Verify Gyeonggi base-data permissions and timestamp roles over HTTPS."""
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from dotenv import dotenv_values
from check_kakao import NoRedirect

CASES = (
    ("station_search", "busstationservice", "getBusStationListv2", {"keyword": "판교역동편"}, "busStationList"),
    ("station_routes", "busstationservice", "getBusStationViaRouteListv2", {"stationId": "200000177"}, "busRouteList"),
    ("route_stations", "busrouteservice", "getBusRouteStationListv2", {"routeId": "200000037"}, "busRouteStationList"),
)


def query_time_parseable(value):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y%m%d%H%M%S"):
        try:
            datetime.strptime(str(value), fmt)
            return True
        except ValueError:
            pass
    return False


def main():
    key = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get("DATA_GO_KR_SERVICE_KEY")
    if not key:
        print(json.dumps({"status": "missing_key"}))
        return 1
    passed = True
    for label, service, operation, supplied, field in CASES:
        params = {**supplied, "serviceKey": urllib.parse.unquote(key), "format": "json"}
        url = "https://apis.data.go.kr/6410000/" + service + "/v2/" + operation + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.build_opener(NoRedirect).open(url, timeout=20) as response:
                data = json.load(response).get("response", {})
                header = data.get("msgHeader") or {}
                code = header.get("resultCode")
                rows = (data.get("msgBody") or {}).get(field) or []
                if isinstance(rows, dict):
                    rows = [rows]
                ok = str(code) == "0" and isinstance(rows, list) and bool(rows)
                query_time = header.get("queryTime") or (data.get("comMsgHeader") or {}).get("queryTime")
                result = {"status": "response_received" if ok else "no_usable_response",
                          "http_status": response.status,
                          "provider_code": int(code) if str(code).isdigit() else None,
                          "row_count": len(rows) if isinstance(rows, list) else None,
                          "query_time_present": bool(query_time),
                          "query_time_parseable": query_time_parseable(query_time),
                          "query_time_is_generation_time": False}
        except urllib.error.HTTPError as error:
            result = {"status": "http_error", "http_status": error.code}
        except Exception as error:
            result = {"status": "request_or_parse_failed", "exception_type": type(error).__name__}
        passed &= result["status"] == "response_received"
        result["stage"] = label
        print(json.dumps(result), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
