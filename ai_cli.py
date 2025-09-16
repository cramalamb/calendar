"""Command line helper that turns natural language into API calls."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import httpx
import typer
from openai import OpenAI

from calendar_app.config import get_settings

SYSTEM_PROMPT = """
You are a helpful assistant that converts natural language scheduling requests into JSON API
calls for a FastAPI calendar service. Always respond with a JSON object using the schema:
{
  "endpoint": "<path starting with />",
  "method": "POST" | "GET",
  "payload": { ... JSON payload ... }
}

The available endpoints are:
1. POST /events.create – create an event. payload keys include title, start_iso, duration_min,
   add_google_meet, description, attendees (list of emails), timezone, location.
2. POST /events.update – update an event. payload must include event_id and can include the same
   fields as create plus clear_attendees.
3. POST /events.delete – delete an event by event_id.
4. POST /freebusy.query – check availability with time_min_iso, time_max_iso, optional calendars.
5. POST /dayplan.apply – apply a day plan. payload can include plan_id or blocks (array of blocks
   with title, start_time, duration_min) plus timezone and attendees.

Return only JSON, no additional commentary.
"""

app = typer.Typer(add_completion=False)


def _load_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise typer.BadParameter(
            "OPENAI_API_KEY is not set. Export it or add it to your .env before running the CLI."
        )
    return OpenAI(api_key=api_key)


@app.command()
def main(
    prompt: str = typer.Argument(..., help="Instruction describing the calendar action to take."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show the request without sending it."),
    model: str = typer.Option(
        None,
        "--model",
        help="OpenAI model to use for translation.",
    ),
) -> None:
    """Convert `prompt` into an API call and execute it."""

    settings = get_settings()
    client = _load_openai_client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.responses.create(
        model=model_name,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    message = response.output_text
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as exc:  # pragma: no cover - depends on model behaviour
        raise RuntimeError(f"OpenAI response was not valid JSON: {message}") from exc

    endpoint = payload.get("endpoint")
    method = payload.get("method", "POST").upper()
    body: Dict[str, Any] = payload.get("payload", {})

    if not endpoint or not isinstance(endpoint, str):
        raise RuntimeError(f"OpenAI response missing endpoint: {message}")
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    request_description = json.dumps({"method": method, "url": endpoint, "payload": body}, indent=2)
    typer.echo(request_description)

    if dry_run:
        return

    headers = {"x-api-key": settings.api_key}
    if method == "POST":
        headers["Content-Type"] = "application/json"

    with httpx.Client(base_url=settings.api_base, timeout=30.0) as http:
        response = http.request(method, endpoint, json=body if method in {"POST", "PUT", "PATCH"} else None, headers=headers)
        response.raise_for_status()
        typer.echo(json.dumps(response.json(), indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
