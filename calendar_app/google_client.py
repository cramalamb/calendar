"""Google Calendar client helpers."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from .config import Settings, get_settings

TOKEN_PATH = Path("token.json")


class GoogleCredentialsError(RuntimeError):
    """Raised when Google credentials are missing or invalid."""


def _load_credentials(settings: Settings) -> Credentials:
    if not TOKEN_PATH.exists():
        raise GoogleCredentialsError(
            "token.json not found. Run `python oauth_bootstrap.py` to generate it."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), settings.google_scopes)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as exc:  # pragma: no cover - network error handling
                raise GoogleCredentialsError(
                    "Unable to refresh credentials. Re-run oauth_bootstrap.py."
                ) from exc
        else:
            raise GoogleCredentialsError(
                "Stored credentials are invalid. Re-run oauth_bootstrap.py to refresh the token."
            )
    return creds


def build_calendar_service(settings: Optional[Settings] = None) -> Resource:
    """Create a Google Calendar API service resource."""

    settings = settings or get_settings()
    creds = _load_credentials(settings)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


class GoogleCalendarClient:
    """Thin wrapper around the Google Calendar API."""

    def __init__(self, calendar_id: Optional[str] = None, service: Optional[Resource] = None):
        self.settings = get_settings()
        self.calendar_id = calendar_id or self.settings.calendar_id
        self._service = service or build_calendar_service(self.settings)

    @property
    def service(self) -> Resource:
        return self._service

    def create_event(self, body: Dict[str, Any], *, conference: bool = False) -> Dict[str, Any]:
        kwargs = {
            "calendarId": self.calendar_id,
            "body": body,
        }
        if conference:
            kwargs["conferenceDataVersion"] = 1
        return self.service.events().insert(**kwargs).execute()

    def patch_event(
        self, event_id: str, body: Dict[str, Any], *, conference: bool = False
    ) -> Dict[str, Any]:
        kwargs = {
            "calendarId": self.calendar_id,
            "eventId": event_id,
            "body": body,
        }
        if conference:
            kwargs["conferenceDataVersion"] = 1
        return self.service.events().patch(**kwargs).execute()

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()

    def get_event(self, event_id: str) -> Dict[str, Any]:
        return self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()

    def freebusy(
        self,
        *,
        time_min: str,
        time_max: str,
        calendars: Optional[Iterable[str]] = None,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in (calendars or [self.calendar_id])],
        }
        if timezone:
            body["timeZone"] = timezone
        return self.service.freebusy().query(body=body).execute()

    @staticmethod
    def build_conference_request() -> Dict[str, Any]:
        """Return a conferenceData payload that requests a Meet link."""

        return {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }


__all__ = ["GoogleCalendarClient", "GoogleCredentialsError", "build_calendar_service"]
