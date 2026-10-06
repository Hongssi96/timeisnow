"""Prepare public-arrival probes. Summaries only; never log keys or request URLs."""
import argparse
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from dotenv import dotenv_values
from check_kakao import NoRedirect


def safe_code(value):
    value = str(value) if value is not None else ""
    return value if re.fullmatch(r"(?:\d{1,3}|(?:INFO|ERROR)-\d{3})", value) else "unknown"


def summarize(raw, provider):
    if provider == "seoul-bus":
        root = ET.fromstring(raw)
        code = safe_code(root.findtext(".//headerCd") or root.findtext(".//returnReasonCode"))
        rows = [{node.tag: node.text for node in item} for item in root.findall(".//itemList")]
        time_fields = ("exps1", "exps2")
        identity_fields = ("busRouteId", "stId", "staOrd", "dir")
        timestamp = "mkTm"
    else:
        data = json.loads(raw)
        if provider == "gyeonggi-bus":
            response = data.get("response", {})
            code = safe_code(response.get("msgHeader", {}).get("resultCode"))
            body = response.get("msgBody") or {}
            rows = body.get("busArrivalItem") or []
            if isinstance(rows, dict):
                rows = [rows]
            time_fields = ("predictTimeSec1", "predictTimeSec2")
            identity_fields = ("stationId", "routeId", "staOrder", "routeDestId")
            timestamp = None
        else:
            code = safe_code((data.get("errorMessage") or data.get("RESULT") or {}).get("code"))
            rows = data.get("realtimeArrivalList") or []
            time_fields = ("barvlDt",)
            identity_fields = ("subwayId", "statnId", "updnLine", "bstatnId")
            timestamp = "recptnDt"
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {"status": "unexpected_schema", "provider_code": code}
    valid_count = sum(1 for row in rows for field in time_fields
                      if re.fullmatch(r"\d+", str(row.get(field, ""))))
    successful = code in {"0", "00", "INFO-000"}
    # A normal empty result is not a successful departure recommendation.
    return {"status": ("response_received" if rows else "no_arrivals") if successful else "provider_error",
            "provider_code": code, "row_count": len(rows),
            "nonnegative_seconds_fields": valid_count,
            "identity_fields_present": bool(rows) and all(
                all(row.get(field) not in (None, "") for field in identity_fields) for row in rows),
            "timestamp_fields_present": bool(rows) and bool(timestamp)
            and all(bool(row.get(timestamp)) for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=("seoul-bus", "gyeonggi-bus", "seoul-subway"))
    parser.add_argument("--sample", action="store_true", help="Subway public sample: Seoul station only")
    parser.add_argument("--official-http", action="store_true", help="Explicit diagnostic HTTP for the two official Seoul hosts")
    args = parser.parse_args()
    settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    if args.sample and args.provider != "seoul-subway":
        print(json.dumps({"status": "sample_not_supported"}))
        return 1
    if args.official_http and args.provider == "gyeonggi-bus":
        print(json.dumps({"status": "http_diagnostic_not_supported"}))
        return 1
    key_name = "SEOUL_SUBWAY_API_KEY" if args.provider == "seoul-subway" else "DATA_GO_KR_SERVICE_KEY"
    key = "sample" if args.sample else settings.get(key_name)
    if not key:
        print(json.dumps({"provider": args.provider, "status": "missing_key", "setting": key_name}))
        return 1
    if args.provider == "seoul-bus":
        params = {"serviceKey": urllib.parse.unquote(key), "busRouteId": "100100118"}
        scheme = "http" if args.official_http else "https"
        url = scheme + "://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll?" + urllib.parse.urlencode(params)
    elif args.provider == "gyeonggi-bus":
        params = {"serviceKey": urllib.parse.unquote(key), "stationId": "200000177",
                  "routeId": "200000037", "staOrder": "19", "format": "json"}
        url = "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2?" + urllib.parse.urlencode(params)
    else:
        # HTTP is explicit on fixed official hosts; never automatic fallback.
        scheme = "http" if args.sample or args.official_http else "https"
        url = (scheme + "://swopenapi.seoul.go.kr/api/subway/" + urllib.parse.quote(key, safe="")
               + "/json/realtimeStationArrival/0/5/" + urllib.parse.quote("서울", safe=""))
    try:
        with urllib.request.build_opener(NoRedirect).open(url, timeout=30) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("response_too_large")
            result = summarize(raw, args.provider)
            result.update({"provider": args.provider, "http_status": response.status,
                           "public_sample": args.sample, "transport": urllib.parse.urlsplit(url).scheme})
            print(json.dumps(result))
            return 0 if result["status"] in {"response_received", "no_arrivals"} else 1
    except urllib.error.HTTPError as error:
        print(json.dumps({"provider": args.provider, "status": "http_error", "http_status": error.code}))
    except Exception as error:
        print(json.dumps({"provider": args.provider, "status": "request_or_parse_failed",
                          "exception_type": type(error).__name__}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
