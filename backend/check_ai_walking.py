"""One synthetic structured-output request; no personal locations or raw output."""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import dotenv_values
from pydantic import ValidationError
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.ai import provider
from app.ai.prompt_loader import load_prompt, PromptLoadError
from app.ai.walking_dto import EstimateOutput
from app.ai.walking_service import parse_input, validate_output
from app.common.errors import AuthError


def main():
    settings = {**dotenv_values(Path(__file__).resolve().parents[1] / '.env'), **os.environ}
    try:
        if urlsplit(settings.get('OPENAI_BASE_URL') or '').hostname != 'mlapi.run':
            print(json.dumps({'status': 'configuration_error'})); return 1
    except ValueError:
        print(json.dumps({'status': 'configuration_error'})); return 1
    value = {'request_id': 'req_synthetic_walking', 'policy_version': 'walk-policy.v1',
        'profile': {'version': 1, 'validated_duration_factor': 1.2, 'valid_factor_range': [0.5, 2.0], 'fallback_speed_mps': None},
        'candidates': [{'candidate_id': 'walk_synthetic_001', 'origin_ref': 'origin_synthetic', 'destination_ref': 'destination_synthetic',
            'direction': 'outbound', 'scope': 'place_entrance_to_stop', 'required_scope': 'place_entrance_to_stop',
            'is_walkable_route': True, 'distance_meters': 350, 'provider_duration_seconds': 300,
            'provider_duration_includes_personalization': False, 'evidence_ids': ['evidence_synthetic_001'], 'missing_segments': []}]}
    started = time.monotonic()
    try:
        request = parse_input(value)
        bundle = load_prompt('walking_estimate', expected_version='walking_estimate.v1')
        raw = provider.fetch_estimate(bundle.messages() + [{'role': 'user', 'content': request.model_dump_json()}])
        output = EstimateOutput.model_validate(provider.json_object(raw))
        validate_output(output, request)
        item = output.results[0]
        passed = item.status == 'ok' and item.estimated_seconds == 360
        print(json.dumps({'status': 'ok' if passed else 'unexpected_response', 'prompt_version': output.prompt_version,
            'model_matches': True, 'result_count': len(output.results), 'result_status': item.status,
            'estimated_seconds': item.estimated_seconds, 'server_validation_passed': True,
            'elapsed_seconds': round(time.monotonic() - started, 2)}))
        return 0 if passed else 1
    except AuthError as error:
        diagnostic = {'status': 'failed', 'http_status': error.status, 'error_code': error.code}
        if isinstance(error, provider.AIProviderError):
            diagnostic.update(upstream_http_status=error.upstream_status, upstream_error_code=error.upstream_code, diagnostic_tags=error.diagnostic_tags)
        print(json.dumps(diagnostic))
    except (ValidationError, ValueError, TypeError, UnicodeError, PromptLoadError):
        print(json.dumps({'status': 'failed', 'error_code': 'AI_OUTPUT_INVALID'}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
