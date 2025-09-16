# Local Calendar Service

A FastAPI microservice that lets you manage Google Calendar events from your local machine. The
service supports creating/updating/deleting events, adding Google Meet links, free/busy queries, and
applying simple day plan templates. Optional helpers include an OAuth bootstrap script and a natural
language CLI that converts requests into API calls via OpenAI.

## Features

- **FastAPI service** exposed at `http://127.0.0.1:8010` via Uvicorn.
- **Google Calendar CRUD** including optional Google Meet links.
- **Free/Busy** endpoint that proxies Google Calendar availability.
- **Day plans** to drop pre-defined or custom schedules on a date.
- **API key guard** using the `x-api-key` header.
- **OAuth bootstrap** script to create `token.json` using your `credentials.json`.
- **Optional AI CLI** to convert natural language into API calls.

## Quick start

1. Clone the repo and create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and edit values, especially `CAL_API_KEY`.

3. Enable the Google Calendar API in Google Cloud Console, download your Desktop OAuth credentials
   as `credentials.json`, then run the bootstrap script:
   ```bash
   python oauth_bootstrap.py
   ```
   Approve the browser prompt; this writes `token.json` next to the script.

4. Start the API:
   ```bash
   uvicorn calendar_service:app --reload --port 8010
   ```

5. Create an event:
   ```bash
   curl -X POST http://127.0.0.1:8010/events.create \
     -H 'Content-Type: application/json' \
     -H "x-api-key: $CAL_API_KEY" \
     -d '{
       "title": "Local Test",
       "start_iso": "2025-09-16T09:00:00-04:00",
       "duration_min": 30,
       "add_google_meet": true
     }'
   ```

## API Overview

All endpoints expect the header `x-api-key` matching `CAL_API_KEY` in your environment.

### `POST /events.create`
Create a new event. Supply `title`, `start_iso`, and either `end_iso` or `duration_min`. Optional
fields: `description`, `location`, `attendees`, `timezone`, `add_google_meet`.

### `POST /events.update`
Update an event by `event_id`. You can edit summary, description, location, attendees (use
`clear_attendees` to remove all), start/end/duration, and Meet settings.

### `POST /events.delete`
Delete an event by `event_id`.

### `POST /freebusy.query`
Proxy to Google Calendar free/busy. Provide `time_min_iso` and `time_max_iso`, plus optional
`calendars` and `timezone`.

### `POST /dayplan.apply`
Apply either a built-in template (see `/dayplan.templates`) or custom blocks to a date. Blocks
support `title`, `start_time` (`HH:MM`), `duration_min`, optional `description`, `attendees`,
`location`, and `add_google_meet`.

### `GET /dayplan.templates`
List the bundled day plan templates.

### `GET /health`
Simple status check.

## Natural language CLI (optional)

Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) in your environment, then run:
```bash
python ai_cli.py "Add Deep Work tomorrow 9-11am ET with a Meet link"
```
The CLI prints the JSON request it will send and the response. Use `--dry-run` to avoid sending the
request.

## OpenAPI schema

Use `openapi.yaml` when connecting a Custom GPT or other client. Update the `servers[0].url` entry
when you expose the service via a tunnel.

## Development notes

- Secrets (`.env`, `credentials.json`, `token.json`) are ignored by git.
- Run `uvicorn calendar_service:app --reload --port 8010` during development.
- The service relies on `token.json` generated via `oauth_bootstrap.py`.
- Tests are not included; use the curl examples above to verify functionality.
