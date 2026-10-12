"""Immutable validated snapshots; no public writes or provider calls."""
from datetime import timedelta
import hashlib
import json
import time
from uuid import uuid4
from pydantic import ValidationError
from psycopg.types.json import Jsonb
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.ai.walking_dto import EstimateOutput
from app.ai.walking_service import parse_input,validate_output,missing as missing_evidence,expected
from app.ai.prompt_loader import load_prompt
from app.journeys.service import check_refs
from app.places.service import parsed_id
from app.walking import history_repository as repository
from app.walking.history_dto import Context,ExecutionMetadata,EstimateSummary


def missing():
    raise AuthError(404,'RESOURCE_NOT_FOUND','도보 산정값을 다시 확인해주세요.')


def invalid():
    raise AuthError(422,'VALIDATION_ERROR','산정 이력 입력을 확인해주세요.')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def parse_context(value,metadata):
    try:
        context=Context.model_validate(value.model_dump() if isinstance(value,Context) else value)
        meta=ExecutionMetadata.model_validate(metadata.model_dump() if isinstance(metadata,ExecutionMetadata) else metadata)
        identifiers=[str(parsed_id(ref.place_id)) for ref in context.place_refs]
        if len(set(identifiers))!=len(identifiers):invalid()
        refs=sorted([{'place_id':str(parsed_id(ref.place_id)),'location_version':ref.location_version} for ref in context.place_refs],key=lambda item:item['place_id'])
        if context.verified_at.tzinfo is None or context.valid_until.tzinfo is None or context.valid_until<=context.verified_at:invalid()
        return context,meta,refs
    except (ValidationError,ValueError,TypeError):
        invalid()


def check_context(connection,user_id,request,context,refs):
    repository.lock(connection,user_id)
    profile=repository.profile(connection,user_id)
    if not profile or profile['status']!='active':missing()
    if profile['version']!=request.profile.version:
        raise AuthError(409,'VERSION_CONFLICT','프로필이 변경됐어요. 다시 산정해주세요.')
    now=repository.clock(connection)
    if context.verified_at>now:invalid()
    if context.valid_until<=now:missing()
    check_refs(connection,user_id,refs)
    return now


def saved_result(connection,user_id,execution_id):
    rows=repository.execution_estimates(connection,user_id,execution_id)
    return {'execution_id':str(execution_id),'estimates':[{'candidate_id':row['candidate_id'],
        'estimate_id':str(row['estimate_id']),'revision_id':str(row['revision_id'])} for row in rows]}


def persist(user_id,value,output,*,context,metadata,failure_code=None):
    """For trusted server callers after ownership and physical evidence verification."""
    user_id=parsed_id(str(user_id))
    request=parse_input(value)
    context,metadata,refs=parse_context(context,metadata)
    bundle=load_prompt('walking_estimate',expected_version='walking_estimate.v1')
    validated=None
    if failure_code is None:
        try:validated=EstimateOutput.model_validate(output.model_dump() if isinstance(output,EstimateOutput) else output)
        except (ValidationError,TypeError,ValueError):
            raise AuthError(502,'AI_OUTPUT_INVALID','AI 산정 결과를 확인할 수 없어요.') from None
        validate_output(validated,request)
        if any(item.status=='ok' for item in validated.results) and metadata.model_version is None:invalid()
    elif failure_code not in {'AI_OUTPUT_INVALID','PROVIDER_UNAVAILABLE','PROVIDER_TIMEOUT','PROMPT_RESOURCE_INVALID'}:invalid()
    status='failed' if failure_code else ('validated' if any(item.status=='ok' for item in validated.results) else 'needs_data')
    # Free-form model reasons are not persisted; they are unnecessary for numeric provenance.
    structured=validated.model_dump() if validated else None
    if structured:
        for item in structured['results']:item.pop('reason',None)
    body_hash=fingerprint({'input':request.model_dump(),'output':validated.model_dump() if validated else None,
        'context':{**context.model_dump(mode='json'),'place_refs':refs},'metadata':metadata.model_dump(),'failure_code':failure_code})
    with database() as connection:
        now=check_context(connection,user_id,request,context,refs)
        old=repository.execution(connection,user_id,request.request_id)
        if old:
            if old['body_hash']!=body_hash:
                raise AuthError(409,'IDEMPOTENCY_CONFLICT','실행 식별자를 다른 산정에 재사용할 수 없어요.')
            if old['retained_until']<=now:missing()
            return saved_result(connection,user_id,old['id'])
        execution_id=uuid4();retained=now+timedelta(days=90)
        repository.insert_execution(connection,(execution_id,user_id,request.request_id,body_hash,metadata.model_version,
            bundle.system.version,bundle.prompt_version,request.policy_version,request.profile.version,
            Jsonb(request.model_dump()),Jsonb({**context.model_dump(mode='json'),'place_refs':refs}),Jsonb(structured) if structured else None,status,failure_code,metadata.latency_ms,
            Jsonb(metadata.usage.model_dump()) if metadata.usage else None,now,retained))
        by_id={item.candidate_id:item for item in validated.results} if validated else {}
        for candidate in request.candidates:
            result=by_id.get(candidate.candidate_id)
            if result is None or result.status!='ok':continue
            if missing_evidence(candidate,request.profile):invalid()
            base,factor,seconds,method=expected(candidate,request.profile)
            expires=min(now+timedelta(days=30),context.valid_until)
            path_id,estimate_id,revision_id=uuid4(),uuid4(),uuid4()
            evidence=candidate.model_dump()
            repository.insert_path(connection,(path_id,user_id,fingerprint({'candidate':evidence,'place_refs':refs}),candidate.candidate_id,
                candidate.origin_ref,candidate.destination_ref,candidate.direction,candidate.scope,Jsonb(refs),Jsonb(evidence),
                context.verified_at,now,expires,retained))
            repository.insert_estimate(connection,(estimate_id,user_id,path_id,request.policy_version,now))
            repository.insert_revision(connection,(revision_id,user_id,estimate_id,execution_id,request.profile.version,
                base,factor,seconds,method,now,expires,retained))
        return saved_result(connection,user_id,execution_id)


def record_failure(user_id,value,*,context,metadata,failure_code):
    return persist(user_id,value,None,context=context,metadata=metadata,failure_code=failure_code)


def detail(request,estimate_id):
    with database() as connection:
        user_id=security.authenticated(connection,request)
        repository.lock(connection,user_id)
        row=repository.summary(connection,user_id,parsed_id(estimate_id))
        now=repository.clock(connection)
        if not row or row['expires_at']<=now or row['retained_until']<=now or row['path_retained_until']<=now:missing()
        profile=repository.profile(connection,user_id)
        if not profile or profile['version']!=row['profile_version']:
            raise AuthError(409,'VERSION_CONFLICT','프로필이 변경됐어요. 다시 산정해주세요.')
        check_refs(connection,user_id,row['place_refs'])
        data=EstimateSummary(estimate_id=row['estimate_id'],revision_id=row['id'],base_seconds=float(row['base_seconds']),
            applied_duration_factor=float(row['applied_duration_factor']),estimated_seconds=int(row['estimated_seconds']),scope=row['scope'],
            calculated_at=row['calculated_at'],expires_at=row['expires_at'],prompt_version=row['prompt_version'],policy_version=row['policy_version'])
    return answer(request,data.model_dump(mode='json'))


def purge_expired_history(user_id):
    with database() as connection:
        user_id=parsed_id(str(user_id))
        repository.lock(connection,user_id)
        repository.purge(connection,user_id)


def _estimate_and_store(user_id,value,*,context):
    """Owned internal end-to-end execution with checks before and after the model call."""
    from app.ai.walking_service import estimate
    request=parse_input(value)
    checked_context,_,refs=parse_context(context,{'model_version':None})
    with database() as connection:
        now=check_context(connection,parsed_id(str(user_id)),request,checked_context,refs)
        old=repository.execution(connection,user_id,request.request_id)
        if old:
            context_snapshot={**checked_context.model_dump(mode='json'),'place_refs':refs}
            if old['input_evidence']!=request.model_dump() or old['context_snapshot']!=context_snapshot:
                raise AuthError(409,'IDEMPOTENCY_CONFLICT','실행 식별자를 다른 산정에 재사용할 수 없어요.')
            if old['retained_until']<=now:missing()
            if old['validation_status']=='failed':
                code=old['failure_code']
                raise AuthError(504 if code=='PROVIDER_TIMEOUT' else 502 if code=='AI_OUTPUT_INVALID' else 503,
                                code,'이전 산정 실행이 실패했어요. 새 실행으로 다시 확인해주세요.')
            rows=repository.execution_estimates(connection,user_id,old['id'])
            if any(row['expires_at']<=now for row in rows):missing()
            replay=old['structured_result']
            for result in replay['results']:result['reason']='저장된 검증 실행 결과예요.'
            return {'result':replay,**saved_result(connection,user_id,old['id'])}
    called=any(not missing_evidence(candidate,request.profile) for candidate in request.candidates)
    started=time.monotonic()
    try:
        output=estimate(request)
    except AuthError as error:
        if error.code in {'AI_OUTPUT_INVALID','PROVIDER_UNAVAILABLE','PROVIDER_TIMEOUT'}:
            record_failure(user_id,request,context=checked_context,metadata={'model_version':None,
                'latency_ms':round((time.monotonic()-started)*1000) if called else None},failure_code=error.code)
        raise
    stored=persist(user_id,request,output,context=checked_context,metadata={'model_version':'gpt-5.6-luna' if called else None,
        'latency_ms':round((time.monotonic()-started)*1000) if called else None})
    return {'result':output.model_dump(mode='json'),**stored}


def estimate_and_store(user_id,value,*,context):
    request=parse_input(value)
    user_id=parsed_id(str(user_id))
    key='walking-execution:'+str(user_id)+':'+request.request_id
    with database() as locking_connection:
        if not repository.try_execution_lock(locking_connection,key):
            raise AuthError(409,'EXECUTION_IN_PROGRESS','같은 산정 실행이 처리 중이에요.')
        try:
            return _estimate_and_store(user_id,request,context=context)
        finally:
            repository.release_execution_lock(locking_connection,key)
