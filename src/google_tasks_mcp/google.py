from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"
DEFAULT_API_NUM_RETRIES = 3
MAX_API_NUM_RETRIES = 10
_CREDENTIALS_LOCK = threading.Lock()


def token_path() -> Path:
    configured = os.environ.get("GOOGLE_TOKEN_FILE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "google-tasks-mcp" / "token.json"


def api_num_retries() -> int:
    configured = os.environ.get("GOOGLE_API_NUM_RETRIES")
    if configured is None:
        return DEFAULT_API_NUM_RETRIES
    try:
        retries = int(configured)
    except ValueError as error:
        raise RuntimeError("GOOGLE_API_NUM_RETRIES must be an integer from 0 to 10") from error
    if not 0 <= retries <= MAX_API_NUM_RETRIES:
        raise RuntimeError("GOOGLE_API_NUM_RETRIES must be an integer from 0 to 10")
    return retries


def load_client_secrets(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    installed = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(installed, dict):
        raise ValueError(
            "--client-secret must point to a Google OAuth Desktop client JSON "
            "containing 'installed'."
        )
    client_id = installed.get("client_id")
    client_secret = installed.get("client_secret")
    if not isinstance(client_id, str) or not client_id:
        raise ValueError("OAuth Desktop client JSON is missing installed.client_id")
    if not isinstance(client_secret, str) or not client_secret:
        raise ValueError("OAuth Desktop client JSON is missing installed.client_secret")
    return {"client_id": client_id, "client_secret": client_secret}


def save_authorized_user_token(credentials: Credentials, path: Path | None = None) -> Path:
    if not credentials.refresh_token:
        raise ValueError(
            "Google did not return a refresh token. Revoke the app grant and run auth again."
        )
    destination = path or token_path()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.parent.chmod(0o700)
    payload = credentials.to_json()  # type: ignore[no-untyped-call]
    descriptor, temporary_name = tempfile.mkstemp(prefix=".token-", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
        destination.chmod(0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def load_tasks_credentials(path: Path) -> Credentials:
    try:
        return Credentials.from_authorized_user_file(  # type: ignore[no-any-return,no-untyped-call]
            str(path), [TASKS_SCOPE]
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "Google Tasks is not authenticated. Run 'google-tasks-mcp-auth' first. "
            f"Token path: {path}. {error}"
        ) from error


def get_tasks_client() -> Resource:
    path = token_path()
    with _CREDENTIALS_LOCK:
        credentials = load_tasks_credentials(path)
        if credentials.expired:
            if not credentials.refresh_token:
                raise RuntimeError(
                    "Google Tasks credentials are expired and have no refresh token. "
                    "Run 'google-tasks-mcp-auth' again."
                )
            refresh_request = GoogleAuthRequest()
            try:
                credentials.refresh(refresh_request)  # type: ignore[no-untyped-call]
                save_authorized_user_token(credentials, path)
            except Exception as error:
                raise RuntimeError(
                    f"Failed to refresh and persist Google Tasks credentials: {error}"
                ) from error
            finally:
                refresh_request.session.close()
    return build("tasks", "v1", credentials=credentials, cache_discovery=False)


def google_error(error: BaseException) -> str:
    if isinstance(error, HttpError):
        status = error.status_code
        reason = error.reason
        message = "Google Tasks API error"
        if status:
            message += f" ({status})"
        if reason:
            message += f": {reason}"
        details = error.error_details
        if details and details != reason:
            formatted = (
                details
                if isinstance(details, str)
                else json.dumps(details, ensure_ascii=False, sort_keys=True, default=str)
            )
            message += f"; details: {formatted}"
        return message
    return str(error) or error.__class__.__name__


def json_result(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)
