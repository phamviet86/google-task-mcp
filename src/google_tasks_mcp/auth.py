from __future__ import annotations

import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from . import __version__
from .google import TASKS_SCOPE, load_client_secrets, save_authorized_user_token


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="google-tasks-mcp-auth",
        description="Authorize Google Tasks with an OAuth Desktop client.",
    )
    result.add_argument(
        "--client-secret",
        required=True,
        type=Path,
        help="Protected Google OAuth Desktop client JSON",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return result


def main() -> None:
    args = parser().parse_args()
    client_secret = args.client_secret.expanduser().resolve()
    load_client_secrets(client_secret)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), [TASKS_SCOPE])
    credentials = flow.run_local_server(port=0)
    destination = save_authorized_user_token(credentials)
    print(f"Google Tasks authorization saved to {destination}")


if __name__ == "__main__":
    main()
