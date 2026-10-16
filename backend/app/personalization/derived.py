"""Recalculate current mapped access from retained base, with zero provider calls."""
from copy import deepcopy
from decimal import Decimal,ROUND_CEILING
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.walking import history_repository as history
from app.personalization import repository
from app.walking.history_service import fingerprint

def recalculate(c,owner,version,factor):
    for row in repository.recalculable(c,owner):
        if not repository.current_places(c,owner,row['place_refs']):continue
        data=deepcopy(row['input_evidence']);result=deepcopy(row['structured_result'])
        data['profile'].update(version=version,validated_duration_factor=factor)
        request_id='profile.rebuild.'+str(uuid4());data['request_id']=request_id
        result['request_id']=request_id
        seconds=int((row['base_seconds']*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
        candidate_id=row['candidate_id']
        # Keep one current candidate in this server-only recalculation execution.
        data['candidates']=[v for v in data['candidates'] if v['candidate_id']==candidate_id]
        result['results']=[v for v in result['results'] if v['candidate_id']==candidate_id]
        if len(data['candidates'])!=1 or len(result['results'])!=1:continue
        result['results'][0].update(base_seconds=float(row['base_seconds']),applied_duration_factor=factor,estimated_seconds=seconds)
        execution=uuid4();now=history.clock(c)
        history.insert_execution(c,(execution,owner,request_id,fingerprint(data),None,row['system_prompt_version'],row['prompt_version'],
          row['policy_version'],version,Jsonb(data),Jsonb(row['context_snapshot']),Jsonb(result),'validated',None,None,None,now,row['execution_retained_until'],Jsonb([])))
        history.insert_recalculation(c,(uuid4(),owner,row['estimate_id'],execution,version,row['base_seconds'],Decimal(str(factor)),seconds,
          row['method'],now,min(row['expires_at'],row['path_expires_at']),min(row['retained_until'],row['path_retained_until']),
          row['id'],candidate_id,owner,row['estimate_id']))
