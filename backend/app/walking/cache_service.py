"""Reuse only caller-verified physical identities and revalidated numeric snapshots."""
import hashlib
import json
import math
from decimal import Decimal, ROUND_CEILING
from pydantic import ValidationError
from app.common.errors import AuthError
from app.ai.walking_dto import Result,Profile
from app.ai.walking_service import missing, expected
from app.ai.prompt_loader import load_prompt
from app.ai.provider import MODEL, invalid
from app.walking.history_dto import CacheSource
from app.walking import history_repository as repository


def parse_sources(value,request):
    if value is None:return None
    try:
        if not isinstance(value,list) or len(value)>20:raise ValueError()
        sources=[CacheSource.model_validate(item.model_dump() if isinstance(item,CacheSource) else item) for item in value]
        ids=[item.candidate_id for item in sources]
        if len(set(ids))!=len(ids) or not set(ids)<={item.candidate_id for item in request.candidates}:raise ValueError()
        for item in sources:
            for key,token in item.model_dump().items():
                if key!='candidate_id' and token.lower() in {'unknown','unconfirmed','none','null'}:raise ValueError()
                if key not in {'candidate_id','origin_entrance_ref','destination_entrance_ref'} and token=='not_applicable':raise ValueError()
        return {item.candidate_id:item.model_dump() for item in sorted(sources,key=lambda item:item.candidate_id)}
    except (ValidationError,ValueError,TypeError):
        raise AuthError(422,'VALIDATION_ERROR','확인된 도보 경로 식별자를 입력해주세요.') from None


def snapshot(context,refs,sources):
    value={**context.model_dump(mode='json'),'place_refs':refs}
    if sources is not None:value['cache_sources']=list(sources.values())
    return value


def identity(candidate,request,refs,source):
    if source is None or missing(candidate,request.profile):return None,None
    bundle=load_prompt('walking_estimate',expected_version='walking_estimate.v1')
    evidence=candidate.model_dump(exclude={'candidate_id','evidence_ids'})
    value={'source':{key:value for key,value in source.items() if key!='candidate_id'},'evidence':evidence,
        'place_refs':refs,'fallback_speed_mps':request.profile.fallback_speed_mps if candidate.provider_duration_seconds is None else None,
        'policy_version':request.policy_version,'system_prompt_version':bundle.system.version,
        'prompt_version':bundle.prompt_version,'model_version':MODEL}
    key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return key,value


def lookup(connection,user_id,candidate,request,refs,source,now,context,revision_id=None,allow_recalculation=False):
    key,physical=identity(candidate,request,refs,source)
    if key is None:return None
    row=repository.cache_candidate(connection,user_id,key,revision_id)
    if row is None:return None
    if row['cache_identity']!=physical or row['place_refs']!=refs:invalid()
    previous=Profile.model_validate(row['input_evidence']['profile'])
    current=request.profile
    changed=previous.model_dump()!=current.model_dump()
    if changed:
        same_fields=previous.model_dump(exclude={'version','validated_duration_factor'})==current.model_dump(exclude={'version','validated_duration_factor'})
        if not allow_recalculation or not same_fields:
            raise AuthError(409,'PROFILE_RECALCULATION_REQUIRED','개인 설정의 기준을 다시 확인해주세요.')
    if row['baseline_model_version']!=physical['model_version'] or row['prompt_version']!=physical['prompt_version'] or row['system_prompt_version']!=physical['system_prompt_version'] or row['policy_version']!=request.policy_version:invalid()
    if row['source']=='ai_estimate':
        old_base,old_factor,old_seconds,old_method=expected(candidate,previous)
    else:
        old_base=float(row['base_seconds'])
        old_factor=1.0 if candidate.provider_duration_includes_personalization else previous.validated_duration_factor or 1.0
        old_seconds=int((row['base_seconds']*Decimal(str(old_factor))).to_integral_value(rounding=ROUND_CEILING))
        old_method=expected(candidate,previous)[3]
    physical_base=expected(candidate,previous)[0]
    if (not math.isclose(float(row['base_seconds']),physical_base,rel_tol=1e-12,abs_tol=1e-9)
        or not math.isclose(float(row['base_seconds']),old_base,rel_tol=1e-12,abs_tol=1e-9)
        or float(row['applied_duration_factor'])!=old_factor or int(row['estimated_seconds'])!=old_seconds or row['method']!=old_method):invalid()
    base,factor,seconds,method=old_base,old_factor,old_seconds,old_method
    if changed:
        base=float(row['base_seconds'])
        factor=1.0 if candidate.provider_duration_includes_personalization else current.validated_duration_factor or 1.0
        seconds=int((row['base_seconds']*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
    expires=min(row['expires_at'],row['path_expires_at'],context.valid_until)
    if expires<=now:return None
    result=Result(candidate_id=candidate.candidate_id,status='ok',origin_ref=candidate.origin_ref,
        destination_ref=candidate.destination_ref,direction=candidate.direction,scope=candidate.scope,
        base_seconds=base,applied_duration_factor=factor,estimated_seconds=seconds,method=method,
        evidence_ids=candidate.evidence_ids,missing_segments=[],reason='같은 조건의 검증된 도보 시간을 재사용했어요.')
    link={'candidate_id':candidate.candidate_id,'estimate_id':str(row['estimate_id']),
        'revision_id':str(row['id']),'expires_at':expires.isoformat()}
    if changed:
        link['recalculated']=True
        result.reason='검증된 기준 시간에 새 개인 계수를 적용했어요.'
    return result,link
