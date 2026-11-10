from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictInt, field_validator

# A type alias: only these two exact strings are valid member types
MemberType = Literal["BASIC", "PREMIUM"]


def _normalize_member_type(value):
    return value.strip().upper() if isinstance(value, str) else value


class MemberCreate(BaseModel):
    #Body of POST /api/members: every field is required

    name: str = Field(..., min_length=1)
    type: MemberType

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return _normalize_member_type(value)


class MemberUpdate(BaseModel):
    #Body of PUT /api/members/{id}: send only the fields you want to change

    name: Optional[str] = Field(None, min_length=1)
    type: Optional[MemberType] = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return _normalize_member_type(value)


class ClassCreate(BaseModel):
    #Body of POST /api/classes: every field is required.

    name: str = Field(..., min_length=1)
    max_capacity: StrictInt = Field(..., gt=0)


class ClassUpdate(BaseModel):
    #Body of PUT /api/classes/{id}: send only the fields you want to change

    name: Optional[str] = Field(None, min_length=1)
    max_capacity: Optional[StrictInt] = Field(None, gt=0)


class BookingCreate(BaseModel):
    #Body of POST /api/classes/{id}/bookings

    member_id: str = Field(..., min_length=1)