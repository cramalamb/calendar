# Custom Calendar Assistant Reference

This repository captures the working notes for a Custom GPT that turns natural-language event descriptions into valid iCalendar (`.ics`) files and can hand the structured payload to a Google Calendar backend.

---

## 1. Event Data Requirements
- **Mandatory fields**
  - `SUMMARY` (title): a concise description of the meeting or event.
  - `DTSTART` (start): exact start date and time with an explicit or inferred time zone.
  - `DURATION`: primary way to derive the end time. If absent, the assistant must prompt because it is required for this workflow.
- **Optional enrichments**
  - Location, conferencing links, attendees, reminders, agenda text, etc. Include any optional data the user supplies, but do not block event creation when it is missing.
- **Default behaviors**
  - Use the agreed default time zone when the user does not specify one.
  - Apply a default reminder strategy only if the user requests it in the prompt.

---

## 2. ICS Generation Guidelines
- **RFC compliance**: Output must remain compatible with macOS Calendar, Microsoft Outlook, Google Calendar, and other iCalendar consumers.
- **UID (unique identifier)**
  - Generate a UUID v4 (or similar globally unique value) and append the primary-calendar domain, e.g., `f81d4fae-7dec-11d0-a765-00a0c91e6bf6@jakekramb.com`.
  - Persist the UID for the life of the event so updates map correctly across calendars.
- **Calendar metadata**
  - `PRODID` can reference this assistant (e.g., `-//Custom GPT Calendar Assistant//EN`).
  - When the user downloads an ICS file, include any optional fields (location, attendees, etc.) that were provided.
- **Time zones**
  - Apply the supplied time zone directly to `DTSTART` and `DTEND` (derived from start + duration).
  - When exporting to ICS, embed a matching `VTIMEZONE` block for non-UTC zones to ensure consistent rendering across clients.

---

## 3. Google Calendar Integration Notes
The assistant sends structured event data to a backend you host; that service then calls the Google Calendar API using stored credentials.

- **Service account**
  - ID: `105305876213370800450` (project `calendar-470802`). Manage its key material in Google Secret Manager and grant it the `https://www.googleapis.com/auth/calendar` scope.
  - Share the `jakekramb@gmail.com` calendar with this service account so it can create events. Using the literal calendar ID `jakekramb@gmail.com` (or the alias `primary`) is acceptable.
- **Stored credentials**
  - Keep the JSON key in Secret Manager or an equivalent vault.
  - The backend should exchange the service-account key for short-lived OAuth access tokens automatically; the GPT never handles raw credentials.
- **Backend responsibilities**
  - Validate incoming requests from the assistant (API key or bearer token as appropriate).
  - Translate the assistant payload into Google Calendar API calls (`events.insert`).
  - Return a structured response (success + event ID, or descriptive error) so the assistant can confirm creation or surface issues.
- **Endpoint contract (to supply)**
  - `BASE_URL`: _TBD_
  - `POST /<path>`: _TBD_
  - JSON schema: _TBD_ (document field names, expected ISO timestamps, optional properties, etc.).
  - Authentication header(s): _TBD_
- **Why stored credentials?**
  - Short-lived access tokens (≈1 hour lifetime) are safer to send over the wire; the backend mints them as needed using the stored service-account key. This keeps the GPT’s requests simple (no OAuth flow in the conversation) while maintaining security hygiene.

---

## 4. Hosting & Deployment Options
- **Google Cloud (recommended)**
  - Cloud Run or Cloud Functions offer always-free quotas suitable for a light personal workload and integrate directly with Secret Manager.
  - Store the service-account key as a secret and mount it at runtime to fetch Google access tokens.
- **Alternative free tiers**
  - Azure Functions consumption plan provides a comparable free grant. Ensure outbound access to `www.googleapis.com` and a secure secret store (Azure Key Vault) for the service-account key.
  - Other options (Render free tier, Fly.io, etc.) are viable if they can keep credentials secure and respect Google API egress requirements.
- **Non-compute storage**
  - Google Drive is not a hosting environment but can store generated ICS files for manual download if desired.

---

## 5. Privacy & Data Handling
- Personal-use context reduces regulatory overhead, yet still:
  - Avoid logging sensitive attendee details unnecessarily.
  - Prefer ephemeral storage for ICS artifacts unless the user explicitly wants them archived.

---

## 6. Next Steps Checklist
1. Define and document the FastAPI (or equivalent) endpoint path, JSON schema, and authentication headers (**open item**).
2. Provision the service-account key in Secret Manager and confirm calendar sharing permissions.
3. Implement backend logic to exchange the stored credential for short-lived tokens and call `events.insert` on the `jakekramb@gmail.com` calendar.
4. Update this README with the finalized endpoint contract so the Custom GPT can invoke it.
5. Add usage examples or prompt templates once the API contract is finalized.
