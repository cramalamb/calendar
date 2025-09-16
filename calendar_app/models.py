"""Pydantic models used by the calendar API."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EventBase(BaseModel):
    """Shared fields for event create/update requests."""

    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(
        default=None, description="Optional description/agenda for the event."
    )
    location: Optional[str] = Field(default=None, description="Where the event takes place.")
    attendees: Optional[List[EmailStr]] = Field(
        default=None, description="Email addresses of attendees to invite."
    )
    add_google_meet: Optional[bool] = Field(
        default=None,
        description="Whether to attach a Google Meet link. Defaults to server configuration.",
    )
    timezone: Optional[str] = Field(
        default=None,
        description="IANA timezone identifier to use when interpreting provided times.",
    )


class EventCreateRequest(EventBase):
    start_iso: Optional[str] = Field(
        default=None,
        description="ISO-8601 start datetime (if omitted, uses now).",
    )
    end_iso: Optional[str] = Field(
        default=None,
        description="ISO-8601 end datetime. If omitted, duration_min is required.",
    )
    duration_min: Optional[int] = Field(
        default=None,
        ge=1,
        description="Duration in minutes. Used when end_iso is not provided.",
    )

    @field_validator("start_iso", mode="before")
    @classmethod
    def _strip(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("end_iso", mode="before")
    @classmethod
    def _strip_end(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value


class EventUpdateRequest(EventBase):
    event_id: str = Field(..., description="Identifier of the event to update.")
    start_iso: Optional[str] = Field(
        default=None, description="Updated start datetime in ISO-8601 format."
    )
    end_iso: Optional[str] = Field(
        default=None, description="Updated end datetime in ISO-8601 format."
    )
    duration_min: Optional[int] = Field(
        default=None,
        ge=1,
        description="Duration used with a provided start time to compute the end time.",
    )
    clear_attendees: bool = Field(
        default=False,
        description="If true and attendees is omitted, existing attendees are removed.",
    )

    @field_validator("event_id", mode="before")
    @classmethod
    def _strip_event_id(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if not value:
            raise ValueError("event_id cannot be blank")
        return value


class EventDeleteRequest(BaseModel):
    event_id: str = Field(..., description="Identifier of the event to delete.")

    @field_validator("event_id", mode="before")
    @classmethod
    def _strip_event_id(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if not value:
            raise ValueError("event_id cannot be blank")
        return value


class FreeBusyRequest(BaseModel):
    time_min_iso: str = Field(..., description="ISO-8601 start datetime for the query range.")
    time_max_iso: str = Field(..., description="ISO-8601 end datetime for the query range.")
    calendars: Optional[List[str]] = Field(
        default=None,
        description="Optional list of calendar IDs to check. Defaults to configured calendar.",
    )
    timezone: Optional[str] = Field(
        default=None, description="Timezone identifier to force in the response."
    )


class DayPlanBlock(BaseModel):
    title: str = Field(..., description="Summary/title for the event block.")
    start_time: Optional[str] = Field(
        default=None,
        description="Start time for the block in HH:MM 24h format. If omitted the block is sequential.",
    )
    duration_min: int = Field(..., ge=1, description="Duration of the block in minutes.")
    description: Optional[str] = Field(default=None, description="Optional description/agenda.")
    add_google_meet: Optional[bool] = Field(
        default=None,
        description="Whether to attach a Meet link for this block.",
    )
    location: Optional[str] = Field(default=None, description="Optional location for the block.")
    attendees: Optional[List[EmailStr]] = Field(
        default=None, description="Optional attendees specific to this block."
    )


class DayPlanRequest(BaseModel):
    date: date = Field(..., description="Date to apply the day plan to.")
    plan_id: Optional[str] = Field(
        default=None,
        description="Identifier of a built-in plan. If omitted, blocks must be provided.",
    )
    blocks: Optional[List[DayPlanBlock]] = Field(
        default=None,
        description="Explicit blocks for the plan. Overrides plan_id when provided.",
    )
    timezone: Optional[str] = Field(
        default=None, description="Timezone to interpret the plan date/times in."
    )
    attendees: Optional[List[EmailStr]] = Field(
        default=None,
        description="Optional attendees applied to every block that does not override attendees.",
    )

    @field_validator("plan_id")
    @classmethod
    def _normalize_plan_id(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ApiErrorResponse(BaseModel):
    detail: str
