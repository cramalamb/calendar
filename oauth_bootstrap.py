"""Utility script to complete the OAuth desktop flow for Google Calendar."""

from __future__ import annotations

from pathlib import Path

from calendar_app.config import get_settings

CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")


def main() -> None:
    """Run the OAuth flow and persist the resulting token.json."""

    settings = get_settings()

    if not CREDENTIALS_PATH.exists():
        raise SystemExit(
            "credentials.json not found. Download it from Google Cloud Console "
            "(OAuth client type Desktop) and place it in this directory."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise SystemExit(
            "google-auth-oauthlib is not installed. Install requirements.txt first."
        ) from exc

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH), scopes=settings.google_scopes
    )
    creds = flow.run_local_server(port=0, prompt="consent")

    TOKEN_PATH.write_text(creds.to_json())
    print(f"Token written to {TOKEN_PATH.resolve()}")


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
