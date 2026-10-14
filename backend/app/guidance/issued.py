"""Short-lived owner-bound routine guidance tokens; no DB writes on GET."""
from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from uuid import uuid4
from datetime import datetime
from app.arrivals import service as arrivals

_items=OrderedDict()
_guard=Lock()

def publish(binding,route,value,profile):
    if not value.valid_for_guidance:return None
    at=arrivals.now()
    if at>value.valid_until:return None
    identifier=uuid4()
    with _guard:
        for key in list(_items):
            if _items[key]['expires_at']<at:del _items[key]
        _items[str(identifier)]={'user_id':binding.user_id,'binding':binding,'route':deepcopy(route),
            'departure':value.model_dump(mode='json'),'profile':dict(profile),
            'expires_at':min(binding.expires_at,value.valid_until,datetime.fromisoformat(value.model_dump(mode='json')['valid_until'].replace('Z','+00:00')))}
        while len(_items)>128:_items.popitem(last=False)
    return identifier

def owned(user_id,guidance_id):
    with _guard:value=_items.get(str(guidance_id))
    if not value or value['user_id']!=user_id or value['expires_at']<arrivals.now():arrivals.missing()
    return deepcopy(value)
