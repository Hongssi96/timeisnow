"""One minimal request to the AI endpoint configured in the project .env."""
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
    key = settings.get("OPENAI_API_KEY")
    base_url = (settings.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = settings.get("OPENAI_MODEL")
    parsed = urllib.parse.urlsplit(base_url)
    if (not key or model != "gpt-5.6-luna" or parsed.scheme != "https"
            or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        print(json.dumps({"status": "configuration_error"}))
        return 1
    payload = {"model": model, "input": "Reply with exactly OK.",
               "max_output_tokens": 32, "reasoning": {"effort": "none"}, "store": False}
    request = urllib.request.Request(
        base_url + "/responses", data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=35) as response:
            data = json.load(response)
            output = "".join(
                part.get("text", "") for item in data.get("output", [])
                for part in item.get("content", []) if part.get("type") == "output_text"
            )
            usage = data.get("usage") or {}
            passed = data.get("status") == "completed" and output.strip() == "OK"
            print(json.dumps({"http_status": response.status,
                              "status": "ok" if passed else "unexpected_response",
                              "response_completed": data.get("status") == "completed",
                              "model_matches": data.get("model") == model,
                              "reply_is_OK": output.strip() == "OK",
                              "elapsed_seconds": round(time.monotonic() - started, 2),
                              "input_tokens": usage.get("input_tokens"),
                              "output_tokens": usage.get("output_tokens"),
                              "total_tokens": usage.get("total_tokens")}))
            return 0 if passed else 1
    except urllib.error.HTTPError as error:
        try:
            code = json.load(error).get("error", {}).get("code")
        except Exception:
            code = None
        allowed = {"invalid_api_key", "insufficient_quota", "model_not_found",
                   "rate_limit_exceeded", "unsupported_parameter", "invalid_parameter",
                   "permission_denied"}
        print(json.dumps({"status": "http_error", "http_status": error.code,
                          "error_code": code if code in allowed else "unclassified"}))
    except Exception as error:
        # Raw errors can include credentials or private endpoint paths.
        print(json.dumps({"status": "connection_error", "exception_type": type(error).__name__}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
