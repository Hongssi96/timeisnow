from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,Field,model_validator
from app.arrivals.dto import Evidence

class PersonalWalk(BaseModel):
    estimate_id: UUID
    revision_id: UUID
    base_seconds: float=Field(gt=0)
    applied_duration_factor: float=Field(ge=.5,le=2)
    estimated_seconds: int=Field(gt=0)
    profile_version: int=Field(ge=1)
    source: Literal['ai_estimate','profile_recalculation']
    reused: bool
    expires_at: datetime

class SupplementalWalk(BaseModel):
    role: Literal['transfer','egress']
    connection_id: UUID|None=None
    from_leg_id: UUID
    to_leg_id: UUID|None=None
    source: Literal['walking_route','same_stop']='walking_route'
    provider_seconds: int=Field(ge=0,le=86400)
    walking_seconds: int=Field(ge=0,le=172800)
    applied_duration_factor: float=Field(ge=.5,le=2)
    fetched_at: datetime
    valid_until: datetime

    @model_validator(mode='after')
    def consistent_source(self):
        if self.role=='transfer' and (self.connection_id is None or self.to_leg_id is None):raise ValueError('Missing transfer reference')
        if self.role=='egress' and (self.connection_id is not None or self.to_leg_id is not None):raise ValueError('Invalid egress reference')
        if self.source=='same_stop':
            if self.role!='transfer' or self.provider_seconds!=0 or self.walking_seconds!=0:raise ValueError('Invalid same-stop evidence')
        elif self.provider_seconds<=0 or self.walking_seconds<=0:raise ValueError('Missing walking time')
        if self.valid_until<=self.fetched_at:raise ValueError('Expired walking evidence')
        return self

class TransferCheck(BaseModel):
    connection_id: UUID
    from_leg_id: UUID
    to_leg_id: UUID
    estimated_alighting_at: datetime|None=None
    minimum_boarding_at: datetime|None=None
    next_boarding_at: datetime|None=None
    transfer_walk_seconds: int|None=None
    transfer_buffer_seconds: int
    feasibility: Literal['estimated_feasible','unavailable','unknown']='unknown'
    time_source: Literal['none','receipt_estimate','source_generation']='none'
    reasons: list[str]=[]

class TargetEvaluation(BaseModel):
    model_version: Literal['target.arrival.v1']='target.arrival.v1'
    scope: Literal['selected_routine_candidate']='selected_routine_candidate'
    status: Literal['not_configured','estimated_meets','estimated_late','target_passed','unknown','stale']
    evaluated_at: datetime
    target_arrival_at: datetime|None=None
    estimated_destination_arrival_at: datetime|None=None
    margin_seconds: int|None=None
    egress_seconds: int|None=None
    timing_basis: Literal['none','provider_timeline']='none'
    reasons: list[str]=Field(default_factory=list)

class Departure(BaseModel):
    model_version: Literal['first.departure.v1']='first.departure.v1'
    guidance_id: UUID|None=None
    departure_state: Literal['unconfirmed','reported_departed']='unconfirmed'
    search_id: UUID
    candidate_id: UUID
    first_leg_id: UUID
    status: Literal['ready','insufficient_data','not_enough_time','stale','unsupported']
    departure_basis: Literal['recommended','now']
    calculated_at: datetime
    valid_until: datetime
    recommended_departure_at: datetime|None=None
    selected_departure_at: datetime|None=None
    vehicle_arrival_at: datetime|None=None
    arrival_candidate_id: UUID|None=None
    approach_seconds: int|None=None
    provider_approach_seconds: int|None=None
    applied_duration_factor: float|None=None
    profile_version: int
    approach_basis: Literal['provider_personalized','ai_validated']|None=None
    provider_approach_source: Literal['transit_segment','boarding_walk']|None=None
    approach_fetched_at: datetime|None=None
    approach_valid_until: datetime|None=None
    buffer_seconds: int
    slack_seconds: int|None=None
    slack_status: Literal['meets_buffer','below_buffer','unreachable','unknown']='unknown'
    timing_basis: Literal['none','source_generation','receipt_estimate']='none'
    valid_for_guidance: bool=False
    reasons: list[str]
    connection_status: Literal['not_checked','estimated_feasible','unavailable','unknown','stale']='not_checked'
    transfers: list[TransferCheck]=Field(default_factory=list,max_length=2)
    estimated_final_alighting_at: datetime|None=None
    arrival_evidence: Evidence
    target_evaluation: TargetEvaluation|None=None
    supplemental_walks: list[SupplementalWalk]=Field(default_factory=list,max_length=3)
    personal_walk: PersonalWalk|None=None

class DepartureEnvelope(BaseModel):
    data: Departure
    meta: dict[str,str]
