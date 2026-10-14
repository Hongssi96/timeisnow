"""Meeting core endpoints; flows live in service, envelope assembled here."""
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.common.response import answer
from app.meetings import service
from app.meetings.dto import (ConfirmationInput, InviteIssueInput, InviteTokenInput, MeetingCreateInput,
                              MeetingUpdateInput, TransitionInput)

router = APIRouter(prefix='/api/v1')


@router.post('/meetings', status_code=201)
def create(request: Request, body: MeetingCreateInput):
    return answer(request, service.create(request, body), 201)


@router.get('/meetings')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), status: str | None = Query(default=None),
            cursor: str | None = None):
    return answer(request, service.listing(request, status, cursor, limit))


@router.get('/meetings/{meeting_id}')
def detail(request: Request, meeting_id: str):
    return answer(request, service.detail(request, meeting_id))


@router.patch('/meetings/{meeting_id}')
def update(request: Request, meeting_id: str, body: MeetingUpdateInput):
    return answer(request, service.update(request, meeting_id, body))


@router.post('/meetings/{meeting_id}/confirmations', status_code=201)
def confirm(request: Request, meeting_id: str, body: ConfirmationInput):
    return answer(request, service.confirm(request, meeting_id, body), 201)


@router.post('/meetings/{meeting_id}/transitions')
def transition(request: Request, meeting_id: str, body: TransitionInput):
    return answer(request, service.transition(request, meeting_id, body))


@router.delete('/meetings/{meeting_id}', status_code=202)
def delete(request: Request, meeting_id: str, expected_version: int = Query(ge=1)):
    return answer(request, service.delete(request, meeting_id, expected_version), 202)


@router.post('/meetings/{meeting_id}/invites', status_code=201)
def issue_invite(request: Request, meeting_id: str, body: InviteIssueInput):
    return answer(request, service.issue_invite(request, meeting_id, body), 201)


@router.delete('/meetings/{meeting_id}/invites/{invite_id}')
def revoke_invite(request: Request, meeting_id: str, invite_id: str, expected_version: int = Query(ge=1)):
    service.revoke_invite(request, meeting_id, invite_id, expected_version)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})


@router.post('/meeting-invite-previews')
def preview(request: Request, body: InviteTokenInput):
    return answer(request, service.preview(request, body))


@router.post('/meeting-invite-acceptances')
def accept(request: Request, body: InviteTokenInput):
    return answer(request, service.accept(request, body))


@router.delete('/meetings/{meeting_id}/members/me')
def leave(request: Request, meeting_id: str, expected_version: int = Query(ge=1)):
    service.leave(request, meeting_id, expected_version)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})
