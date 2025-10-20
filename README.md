# Custom Calendar Assistant Notes

## Minimum Event Requirements
- **Title:** Every event must specify a concise summary that will become the `SUMMARY` field in the ICS output.
- **Start Time:** Capture an exact start date and time, including an explicit or inferred time zone.
- **Duration:** Use the supplied duration to compute the event end time. If a user omits duration, prompt for it because it is mandatory in this workflow.
- **Optional Extras:** Any additional details (location, attendees, reminders, conferencing links, etc.) are appended when provided but are not required to create the event.

## ICS File Expectations
- **Template Compatibility:** Generate files that comply with the iCalendar RFC so they import cleanly into macOS Calendar, Microsoft Outlook, and Google Calendar.
- **UID (Unique Identifier):** Each event needs a globally unique ID inside the `UID` property (for example, a UUID combined with a domain such as `1234@example.com`). This identifier lets calendar applications recognize updates to the same event.
- **Calendar Association:** The `PRODID` and `UID` can reference the primary calendar since that is the intended destination.

## Google Calendar Integration
- **API Endpoint:** Plan for a backend (e.g., FastAPI) that receives the structured event payload and calls the Google Calendar API to create the event.
- **Short-Lived Tokens vs. Stored Credentials:**
  - *Short-Lived Tokens* (OAuth access tokens) typically expire within an hour and are obtained via an authorization flow using refresh tokens or service accounts. They reduce risk because compromised tokens quickly become invalid but require automatic refresh logic.
  - *Stored Credentials* (refresh tokens or service account keys) persist on disk or in a secret manager so the backend can request new short-lived tokens without re-prompting the user. They demand stricter security controls because they remain valid until revoked.
- **Authentication Choice:** Decide whether the assistant requests tokens from the user each session or whether the backend stores the credentials securely (e.g., in Google Secret Manager) and handles token refresh transparently.

## Hosting and Deployment
- **Environment Options:** Google Cloud is a straightforward choice (Cloud Run, Cloud Functions, or a Compute Engine VM) because it integrates easily with Google APIs. Google Drive alone is not a compute platform, but you can store generated ICS files there if needed.
- **Quotas:** No specific custom quotas were identified, but remember the default Google Calendar API quota (e.g., 1,000,000 queries per day). Monitor usage and request increases if necessary.

## Time Zone Handling
- If the user supplies a time zone, apply it to the event's `DTSTART`/`DTEND` fields and include the matching `VTIMEZONE` definition when exporting ICS files. If the user does not provide one, apply the agreed default time zone before generating the event.
