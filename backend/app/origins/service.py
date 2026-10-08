"""Origin validation rules; numerical GPS policy is deferred."""
from datetime import datetime, timedelta, timezone

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.timeutil import iso
from app.origins import repository
from app.origins.dto import CurrentOrigin, SavedOrigin
from app.places import provider
from app.places.dto import Location
from app.places.service import missing, parsed_id


def manual_assessment(origin, now):
    """Report user choices and timestamps; numerical GPS policy is deferred."""
    current = isinstance(origin, CurrentOrigin)
    return {
        'quality': {
            'assessment': 'unassessed' if current else 'user_selected',
            'confirmation': ('reported' if origin.location_confirmed else 'required') if current else 'not_applicable',
            'numeric_policy': 'deferred',
            'time_relation': ('future' if origin.captured_at > now else 'past_or_present') if current else 'not_applicable',
        },
        'place_match': {'status': 'selected_by_user' if isinstance(origin, SavedOrigin) else 'unconfirmed'},
    }


def validate(request, body):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        _, secret, _ = security.settings()
        security.increment(connection, security.bucket(connection, 'origin-validation', str(user_id), 60, 10, secret))
    with database() as connection:
        security.authenticated(connection, request, True)
        if isinstance(body.origin, SavedOrigin):
            row = repository.find_owned_place(connection, user_id, parsed_id(body.origin.place_id))
            if not row:
                missing()
            if body.origin.location_version is not None and body.origin.location_version != row['location_version']:
                raise AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 선택해주세요.')
            return {'origin': {'type':'saved_place','place_id':str(row['id']),
                'location_version':row['location_version']}, 'label':row['label'],
                'location':{'latitude':row['latitude'],'longitude':row['longitude']},
                'location_address':row['location_address'] or row['address'],
                'quality_status':'not_applicable',
                **manual_assessment(body.origin, datetime.now(timezone.utc)),
                'expires_at':iso(datetime.now(timezone.utc)+timedelta(seconds=600))}
    location = Location(latitude=body.origin.latitude, longitude=body.origin.longitude)
    address = provider.region_for_location(location)
    with database() as connection:
        security.authenticated(connection, request, True)
    now = datetime.now(timezone.utc)
    return {'origin':body.origin.model_dump(mode='json'),
        'label':'현재 위치' if isinstance(body.origin, CurrentOrigin) else '지도 선택 위치',
        'location':location.model_dump(), 'location_address':address,
        'quality_status':('user_confirmed' if body.origin.location_confirmed else 'pending') if isinstance(body.origin, CurrentOrigin) else 'not_applicable',
        **manual_assessment(body.origin, now),
        'expires_at':iso(now+timedelta(seconds=600))}
