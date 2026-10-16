from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,AwareDatetime,StrictInt,StrictBool,Field,field_validator,model_validator

class Create(BaseModel):
    model_config=ConfigDict(extra='forbid')
    guidance_id:UUID
    measurement_mode:Literal['assisted','baseline']

class Event(BaseModel):
    model_config=ConfigDict(extra='forbid')
    client_event_id:UUID
    type:Literal['departed','approach_arrived','boarded','alighted','missed','arrived']
    occurred_at:AwareDatetime
    leg_id:UUID
    source:Literal['manual']

    @field_validator('occurred_at',mode='before')
    @classmethod
    def timestamp_text(cls,value):
        if not isinstance(value,str):raise ValueError('ISO timestamp required')
        return value

class Cancel(BaseModel):
    model_config=ConfigDict(extra='forbid')
    outcome:Literal['cancelled']
    expected_version:StrictInt=Field(ge=1)

class RecordMutation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)
    client_request_id:UUID

class EventCorrection(RecordMutation):
    occurred_at:AwareDatetime|None=None
    excluded:StrictBool|None=None
    correction_reason:Literal['timestamp_error','accidental_input','learning_exclusion','learning_restore']
    @field_validator('occurred_at',mode='before')
    @classmethod
    def time_text(cls,value):
        if not isinstance(value,str):raise ValueError('ISO timestamp required')
        return value
    @model_validator(mode='after')
    def fields(self):
        if not self.model_fields_set.intersection({'occurred_at','excluded'}):raise ValueError('Change required')
        if 'excluded' in self.model_fields_set and self.excluded is None:raise ValueError('Boolean required')
        return self

from app.journeys.dto import CurrentLocation
from app.origins.dto import MapOrigin
from typing import Annotated

class RemainingSearch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)
    stage:Literal['before_first_boarding','transfer']
    position_confirmed:Literal[True]
    origin:Annotated[CurrentLocation|MapOrigin,Field(discriminator='type')]

    @field_validator('position_confirmed',mode='before')
    @classmethod
    def confirmation(cls,value):
        if value is not True:raise ValueError('Manual position confirmation required')
        return value
