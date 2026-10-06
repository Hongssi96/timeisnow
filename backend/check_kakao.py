"""One public-place search to verify the configured Kakao REST key."""
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    key = settings.get("KAKAO_REST_API_KEY")
    if not key:
        print(json.dumps({"status": "missing_rest_key"}))
        return 1
    params = {"query": "강남역", "category_group_code": "SW8", "size": 3,
              "x": "127.0276", "y": "37.4979", "radius": 1000}
    request = urllib.request.Request(
        "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(params),
        headers={"Authorization": "KakaoAK " + key},
    )
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            data = json.load(response)
            documents = data.get("documents", [])
            valid = bool(documents) and all(
                item.get("id") and item.get("place_name") and item.get("category_group_code") == "SW8"
                and -180 <= float(item["x"]) <= 180 and -90 <= float(item["y"]) <= 90
                for item in documents
            )
            print(json.dumps({"status": "ok" if valid else "unexpected_response",
                              "http_status": response.status, "result_count": len(documents),
                              "place_fields_and_coordinates_valid": valid,
                              "elapsed_seconds": round(time.monotonic() - started, 2)}))
            return 0 if valid else 1
    except urllib.error.HTTPError as error:
        try:
            data = json.load(error)
            code = data.get("code")
        except Exception:
            code = None
        print(json.dumps({"status": "http_error", "http_status": error.code,
                          "provider_error_code": code if isinstance(code, int) else None}))
    except Exception as error:
        # Never print raw exceptions or payloads, which may contain secrets.
        print(json.dumps({"status": "connection_error", "exception_type": type(error).__name__}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
