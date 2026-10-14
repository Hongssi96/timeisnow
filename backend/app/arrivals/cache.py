"""Bounded process-local transit context; no device points or persistence."""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
from threading import Lock

@dataclass
class Entry:
    context: dict
    expires_at: datetime
    fingerprint: str
    lock: object = field(default_factory=Lock)
    mapping: object = None
    evidence: object = None
    attempted_at: object = None
    following: dict = field(default_factory=dict)

_searches = OrderedDict()
_guard = Lock()

def fingerprint(candidate):
    return hashlib.sha256(json.dumps(candidate,sort_keys=True).encode()).hexdigest()

def clear():
    with _guard: _searches.clear()

def purge(at):
    for key in list(_searches):
        if _searches[key][0] <= at: del _searches[key]

def publish(user_id,search_id,candidates,contexts,expires_at):
    at=datetime.now(timezone.utc)
    if expires_at<=at: return
    entries={c['candidate_id']:Entry(deepcopy(contexts[c['candidate_id']]),expires_at,fingerprint(c))
             for c in candidates[:20] if c['candidate_id'] in contexts}
    if not entries: return
    with _guard:
        purge(at)
        _searches[(str(user_id),str(search_id))]=(expires_at,entries)
        while len(_searches)>32: _searches.popitem(last=False)

def lookup(user_id,search_id,candidate_id,snapshot,at):
    with _guard:
        purge(at)
        stored=_searches.get((str(user_id),str(search_id)))
        entry=stored[1].get(str(candidate_id)) if stored else None
        return entry if entry and entry.fingerprint==snapshot else None


def following_entry(parent,leg_id):
    contexts=parent.context.get('following',[])
    if not isinstance(contexts,list) or len(contexts)>2:return None
    matching=[item for item in contexts if item.get('first_leg_id')==str(leg_id)]
    if len(matching)!=1:return None
    with _guard:
        if str(leg_id) not in parent.following:
            parent.following[str(leg_id)]=Entry(deepcopy(matching[0]),parent.expires_at,parent.fingerprint)
        return parent.following[str(leg_id)]
