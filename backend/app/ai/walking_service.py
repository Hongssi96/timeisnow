"""Internal walking estimation; callers must authorize and verify physical evidence."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import math
from pydantic import ValidationError
from app.common.errors import AuthError
from app.ai.prompt_loader import load_prompt
from app.ai.walking_dto import EstimateInput, EstimateOutput, Result
from app.ai import provider
from app.walking.dto import Evidence


def parse_input(value):
    try:
        return EstimateInput.model_validate(value.model_dump() if isinstance(value, EstimateInput) else value)
    except (ValidationError, TypeError, ValueError):
        raise AuthError(422, 'VALIDATION_ERROR', 'AI 산정 입력을 확인해주세요.') from None


def missing(candidate, profile):
    reasons = list(candidate.missing_segments)
    if not candidate.is_walkable_route: reasons.append('WALKABLE_ROUTE_UNCONFIRMED')
    if candidate.direction == 'unknown': reasons.append('DIRECTION_UNCONFIRMED')
    if candidate.scope in ('unknown', 'provider_walking_segment') or candidate.scope != candidate.required_scope:
        reasons.append('REQUIRED_SCOPE_UNCONFIRMED')
    if not candidate.evidence_ids: reasons.append('EVIDENCE_MISSING')
    if candidate.provider_duration_seconds is None and (candidate.distance_meters is None or profile.fallback_speed_mps is None):
        reasons.append('BASE_DURATION_MISSING')
    return list(dict.fromkeys(reasons))


def expected(candidate, profile):
    if candidate.provider_duration_seconds is not None:
        base, method = Decimal(str(candidate.provider_duration_seconds)), 'provider_duration'
    else:
        base = Decimal(str(candidate.distance_meters)) / Decimal(str(profile.fallback_speed_mps))
        method = 'distance_speed'
    factor = Decimal('1') if candidate.provider_duration_includes_personalization else Decimal(str(profile.validated_duration_factor or 1.0))
    seconds = int((base * factor).to_integral_value(rounding=ROUND_CEILING))
    if not math.isfinite(float(base)) or seconds < 1:
        raise AuthError(422, 'VALIDATION_ERROR', 'AI 산정 입력을 확인해주세요.')
    return float(base), float(factor), seconds, method


def needs_data(candidate, reasons):
    return Result(candidate_id=candidate.candidate_id, status='needs_data',
        origin_ref=candidate.origin_ref, destination_ref=candidate.destination_ref,
        direction=candidate.direction, scope=candidate.scope, base_seconds=None,
        applied_duration_factor=None, estimated_seconds=None, method='none',
        evidence_ids=candidate.evidence_ids, missing_segments=reasons,
        reason='검증된 보행 근거가 부족해 시간을 산정할 수 없어요.')


def validate_output(output, request):
    if output.request_id != request.request_id: provider.invalid()
    by_id = {item.candidate_id: item for item in output.results}
    if len(by_id) != len(output.results) or set(by_id) != {item.candidate_id for item in request.candidates}: provider.invalid()
    for candidate in request.candidates:
        result = by_id[candidate.candidate_id]
        for key in ('origin_ref', 'destination_ref', 'direction', 'scope'):
            if getattr(result, key) != getattr(candidate, key): provider.invalid()
        if len(set(result.evidence_ids)) != len(result.evidence_ids) or not set(result.evidence_ids) <= set(candidate.evidence_ids): provider.invalid()
        if len(set(result.missing_segments)) != len(result.missing_segments): provider.invalid()
        if result.status != 'ok':
            if any(value is not None for value in (result.base_seconds, result.applied_duration_factor, result.estimated_seconds)) or result.method != 'none': provider.invalid()
            if result.status == 'needs_data' and not result.missing_segments: provider.invalid()
            continue
        if missing(candidate, request.profile) or result.missing_segments or set(result.evidence_ids) != set(candidate.evidence_ids): provider.invalid()
        base, factor, seconds, method = expected(candidate, request.profile)
        if (result.base_seconds is None or not math.isclose(result.base_seconds, base, rel_tol=1e-12, abs_tol=1e-9)
                or result.applied_duration_factor != factor or result.estimated_seconds != seconds or result.method != method): provider.invalid()
    return output


def estimate(value):
    request = parse_input(value)
    bundle = load_prompt('walking_estimate', expected_version='walking_estimate.v1')
    local, eligible = {}, []
    for candidate in request.candidates:
        reasons = missing(candidate, request.profile)
        if reasons: local[candidate.candidate_id] = needs_data(candidate, reasons)
        else:
            try:
                expected(candidate, request.profile)
            except ArithmeticError:
                raise AuthError(422, 'VALIDATION_ERROR', 'AI 산정 입력을 확인해주세요.') from None
            eligible.append(candidate)
    if eligible:
        subset = parse_input({**request.model_dump(), 'candidates': [item.model_dump() for item in eligible]})
        messages = bundle.messages() + [{'role': 'user', 'content': subset.model_dump_json()}]
        for attempt in range(2):
            raw = provider.fetch_estimate(messages)
            try:
                output = EstimateOutput.model_validate(provider.json_object(raw))
            except (ValidationError, ValueError, TypeError, UnicodeError):
                if attempt == 0: continue
                provider.invalid()
            # Semantic failures do not consume a second model request.
            validate_output(output, subset)
            local.update({item.candidate_id: item for item in output.results})
            break
    return EstimateOutput(request_id=request.request_id, prompt_version=bundle.prompt_version,
                          results=[local[item.candidate_id] for item in request.candidates])


def estimate_evidence(evidence, *, request_id, profile):
    """Bridge the current unready evidence without names, coordinates or provider calls.

    This is not an HTTP authorization boundary. The calling service must obtain
    an owned evidence record through the existing ownership/version checks.
    """
    evidence = Evidence.model_validate(evidence.model_dump() if isinstance(evidence, Evidence) else evidence)
    if evidence.expires_at.tzinfo is None or evidence.expires_at <= datetime.now(timezone.utc):
        raise AuthError(404, 'RESOURCE_NOT_FOUND', '도보 근거를 다시 확인해주세요.')
    def ref(value):
        return str(value.leg_id) if value.type == 'transit_stop' else value.type
    candidates = [dict(candidate_id=str(item.segment_id), origin_ref=ref(item.from_ref), destination_ref=ref(item.to_ref),
        direction='unknown', scope=item.scope, required_scope='unknown', is_walkable_route=False,
        distance_meters=item.provider_distance_meters or None, provider_duration_seconds=item.provider_duration_seconds or None,
        provider_duration_includes_personalization=False, evidence_ids=[str(value) for value in item.walking_leg_ids],
        missing_segments=item.missing_segments) for item in evidence.segments]
    return estimate(dict(request_id=request_id, policy_version='walk-policy.v1', profile=profile, candidates=candidates))
