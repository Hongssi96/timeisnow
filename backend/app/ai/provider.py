"""Bounded Responses transport: no redirects, tools, logs, or raw error exposure."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dotenv import dotenv_values
from app.common.database import ROOT
from app.common.errors import AuthError
from app.common.http import NoRedirect
from app.ai.walking_dto import EstimateOutput

MODEL = 'gpt-5.6-luna'
MAX_BYTES = 262144


def invalid():
    raise AuthError(502, 'AI_OUTPUT_INVALID', 'AI 산정 결과를 확인할 수 없어요.')


def unavailable():
    raise AuthError(503, 'PROVIDER_UNAVAILABLE', 'AI 서비스에 연결할 수 없어요.')


class AIProviderError(AuthError):
    """Internal diagnostic facts only; public error contract remains unchanged."""
    def __init__(self, upstream_status, upstream_code, diagnostic_tags=()):
        super().__init__(503, 'PROVIDER_UNAVAILABLE', 'AI 서비스에 연결할 수 없어요.')
        self.upstream_status = upstream_status
        self.upstream_code = upstream_code
        self.diagnostic_tags = list(diagnostic_tags)


def http_failure(error):
    allowed = {'invalid_api_key', 'insufficient_quota', 'model_not_found',
               'rate_limit_exceeded', 'unsupported_parameter', 'invalid_parameter',
               'permission_denied', 'invalid_json_schema', 'invalid_request_error'}
    code = 'unclassified'
    tags = []
    try:
        raw = error.read(MAX_BYTES + 1)
        if len(raw) <= MAX_BYTES:
            body = json_object(raw)
            error_data = body.get('error') if isinstance(body, dict) else None
            value = error_data.get('code') if isinstance(error_data, dict) else None
            if isinstance(value, str) and value in allowed: code = value
            # Emit fixed vocabulary only, never any substring from the upstream body.
            lowered = json.dumps(body, ensure_ascii=False).lower()
            vocabulary = {'schema': 'SCHEMA', 'exclusiveMinimum': 'EXCLUSIVE_MINIMUM',
                          'pattern': 'PATTERN', 'maxItems': 'MAX_ITEMS', 'minItems': 'MIN_ITEMS',
                          'minimum': 'MINIMUM', 'maximum': 'MAXIMUM', 'anyOf': 'ANY_OF',
                          'const': 'CONST', 'additionalProperties': 'ADDITIONAL_PROPERTIES',
                          'unsupported': 'UNSUPPORTED', 'not supported': 'UNSUPPORTED',
                          'unknown parameter': 'UNKNOWN_PARAMETER', 'invalid': 'INVALID',
                          'quota': 'QUOTA', 'balance': 'BALANCE', 'credit': 'CREDIT',
                          'model': 'MODEL', 'authentication': 'AUTHENTICATION',
                          'reasoning': 'REASONING', 'text.format': 'TEXT_FORMAT',
                          'json_schema': 'JSON_SCHEMA', 'required': 'REQUIRED',
                          'max_output_tokens': 'MAX_OUTPUT_TOKENS', 'input': 'INPUT',
                          'store': 'STORE'}
            tags = list(dict.fromkeys(tag for word, tag in vocabulary.items() if word.lower() in lowered))
    except (OSError, ValueError, TypeError, AttributeError, UnicodeError):
        pass
    raise AIProviderError(error.code, code, tags) from None


def json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('DUPLICATE_KEY')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE')))


def fetch_estimate(messages):
    settings = {**dotenv_values(ROOT / '.env'), **os.environ}
    key, model = settings.get('OPENAI_API_KEY'), settings.get('OPENAI_MODEL')
    base = (settings.get('OPENAI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
    try:
        url = urllib.parse.urlsplit(base)
        valid = (url.scheme == 'https' and url.hostname and not url.username and not url.password
                 and not url.query and not url.fragment)
    except ValueError:
        valid = False
    if not key or model != MODEL or not valid: unavailable()
    payload = {'model': MODEL, 'input': messages, 'store': False,
               'max_output_tokens': 512, 'reasoning': {'effort': 'none'},
               'text': {'format': {'type': 'json_schema', 'name': 'walking_estimate',
                                  'strict': True, 'schema': EstimateOutput.model_json_schema()}}}
    request = urllib.request.Request(base + '/responses', data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=35) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES: invalid()
            data = json_object(raw)
    except urllib.error.HTTPError as error:
        http_failure(error)
    except (TimeoutError, urllib.error.URLError) as error:
        if isinstance(error, TimeoutError) or isinstance(getattr(error, 'reason', None), TimeoutError):
            raise AuthError(504, 'PROVIDER_TIMEOUT', 'AI 서비스 응답을 기다릴 수 없어요.') from None
        unavailable()
    except OSError:
        unavailable()
    except (ValueError, UnicodeError, TypeError):
        invalid()
    if not isinstance(data, dict) or data.get('status') != 'completed' or data.get('model') != MODEL:
        invalid()
    output = data.get('output')
    if not isinstance(output, list): invalid()
    texts = []
    for item in output:
        if not isinstance(item, dict): invalid()
        if item.get('type') == 'reasoning': continue
        if item.get('type') != 'message' or item.get('role') != 'assistant' or item.get('status') != 'completed': invalid()
        content = item.get('content')
        if not isinstance(content, list): invalid()
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'output_text' or not isinstance(part.get('text'), str): invalid()
            texts.append(part['text'])
    if len(texts) != 1 or not texts[0].strip(): invalid()
    return texts[0]
