"""Coordinate-free shared journey model; provider estimates remain unverified."""
from typing import Annotated, Literal
from datetime import datetime
from uuid import UUID, uuid5
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

from app.common.errors import AuthError

Seconds = Annotated[int, Field(strict=True, ge=0)]
Name = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Stop(Model):
    name: Name
    public_id: None = None
    entrance_ref: None = None
    platform_ref: None = None


class Direction(Model):
    source: Literal['provider_stop_order','unknown']
    from_stop_name: Name | None = None
    to_stop_name: Name | None = None
    public_direction_id: None = None


class Vehicle(Model):
    name: Name
    provider_type: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)] | None = None


class LegacyLeg(Model):
    leg_id: UUID
    sequence: Seconds
    type: Literal['WALKING','BUS','SUBWAY']
    seconds: Seconds
    distance_meters: Seconds
    stops: list[Name] = Field(max_length=500)
    vehicles: list[Name] = Field(max_length=500)
    time_source: Literal['provider_estimate']


class Leg(LegacyLeg):
    walking_role: Literal['access','transfer','egress'] | None
    boarding: Stop | None
    alighting: Stop | None
    direction: Direction
    vehicle_options: list[Vehicle] = Field(max_length=500)

    @model_validator(mode='after')
    def evidence(self):
        if self.type == 'WALKING':
            if (self.walking_role is None or self.boarding is not None or self.alighting is not None
                or self.stops or self.vehicles or self.vehicle_options
                or self.direction != Direction(source='unknown')):
                raise ValueError('Invalid walking evidence')
        elif (self.walking_role is not None or len(self.stops) < 2 or not self.vehicles
              or self.boarding != Stop(name=self.stops[0]) or self.alighting != Stop(name=self.stops[-1])
              or self.direction != Direction(source='provider_stop_order',from_stop_name=self.stops[0],to_stop_name=self.stops[-1])
              or [v.name for v in self.vehicle_options] != self.vehicles):
            raise ValueError('Invalid transit evidence')
        return self


class Connection(Model):
    connection_id: UUID
    from_leg_id: UUID
    to_leg_id: UUID
    from_stop: Stop
    to_stop: Stop
    walking_leg_ids: list[UUID] = Field(max_length=500)
    walking_seconds: Seconds | None
    feasibility: Literal['unknown'] = 'unknown'
    time_source: Literal['provider_estimate'] = 'provider_estimate'
    physical_stop_match: Literal['unconfirmed'] = 'unconfirmed'


class Breakdown(Model):
    walking_seconds: Seconds
    in_vehicle_seconds: Seconds
    legs_total_seconds: Seconds
    provider_total_seconds: Seconds
    unallocated_seconds: Seconds | None
    status: Literal['consistent','unallocated','inconsistent']


class LegacyCandidate(Model):
    candidate_id: UUID
    type: Literal['BUS','SUBWAY','BUS_AND_SUBWAY']
    validity: Literal['insufficient_data']
    ordered_legs: list[LegacyLeg] = Field(min_length=1, max_length=500)
    transfer_count: Seconds
    total_seconds: Seconds
    total_distance_meters: Seconds
    walking_seconds: Seconds
    estimated_arrival_at: None
    time_sources: list[Literal['provider_estimate']] = Field(min_length=1, max_length=1)
    missing_segments: list[Annotated[str, StringConstraints(strict=True, pattern=r'^[A-Z_]{1,64}$')]] = Field(max_length=32)


def structural(legs):
    transit = [i for i,leg in enumerate(legs) if leg.type != 'WALKING']
    if not transit or [leg.sequence for leg in legs] != list(range(len(legs))) or len({leg.leg_id for leg in legs}) != len(legs):
        raise ValueError('Invalid leg ordering')
    types = {legs[i].type for i in transit}
    kind = 'BUS_AND_SUBWAY' if len(types) == 2 else next(iter(types))
    return transit, kind


def connection(candidate_id, legs, before, after):
    walks = legs[before+1:after]
    return Connection(connection_id=uuid5(candidate_id,f'connection:{legs[before].leg_id}:{legs[after].leg_id}'),
        from_leg_id=legs[before].leg_id,to_leg_id=legs[after].leg_id,
        from_stop=Stop(name=legs[before].stops[-1]),to_stop=Stop(name=legs[after].stops[0]),
        walking_leg_ids=[leg.leg_id for leg in walks],walking_seconds=sum(leg.seconds for leg in walks) if walks else None)


def breakdown(legs, total):
    walking = sum(leg.seconds for leg in legs if leg.type == 'WALKING')
    in_vehicle = sum(leg.seconds for leg in legs if leg.type != 'WALKING')
    difference = total - walking - in_vehicle
    return Breakdown(walking_seconds=walking,in_vehicle_seconds=in_vehicle,legs_total_seconds=walking+in_vehicle,
        provider_total_seconds=total,unallocated_seconds=difference if difference >= 0 else None,
        status='consistent' if difference == 0 else 'unallocated' if difference > 0 else 'inconsistent')


def extra_reasons(legs, transit, transfers, timing):
    reasons = ['PUBLIC_DIRECTION_UNVERIFIED']
    if transit[0] == 0: reasons.append('ACCESS_WALK_MISSING')
    if transit[-1] == len(legs)-1: reasons.append('EGRESS_WALK_MISSING')
    if any(after == before+1 for before,after in zip(transit,transit[1:])): reasons.append('TRANSFER_WALK_MISSING')
    if transfers != len(transit)-1: reasons.append('TRANSFER_COUNT_MISMATCH')
    if timing.status == 'inconsistent': reasons.append('DURATION_TOTAL_MISMATCH')
    return reasons


class Candidate(LegacyCandidate):
    model_version: Literal['journey.v1']
    ordered_legs: list[Leg] = Field(min_length=1,max_length=500)
    transfer_count: Annotated[int, Field(strict=True, ge=0, le=2)]
    transfer_count_computed: Annotated[int, Field(strict=True, ge=0, le=2)]
    connections: list[Connection] = Field(max_length=499)
    timing_breakdown: Breakdown

    @model_validator(mode='after')
    def continuity(self):
        legs = self.ordered_legs
        transit,kind = structural(legs)
        timing = breakdown(legs,self.total_seconds)
        if (self.type != kind or self.transfer_count_computed != len(transit)-1
            or self.walking_seconds != timing.walking_seconds or self.timing_breakdown != timing):
            raise ValueError('Invalid candidate totals')
        for index,leg in enumerate(legs):
            role = 'access' if index < transit[0] else 'egress' if index > transit[-1] else 'transfer'
            if leg.type == 'WALKING' and leg.walking_role != role: raise ValueError('Invalid walking role')
        expected = [connection(self.candidate_id,legs,before,after) for before,after in zip(transit,transit[1:])]
        if self.connections != expected or not set(extra_reasons(legs,transit,self.transfer_count,timing)).issubset(self.missing_segments):
            raise ValueError('Invalid connections')
        return self


class SearchResult(Model):
    search_id: UUID
    job_id: UUID
    status: Literal['queued','running','succeeded','failed']
    candidates: list[Candidate] = Field(max_length=20)
    unavailable_reasons: list[str]
    error: dict | None
    expires_at: datetime


class SearchEnvelope(Model):
    data: SearchResult
    meta: dict[str,str]


def common_candidate(value, vehicle_options=None):
    """Read legacy candidates without changing their IDs or making provider calls."""
    try:
        if 'model_version' in value:
            return Candidate.model_validate(value).model_dump(mode='json')
        old = LegacyCandidate.model_validate(value)
        transit,kind = structural(old.ordered_legs)
        if kind != old.type: raise ValueError('Provider route type mismatch')
        legs = []
        for index,leg in enumerate(old.ordered_legs):
            walking = leg.type == 'WALKING'
            if not walking and (len(leg.stops) < 2 or not leg.vehicles): raise ValueError('Missing stops')
            data = leg.model_dump(mode='json')
            # A walking step must not leak provider stop/vehicle labels or location text.
            if walking: data.update(stops=[],vehicles=[])
            options = (vehicle_options or {}).get(str(leg.leg_id),[{'name':name,'provider_type':None} for name in leg.vehicles])
            legs.append(Leg(**data,walking_role=('access' if index < transit[0] else 'egress' if index > transit[-1] else 'transfer') if walking else None,
                boarding=Stop(name=leg.stops[0]) if not walking else None,alighting=Stop(name=leg.stops[-1]) if not walking else None,
                direction=Direction(source='unknown') if walking else Direction(source='provider_stop_order',from_stop_name=leg.stops[0],to_stop_name=leg.stops[-1]),
                vehicle_options=[] if walking else options))
        timing = breakdown(legs,old.total_seconds)
        reasons = list(dict.fromkeys(old.missing_segments + extra_reasons(legs,transit,old.transfer_count,timing)))
        data = old.model_dump(mode='json');data['ordered_legs'] = [leg.model_dump(mode='json') for leg in legs]
        data['missing_segments'] = reasons
        return Candidate(**data,model_version='journey.v1',transfer_count_computed=len(transit)-1,
            connections=[connection(old.candidate_id,legs,before,after) for before,after in zip(transit,transit[1:])],
            timing_breakdown=timing).model_dump(mode='json')
    except (ValidationError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        raise AuthError(502,'PROVIDER_RESPONSE_INVALID','경로 구간을 확인할 수 없어요.') from None
