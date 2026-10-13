from datetime import datetime
from typing import Annotated,Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field
from app.ai.walking_dto import Token

class Mapping(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    provider: Literal['gyeonggi-bus']
    first_leg_id: UUID
    station_id: Annotated[str,Field(pattern=r'^[1-9][0-9]{0,19}$')]
    route_id: Annotated[str,Field(pattern=r'^[1-9][0-9]{0,19}$')]
    sta_order: Annotated[int,Field(ge=1,le=1000)]
    route_dest_id: Annotated[str,Field(pattern=r'^[1-9][0-9]{0,19}$')]
    mapping_version: Token
    verified_at: datetime
    valid_until: datetime

class Arrival(BaseModel):
    candidate_id: UUID
    provider_prediction_seconds: int
    remaining_seconds: int|None=None
    predicted_arrival_at: datetime|None

class Evidence(BaseModel):
    model_version: Literal['arrival.evidence.v2']='arrival.evidence.v2'
    search_id: UUID
    candidate_id: UUID
    first_leg_id: UUID
    status: Literal['mapping_required','unsupported','no_arrivals','insufficient_data','fresh','estimated','expired']
    source_status: Literal['unknown','fresh','stale','clock_mismatch']='unknown'
    timing_basis: Literal['none','source_generation','receipt_estimate']='none'
    received_at: datetime|None=None
    generated_at: datetime|None=None
    expires_at: datetime
    valid_for_guidance: bool=False
    reasons: list[str]
    candidates: list[Arrival]=[]

class Envelope(BaseModel):
    data: Evidence
    meta: dict[str,str]
