"""FastAPI service for interacting with Google Calendar."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, status
from googleapiclient.errors import HttpError

from calendar_app.config import Settings, get_settings
from calendar_app.day_plans import DAY_PLANS, get_plan, list_plan_ids
from calendar_app.google_client import GoogleCalendarClient, GoogleCredentialsError
from calendar_app.models import (
    ApiErrorResponse,
    DayPlanRequest,
    EventCreateRequest,
    EventDeleteRequest,
    EventUpdateRequest,
    FreeBusyRequest,
)
from calendar_app.security import verify_api_key

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Local Calendar Service",
    version="1.0.0",
    description=(
        "A lightweight FastAPI wrapper around Google Calendar that supports creating, "
        "updating, deleting events, checking free/busy, and applying simple day plans."
    ),
)


def get_client() -> GoogleCalendarClient:
    """FastAPI dependency that returns a Google Calendar client."""

    return GoogleCalendarClient()


@app.on_event("startup")
def startup_event() -> None:
    """Validate configuration when the service starts."""

    settings = get_settings()
    logger.info("Calendar service starting. Calendar ID: %s", settings.calendar_id)


@app.get("/health", tags=["meta"])
def health() -> Dict[str, str]:
    """Simple health check endpoint."""

    return {"status": "ok"}


def _get_timezone(settings: Settings, override: Optional[str]) -> ZoneInfo:
    tz_name = override or settings.default_timezone
    try:
        return ZoneInfo(tz_name)
    except Exception as exc:  # pragma: no cover - depends on system tz database
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown timezone '{tz_name}'.",
        ) from exc


def _parse_datetime(value: Optional[str], tz: ZoneInfo) -> Optional[datetime]:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: '{value}'. Use ISO-8601 (e.g. 2024-05-20T09:30:00-04:00).",
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _event_time_payload(dt: datetime, timezone: str) -> Dict[str, str]:
    return {"dateTime": dt.isoformat(), "timeZone": timezone}


def _attendees_payload(attendees: Optional[List[str]]) -> Optional[List[Dict[str, str]]]:
    if not attendees:
        return None
    return [{"email": email} for email in attendees]


def _handle_google_error(exc: HttpError) -> None:
    status_code = exc.resp.status if exc.resp else status.HTTP_502_BAD_GATEWAY
    detail = "Google Calendar API error"
    try:
        if exc.resp and exc.resp.reason:
            detail = f"Google API error: {exc.resp.reason}"
    except Exception:  # pragma: no cover - defensive
        detail = "Google Calendar API error"
    raise HTTPException(status_code=status_code, detail=detail) from exc


@app.post(
    "/events.create",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Event created"},
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
        500: {"model": ApiErrorResponse},
    },
    tags=["events"],
)
def create_event(
    request: EventCreateRequest,
    client: GoogleCalendarClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
):
    tz = _get_timezone(settings, request.timezone)
    timezone_name = request.timezone or settings.default_timezone

    start_dt = _parse_datetime(request.start_iso, tz) or datetime.now(tz)

    if request.end_iso:
        end_dt = _parse_datetime(request.end_iso, tz)
    else:
        duration = request.duration_min or settings.default_duration_min
        end_dt = start_dt + timedelta(minutes=duration)

    if end_dt <= start_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event end time must be after the start time.",
        )

    event_body: Dict[str, Optional[Dict[str, str]]] = {
        "summary": request.title,
        "start": _event_time_payload(start_dt, timezone_name),
        "end": _event_time_payload(end_dt, timezone_name),
    }
    if request.description is not None:
        event_body["description"] = request.description
    if request.location is not None:
        event_body["location"] = request.location
    attendees_payload = _attendees_payload(request.attendees)
    if attendees_payload is not None:
        event_body["attendees"] = attendees_payload

    add_meet = (
        request.add_google_meet
        if request.add_google_meet is not None
        else settings.default_add_google_meet
    )
    if add_meet:
        event_body["conferenceData"] = client.build_conference_request()

    try:
        created = client.create_event(event_body, conference=add_meet)
    except GoogleCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except HttpError as exc:  # pragma: no cover - network call
        _handle_google_error(exc)

    return created


def _load_existing_event(
    client: GoogleCalendarClient, event_id: str, tz: ZoneInfo
) -> Dict[str, datetime]:
    existing = client.get_event(event_id)
    try:
        start_raw = existing["start"]["dateTime"]
        end_raw = existing["end"]["dateTime"]
    except KeyError as exc:  # pragma: no cover - only triggered for all-day events
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All-day events are not supported by this endpoint.",
        ) from exc
    start_dt = _parse_datetime(start_raw, tz)
    end_dt = _parse_datetime(end_raw, tz)
    assert start_dt and end_dt
    return {"start": start_dt, "end": end_dt}


@app.post(
    "/events.update",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Event updated"},
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
    tags=["events"],
)
def update_event(
    request: EventUpdateRequest,
    client: GoogleCalendarClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
):
    tz = _get_timezone(settings, request.timezone)
    timezone_name = request.timezone or settings.default_timezone

    body: Dict[str, object] = {}
    if request.title is not None:
        body["summary"] = request.title
    if request.description is not None:
        body["description"] = request.description
    if request.location is not None:
        body["location"] = request.location

    if request.attendees is not None:
        body["attendees"] = _attendees_payload(request.attendees) or []
    elif request.clear_attendees:
        body["attendees"] = []

    start_dt = _parse_datetime(request.start_iso, tz)
    end_dt = _parse_datetime(request.end_iso, tz)

    existing_times: Optional[Dict[str, datetime]] = None

    if request.duration_min is not None:
        if start_dt is not None:
            end_dt = start_dt + timedelta(minutes=request.duration_min)
        else:
            if existing_times is None:
                existing_times = _load_existing_event(client, request.event_id, tz)
            start_dt = existing_times["start"]
            end_dt = start_dt + timedelta(minutes=request.duration_min)

    if start_dt is not None and end_dt is None:
        if existing_times is None:
            existing_times = _load_existing_event(client, request.event_id, tz)
        duration = existing_times["end"] - existing_times["start"]
        end_dt = start_dt + duration

    if end_dt is not None and start_dt is None:
        if existing_times is None:
            existing_times = _load_existing_event(client, request.event_id, tz)
        start_dt = existing_times["start"]

    if start_dt is not None and end_dt is not None:
        if end_dt <= start_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after the start time.",
            )
        body["start"] = _event_time_payload(start_dt, timezone_name)
        body["end"] = _event_time_payload(end_dt, timezone_name)

    add_meet = request.add_google_meet
    conference_flag = False
    if add_meet is not None:
        if add_meet:
            body["conferenceData"] = client.build_conference_request()
            conference_flag = True
        else:
            body["conferenceData"] = None
            conference_flag = True

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields were provided.",
        )

    try:
        updated = client.patch_event(request.event_id, body, conference=conference_flag)
    except GoogleCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except HttpError as exc:  # pragma: no cover - network call
        if exc.resp and exc.resp.status == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        _handle_google_error(exc)

    return updated


@app.post(
    "/events.delete",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Event deleted"},
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
    tags=["events"],
)
def delete_event(
    request: EventDeleteRequest,
    client: GoogleCalendarClient = Depends(get_client),
):
    try:
        client.delete_event(request.event_id)
    except GoogleCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except HttpError as exc:  # pragma: no cover - network call
        if exc.resp and exc.resp.status == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        _handle_google_error(exc)

    return {"status": "deleted", "event_id": request.event_id}


@app.post(
    "/freebusy.query",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Free/busy response from Google"},
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
    },
    tags=["availability"],
)
def freebusy(
    request: FreeBusyRequest,
    client: GoogleCalendarClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
):
    tz = _get_timezone(settings, request.timezone)
    time_min = _parse_datetime(request.time_min_iso, tz)
    time_max = _parse_datetime(request.time_max_iso, tz)

    if time_min is None or time_max is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both time_min_iso and time_max_iso are required.",
        )

    if time_max <= time_min:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_max_iso must be after time_min_iso.",
        )

    try:
        response = client.freebusy(
            time_min=time_min.isoformat(),
            time_max=time_max.isoformat(),
            calendars=request.calendars,
            timezone=request.timezone or settings.default_timezone,
        )
    except GoogleCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except HttpError as exc:  # pragma: no cover
        _handle_google_error(exc)

    return response


@app.post(
    "/dayplan.apply",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Day plan applied"},
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
    },
    tags=["dayplans"],
)
def apply_day_plan(
    request: DayPlanRequest,
    client: GoogleCalendarClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
):
    tz = _get_timezone(settings, request.timezone)
    timezone_name = request.timezone or settings.default_timezone

    if request.blocks:
        blocks = request.blocks
    elif request.plan_id:
        try:
            blocks = get_plan(request.plan_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either plan_id or blocks must be provided.",
        )

    attendees_override = request.attendees or []

    applied_events = []
    previous_end: Optional[datetime] = None

    for block in blocks:
        block_attendees = block.attendees or attendees_override or None

        if block.start_time:
            try:
                hours, minutes = [int(part) for part in block.start_time.split(":", maxsplit=1)]
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_time '{block.start_time}'. Use HH:MM format.",
                ) from exc
            start_dt = datetime(
                request.date.year,
                request.date.month,
                request.date.day,
                hours,
                minutes,
                tzinfo=tz,
            )
        else:
            if previous_end is None:
                start_dt = datetime(
                    request.date.year,
                    request.date.month,
                    request.date.day,
                    9,
                    0,
                    tzinfo=tz,
                )
            else:
                start_dt = previous_end

        end_dt = start_dt + timedelta(minutes=block.duration_min)
        previous_end = end_dt

        event_body = {
            "summary": block.title,
            "start": _event_time_payload(start_dt, timezone_name),
            "end": _event_time_payload(end_dt, timezone_name),
        }
        if block.description is not None:
            event_body["description"] = block.description
        if block.location is not None:
            event_body["location"] = block.location
        attendees_payload = _attendees_payload(block_attendees)
        if attendees_payload is not None:
            event_body["attendees"] = attendees_payload

        add_meet = (
            block.add_google_meet
            if block.add_google_meet is not None
            else settings.default_add_google_meet
        )
        if add_meet:
            event_body["conferenceData"] = client.build_conference_request()

        try:
            created = client.create_event(event_body, conference=add_meet)
        except GoogleCredentialsError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        except HttpError as exc:  # pragma: no cover
            _handle_google_error(exc)

        applied_events.append(created)

    return {"applied": len(applied_events), "events": applied_events, "plan_id": request.plan_id}


@app.get(
    "/dayplan.templates",
    dependencies=[Depends(verify_api_key)],
    tags=["dayplans"],
)
def list_day_plans():
    """List available built-in day plan templates."""

    return {"plans": {plan_id: [block.model_dump() for block in DAY_PLANS[plan_id]] for plan_id in list_plan_ids()}}
