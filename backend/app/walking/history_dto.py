"""Trusted internal persistence context and public estimate summary."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.ai.walking_dto import Token


class Internal(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class PlaceRef(Internal):
    place_id: str
    location_version: Annotated[int,Field(ge=1)]


class Context(Internal):
    place_refs: Annotated[list[PlaceRef],Field(max_length=2)]
    verified_at: datetime
    valid_until: datetime


class Usage(Internal):
    input_tokens: Annotated[int,Field(ge=0)] | None=None
    output_tokens: Annotated[int,Field(ge=0)] | None=None
    total_tokens: Annotated[int,Field(ge=0)] | None=None


class ExecutionMetadata(Internal):
    model_version: Literal['gpt-5.6-luna'] | None
    latency_ms: Annotated[int,Field(ge=0)] | None=None
    usage: Usage | None=None


class EstimateSummary(BaseModel):
    estimate_id: UUID
    revision_id: UUID
    base_seconds: float
    applied_duration_factor: float
    estimated_seconds: int
    scope: str
    source: Literal['ai_estimate','profile_recalculation']='ai_estimate'
    reused: Literal[False]=False
    calculated_at: datetime
    expires_at: datetime
    prompt_version: str
    policy_version: str


class EstimateEnvelope(BaseModel):
    data: EstimateSummary
    meta: dict[str,str]


class CacheSource(Internal):
    candidate_id: Token
    provider: Token
    provider_path_ref: Token
    path_version: Token
    origin_entrance_ref: Token
    destination_entrance_ref: Token
    condition_version: Token
