from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,AwareDatetime,StrictInt,Field,field_validator

class Create(BaseModel):
    model_config=ConfigDict(extra='forbid')
    guidance_id:UUID
    measurement_mode:Literal['assisted','baseline']

class Event(BaseModel):
    model_config=ConfigDict(extra='forbid')
    client_event_id:UUID
    type:Literal['departed']
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
