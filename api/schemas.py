from typing import Literal

from pydantic import BaseModel, Field, StrictInt, field_validator

class MemberPayload(BaseModel):
    
    name: str = Field(..., min_length=1)
    type: Literal["BASIC", "PREMIUM"]

    @field_validator("type", mode="before")
    
    @classmethod
    def normalize_type(cls, value):
        return value.strip().upper() if isinstance(value, str) else value
    
class ClassPayload(BaseModel):

    name: str = Field(..., min_length=1)
    max_capacity: StrictInt = Field(..., gt=0)


class BookingCreate(BaseModel):
    member_id: str = Field(..., min_length=1)