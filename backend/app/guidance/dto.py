from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel
from app.arrivals.dto import Evidence

class Departure(BaseModel):
    model_version: Literal['first.departure.v1']='first.departure.v1'
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
    approach_basis: Literal['provider_personalized']|None=None
    buffer_seconds: int
    slack_seconds: int|None=None
    slack_status: Literal['meets_buffer','below_buffer','unreachable','unknown']='unknown'
    timing_basis: Literal['none','source_generation','receipt_estimate']='none'
    valid_for_guidance: bool=False
    reasons: list[str]
    arrival_evidence: Evidence

class DepartureEnvelope(BaseModel):
    data: Departure
    meta: dict[str,str]
