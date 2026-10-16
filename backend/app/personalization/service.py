"""Server-only robust updates from separate manual start/ready confirmations."""
import hashlib,json
from datetime import datetime
from decimal import Decimal
from statistics import median
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.places.service import parsed_id
from app.trips import service as trips,repository as trip_repo
from app.personalization import repository as repo

POLICY='manual-walking.v1'

def digest(body):return hashlib.sha256(json.dumps(body.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()
def conflicting():raise AuthError(409,'IDEMPOTENCY_CONFLICT','같은 기록의 확인 내용이 달라요.')

def summary(c,owner,p):
    rows=repo.samples(c,owner,p['generation'])
    n=len(rows);counts=repo.counts(c,owner,p['generation'])
    def mae(field):return float(sum(abs(r['observed_seconds']-r[field]) for r in rows)/n) if n else None
    def under(field):return sum(r[field]<r['observed_seconds'] for r in rows)/n if n else None
    return {'status':'active' if counts['valid']>=5 else 'learning','profile_version':p['version'],
      'factors':[{'type':'provider_mapped_access','value':p['walking_duration_factor']}],
      'sample_counts':counts,'policy_version':POLICY,
      'quality':{'sample_count':n,'baseline_mae_seconds':mae('base_seconds'),'personalized_mae_seconds':mae('predicted_seconds'),
        'baseline_underprediction_rate':under('base_seconds'),'personalized_underprediction_rate':under('predicted_seconds')},
      'can_restore':bool((repo.last_change(c,owner) or {}).get('restorable',False))}

def get(request):
    owner=trips.authenticate(request)
    with database() as c:return answer(request,summary(c,owner,repo.locked(c,owner)))

def mutate(request,body,kind):
    owner=trips.authenticate(request,'personalization');hash_value=digest(body)
    with database() as c:
        p=repo.locked(c,owner);previous=repo.request(c,owner,body.client_request_id)
        if previous:
            if previous['body_hash']!=hash_value or previous['kind']!=kind:conflicting()
            return answer(request,previous['response'])
        if p['version']!=body.expected_version:trips.conflict()
        last=repo.last_change(c,owner)
        if kind=='restore' and (last is None or not last['restorable']):raise AuthError(409,'RESTORE_UNAVAILABLE','복구할 이전 계수가 없어요.')
        factor=1.0 if kind=='reset' else last['previous_factor']
        version=repo.change(c,owner,factor,kind)
        if kind=='reset':repo.reset_generation(c,owner)
        repo.save_change(c,(uuid4(),owner,version,p['walking_duration_factor'],factor,kind,body.client_request_id,hash_value))
        value=summary(c,owner,repo.locked(c,owner));repo.save_response(c,owner,body.client_request_id,value)
        return answer(request,value)

def quality(c,owner,trip,events,body,p):
    d=trip['snapshot']['departure'];legs=trip['snapshot']['candidate']['ordered_legs']
    first=next(i for i,l in enumerate(legs) if l['type'] in ('BUS','SUBWAY'))
    start=next((e for e in events if e['type']=='departed' and str(e['leg_id'])==legs[0]['leg_id']),None)
    ready=next((e for e in events if e['type']=='approach_arrived' and str(e['leg_id'])==legs[max(0,first-1)]['leg_id']),None)
    reasons=[];observed=None
    if not start or not ready:reasons.append('MISSING_WALK_EVENTS')
    else:
        observed=Decimal(str((ready['occurred_at']-start['occurred_at']).total_seconds()))
        if observed<=0:reasons.append('INVALID_WALK_INTERVAL')
        if start['occurred_at']<p['started_at']:reasons.append('BEFORE_RESET')
        if any(e['excluded'] or e['source']!='manual' for e in (start,ready)):reasons.append('EVENT_EXCLUDED')
        if any(not 0<=(e['received_at']-e['occurred_at']).total_seconds()<=60 for e in (start,ready)):reasons.append('INPUT_DELAY')
        calculated=datetime.fromisoformat(d['calculated_at'].replace('Z','+00:00'))
        until=datetime.fromisoformat(d['valid_until'].replace('Z','+00:00'))
        if not calculated<=start['occurred_at']<until:reasons.append('STALE_GUIDANCE')
    if not body.same_scope:reasons.append('SCOPE_MISMATCH')
    if body.condition!='normal':reasons.append(body.condition.upper())
    personal=d.get('personal_walk');evidence=None
    if personal and legs[first]['type']=='BUS':evidence=repo.evidence(c,owner,personal['revision_id'])
    if (not evidence or evidence['scope']!='provider_mapped_access' or not evidence['cache_key']
        or evidence['base_seconds']<=0 or evidence['evidence'].get('provider_duration_includes_personalization') is not False
        or str(evidence['estimate_id'])!=personal['estimate_id']
        or evidence['profile_version']!=d['profile_version'] or evidence['estimated_seconds']!=d['approach_seconds']):
        reasons.append('UNVERIFIED_BASE');evidence=None
    if evidence and not repo.current_places(c,owner,evidence['place_refs']):reasons.append('PLACE_CHANGED')
    ratio=observed/evidence['base_seconds'] if evidence and observed is not None and observed>0 else None
    if ratio is not None and not Decimal('.5')<=ratio<=Decimal('2'):reasons.append('RATIO_REVIEW_REQUIRED')
    return reasons,observed,evidence,ratio

def observe(request,trip_id,body):
    owner=trips.authenticate(request,'walking-observation');hash_value=digest(body)
    with database() as c:
        p=repo.locked(c,owner);trip=trip_repo.owned(c,owner,parsed_id(trip_id),True)
        if trip is None:trips.missing()
        previous=repo.previous(c,owner,trip['id'])
        if previous:
            if previous['body_hash']!=hash_value:conflicting()
            return answer(request,previous['response'])
        reasons,observed,evidence,ratio=quality(c,owner,trip,trip_repo.events(c,trip['id']),body,p)
        oid=uuid4();status='excluded' if reasons else 'valid'
        result={'observation_id':str(oid),'status':status,'exclusion_reasons':reasons,
          'observed_seconds':float(observed) if observed is not None else None,'profile_version':p['version'],'sample_count':0,'updated':False}
        repo.save_observation(c,(oid,owner,trip['id'],hash_value,p['generation'],evidence['cache_key'] if evidence else None,
          Jsonb(evidence['place_refs'] if evidence else []),evidence['base_seconds'] if evidence else None,observed,
          evidence['estimated_seconds'] if evidence else None,ratio,status,Jsonb(reasons),Jsonb(result),trip['expires_at']))
        repo.save_confirmation(c,oid,body.model_dump(mode='json'))
        if not reasons:
            rows=repo.samples(c,owner,p['generation'],evidence['cache_key']);scope='same_segment'
            if len(rows)<5:rows=repo.samples(c,owner,p['generation']);scope='same_type'
            result['sample_count']=len(rows)
            if len(rows)>=5:
                factor=float(min(Decimal('2'),max(Decimal('.5'),Decimal('.8')*Decimal(str(p['walking_duration_factor']))+Decimal('.2')*median(r['ratio'] for r in rows))))
                version=repo.change(c,owner,factor,'observation')
                repo.save_change(c,(uuid4(),owner,version,p['walking_duration_factor'],factor,'observation',None,None))
                repo.save_samples(c,owner,version,rows,scope)
                result.update(profile_version=version,updated=True)
        repo.observation_response(c,oid,result)
        return answer(request,result,201)
