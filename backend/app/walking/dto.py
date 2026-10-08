from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SearchPoint(Model):
    type: Literal['search_origin', 'search_destination']


class TransitStop(Model):
    type: Literal['transit_stop'] = 'transit_stop'
    leg_id: UUID
    stop_name: str


Endpoint = Annotated[SearchPoint | TransitStop, Field(discriminator='type')]


class Segment(Model):
    segment_id: UUID
    role: Literal['access', 'transfer', 'egress']
    connection_id: UUID | None
    walking_leg_ids: list[UUID]
    from_ref: Endpoint
    to_ref: Endpoint
    provider_duration_seconds: Annotated[int, Field(strict=True, ge=0)] | None
    provider_distance_meters: Annotated[int, Field(strict=True, ge=0)] | None
    source: Literal['provider_estimate', 'missing']
    scope: Literal['provider_walking_segment', 'unknown']
    physical_endpoints: Literal['unconfirmed'] = 'unconfirmed'
    missing_segments: list[Literal['PROVIDER_WALK_MISSING', 'WALK_DURATION_ZERO',
                                 'PHYSICAL_ENDPOINTS_UNCONFIRMED', 'ENTRANCE_PLATFORM_UNCONFIRMED']]


class Evidence(Model):
    model_version: Literal['walking.evidence.v1'] = 'walking.evidence.v1'
    search_id: UUID
    candidate_id: UUID
    expires_at: datetime
    status: Literal['needs_data'] = 'needs_data'
    ready_for_estimation: Literal[False] = False
    reusable: Literal[False] = False
    segments: list[Segment]


class EvidenceEnvelope(Model):
    data: Evidence
    meta: dict[str, str]
