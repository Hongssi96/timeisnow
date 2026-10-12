"""Strict, coordinate-free internal walking input and model output contracts."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Token = Annotated[str, Field(min_length=1, max_length=200, pattern=r'^[A-Za-z0-9_.:-]+$')]
Code = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Z0-9_]+$')]
Positive = Annotated[float, Field(gt=0)]
IDs = Annotated[list[Token], Field(max_length=20)]
Codes = Annotated[list[Code], Field(max_length=20)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Profile(Model):
    version: Annotated[int, Field(ge=1)]
    validated_duration_factor: Annotated[float, Field(ge=0.5, le=2.0)] | None
    valid_factor_range: list[float]
    fallback_speed_mps: Positive | None

    @model_validator(mode='after')
    def fixed_range(self):
        if self.valid_factor_range != [0.5, 2.0]:
            raise ValueError('PROFILE_RANGE_INVALID')
        return self


class Candidate(Model):
    candidate_id: Token
    origin_ref: Token
    destination_ref: Token
    direction: Token
    scope: Token
    required_scope: Token
    is_walkable_route: bool
    distance_meters: Positive | None
    provider_duration_seconds: Positive | None
    provider_duration_includes_personalization: bool
    evidence_ids: IDs
    missing_segments: Codes

    @model_validator(mode='after')
    def unique_evidence(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or len(set(self.missing_segments)) != len(self.missing_segments):
            raise ValueError('DUPLICATE_EVIDENCE')
        return self


class EstimateInput(Model):
    request_id: Token
    policy_version: Literal['walk-policy.v1']
    profile: Profile
    candidates: Annotated[list[Candidate], Field(min_length=1, max_length=20)]

    @model_validator(mode='after')
    def unique_candidates(self):
        ids = [item.candidate_id for item in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError('DUPLICATE_CANDIDATE')
        return self


class Result(Model):
    candidate_id: Token
    status: Literal['ok', 'needs_data', 'unsupported']
    origin_ref: Token
    destination_ref: Token
    direction: Token
    scope: Token
    base_seconds: Positive | None
    applied_duration_factor: Annotated[float, Field(ge=0.5, le=2.0)] | None
    estimated_seconds: Annotated[int, Field(gt=0)] | None
    method: Literal['provider_duration', 'distance_speed', 'none']
    evidence_ids: IDs
    missing_segments: Annotated[list[Code], Field(max_length=32)]
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class EstimateOutput(Model):
    request_id: Token
    prompt_version: Literal['walking_estimate.v1']
    results: Annotated[list[Result], Field(min_length=1, max_length=20)]
