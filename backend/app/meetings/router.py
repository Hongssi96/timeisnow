"""Meeting core endpoints; flows live in MeetingService, envelope assembled here.

서비스는 Depends(get_meeting_service)로 조립돼 주입된다. 엔드포인트는 요청 해석과
응답 봉투만 담당한다.
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.common.response import answer
from app.meetings import guidance as meeting_guidance
from app.meetings.dto import (ArrivalCorrectionInput, ArrivalsInput, ConfirmationInput, GuidanceQueryInput,
                              InviteIssueInput, InviteTokenInput, MeetingCreateInput, MeetingUpdateInput,
                              MemberOriginInput, SharingToggleInput, TransitionInput)
from app.meetings.service import MeetingService
from app.meetings.wiring import get_meeting_service

router = APIRouter(prefix='/api/v1')


@router.post('/meetings', status_code=201)
def create(request: Request, body: MeetingCreateInput, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.create(request, body), 201)


@router.get('/meetings')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), status: str | None = Query(default=None),
            cursor: str | None = None, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.listing(request, status, cursor, limit))


@router.get('/meetings/{meeting_id}')
def detail(request: Request, meeting_id: str, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.detail(request, meeting_id))


@router.patch('/meetings/{meeting_id}')
def update(request: Request, meeting_id: str, body: MeetingUpdateInput,
           service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.update(request, meeting_id, body))


@router.post('/meetings/{meeting_id}/confirmations', status_code=201)
def confirm(request: Request, meeting_id: str, body: ConfirmationInput,
            service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.confirm(request, meeting_id, body), 201)


@router.post('/meetings/{meeting_id}/transitions')
def transition(request: Request, meeting_id: str, body: TransitionInput,
               service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.transition(request, meeting_id, body))


@router.delete('/meetings/{meeting_id}', status_code=202)
def delete(request: Request, meeting_id: str, expected_version: int = Query(ge=1),
           service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.delete(request, meeting_id, expected_version), 202)


@router.post('/meetings/{meeting_id}/invites', status_code=201)
def issue_invite(request: Request, meeting_id: str, body: InviteIssueInput,
                 service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.issue_invite(request, meeting_id, body), 201)


@router.delete('/meetings/{meeting_id}/invites/{invite_id}')
def revoke_invite(request: Request, meeting_id: str, invite_id: str, expected_version: int = Query(ge=1),
                  service: MeetingService = Depends(get_meeting_service)):
    service.revoke_invite(request, meeting_id, invite_id, expected_version)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})


@router.post('/meeting-invite-previews')
def preview(request: Request, body: InviteTokenInput, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.preview(request, body))


@router.post('/meeting-invite-acceptances')
def accept(request: Request, body: InviteTokenInput, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.accept(request, body))


@router.delete('/meetings/{meeting_id}/members/me')
def leave(request: Request, meeting_id: str, expected_version: int = Query(ge=1),
          service: MeetingService = Depends(get_meeting_service)):
    service.leave(request, meeting_id, expected_version)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})


@router.put('/meetings/{meeting_id}/members/me/origin')
def set_origin(request: Request, meeting_id: str, body: MemberOriginInput,
               service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.set_origin(request, meeting_id, body))


@router.get('/meetings/{meeting_id}/members/me/origin')
def get_origin(request: Request, meeting_id: str, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.get_origin(request, meeting_id))


@router.post('/meetings/{meeting_id}/guidance-queries')
def guidance_queries(request: Request, meeting_id: str, body: GuidanceQueryInput):
    return answer(request, meeting_guidance.guidance_query(request, meeting_id, body))


@router.patch('/meetings/{meeting_id}/members/me/sharing')
def set_sharing(request: Request, meeting_id: str, body: SharingToggleInput,
                service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.set_sharing(request, meeting_id, body))


@router.get('/meetings/{meeting_id}/shared-statuses')
def shared_statuses(request: Request, meeting_id: str, service: MeetingService = Depends(get_meeting_service)):
    return answer(request, service.shared_statuses(request, meeting_id))


@router.post('/meetings/{meeting_id}/arrivals', status_code=201)
def create_arrival(request: Request, meeting_id: str, body: ArrivalsInput,
                   service: MeetingService = Depends(get_meeting_service)):
    return service.create_arrival(request, meeting_id, body)


@router.post('/meetings/{meeting_id}/arrival-corrections', status_code=201)
def correct_arrival(request: Request, meeting_id: str, body: ArrivalCorrectionInput,
                    service: MeetingService = Depends(get_meeting_service)):
    return service.correct_arrival(request, meeting_id, body)
