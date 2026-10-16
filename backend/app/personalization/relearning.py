"""Rebuild from surviving samples; preserve the predictions made before learning."""
from collections import defaultdict,deque
from decimal import Decimal
from statistics import median
from types import SimpleNamespace
from uuid import uuid4
from app.personalization import repository as repo,service
from app.trips import repository as trips

def refresh(c,owner,trip,p,confirmation=None):
    old=repo.previous(c,owner,trip['id'])
    if old is None:return None
    body=confirmation if confirmation is not None else old['confirmation']
    if body is None:
        reasons=['CONFIRMATION_REQUIRED'];observed=old['observed_seconds'];evidence=None;ratio=None
    else:
        reasons,observed,evidence,ratio=service.quality(c,owner,trip,trips.events(c,trip['id']),SimpleNamespace(**body),p)
    # Never move a pre-reset observation into the new learning generation.
    if old['generation']!=p['generation'] and 'BEFORE_RESET' not in reasons:reasons.append('BEFORE_RESET')
    value={**old['response'],'status':'excluded' if reasons else 'valid','exclusion_reasons':reasons,
      'observed_seconds':float(observed) if observed is not None else None,'updated':False,'profile_version':p['version'],
      'sample_count':0,'version':old['version']+1}
    repo.refreshed(c,old,body,reasons,observed,evidence,ratio,trip['snapshot']['departure']['approach_seconds'],value)
    return old

def rebuild(c,owner,p):
    rows=repo.rebuild_samples(c,owner,p['generation'])
    all_rows=deque(maxlen=20);segments=defaultdict(lambda:deque(maxlen=20));factor=Decimal('1');used=[];scope=None
    for row in rows:
        all_rows.append(row);segments[row['path_key']].append(row)
        chosen=segments[row['path_key']]
        if len(chosen)<5:chosen=all_rows;scope='same_type'
        else:scope='same_segment'
        if len(chosen)>=5:
            factor=min(Decimal('2'),max(Decimal('.5'),Decimal('.8')*factor+Decimal('.2')*median(r['ratio'] for r in chosen)))
            used=list(chosen)
    # A previously saved factor may contain the removed/corrected sample.
    repo.revoke_restores(c,owner)
    version=repo.change(c,owner,float(factor),'rebuild')
    repo.save_change(c,(uuid4(),owner,version,p['walking_duration_factor'],float(factor),'rebuild',None,None))
    repo.revoke_restores(c,owner)
    repo.save_samples(c,owner,version,used,scope)
    from app.personalization.derived import recalculate
    recalculate(c,owner,version,float(factor))
    return repo.locked(c,owner)
