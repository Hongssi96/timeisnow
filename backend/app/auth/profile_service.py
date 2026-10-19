"""Owned preferences; learning coefficients and recorded journeys stay server-controlled."""
from app.auth import repository,security
from app.common.database import database
from app.common.errors import AuthError
from app.personalization.repository import locked
from app.personalization.derived import recalculate


def update(request,body):
    with database() as connection:
        owner=security.authenticated(connection,request,write=True)
        current=locked(connection,owner,maintain=False)
        if current['version']!=body.expected_version:
            raise AuthError(409,'VERSION_CONFLICT','설정이 변경됐어요. 최신 설정을 다시 확인해주세요.')
        changes=body.model_dump(exclude_unset=True,exclude={'expected_version'})
        if any(current[key]!=value for key,value in changes.items()):
            profile=repository.update_profile(connection,owner,{**current,**changes})
            recalculate(connection,owner,profile['version'],profile['walking_duration_factor'])
        else:
            profile=repository.find_profile(connection,owner)
        profile.pop('user_id')
        return {'profile':profile,'profile_version':profile['version']}
