"""Composition root: builds MeetingService with its concrete adapters.

엔드포인트는 get_meeting_service 의존성을 통해 조립된 서비스를 받는다.
테스트는 build_meeting_service에 다른 구현체를 넘겨 협업 객체를 교체한다.
"""
from app.common.ports import (Clock, Database, Identity, PostgresDatabase, SessionIdentity,
                              TokenIssuer, UtcClock, UrlSafeTokenIssuer)
from app.meetings.repository import MeetingRepository, PostgresMeetingRepository
from app.meetings.service import MeetingService


def build_meeting_service(repository: MeetingRepository | None = None, database: Database | None = None,
                          identity: Identity | None = None, clock: Clock | None = None,
                          tokens: TokenIssuer | None = None) -> MeetingService:
    """Overrides let tests replace any collaborator; production uses the defaults."""
    return MeetingService(
        repository=repository or PostgresMeetingRepository(),
        database=database or PostgresDatabase(),
        identity=identity or SessionIdentity(),
        clock=clock or UtcClock(),
        tokens=tokens or UrlSafeTokenIssuer(),
    )


def get_meeting_service() -> MeetingService:
    """FastAPI dependency; Depends(get_meeting_service) in the router."""
    return build_meeting_service()
