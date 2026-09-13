"""Local, read-only onboarding checks that never inspect OAuth contents."""

from __future__ import annotations

import os
import stat
from typing import Any

from .google import token_path


def doctor() -> dict[str, Any]:
    configured = token_path().expanduser()
    path = configured.absolute()
    checks: dict[str, bool] = {
        "token_path_is_absolute": configured.is_absolute(),
        "token_parent_exists": False,
        "token_parent_is_directory": False,
        "token_parent_is_not_symlink": False,
        "token_parent_owner_only": False,
        "token_file_exists": False,
        "token_file_is_regular": False,
        "token_file_is_not_symlink": False,
        "token_file_owned_by_current_user": False,
        "token_file_owner_readable": False,
        "token_file_owner_only": False,
    }
    actions: list[str] = []
    try:
        parent_status = path.parent.lstat()
    except FileNotFoundError:
        actions.append("Run google-tasks-mcp-auth; it creates the protected token directory.")
    except OSError as error:
        actions.append(
            f"Inspect the local token directory ({type(error).__name__}); it was not read."
        )
    else:
        checks["token_parent_exists"] = True
        checks["token_parent_is_directory"] = stat.S_ISDIR(parent_status.st_mode)
        checks["token_parent_is_not_symlink"] = not stat.S_ISLNK(parent_status.st_mode)
        checks["token_parent_owner_only"] = (stat.S_IMODE(parent_status.st_mode) & 0o077) == 0
        if not checks["token_parent_is_not_symlink"]:
            actions.append("Replace the token-directory symlink with an owner-owned directory.")
        elif not checks["token_parent_is_directory"]:
            actions.append("Use a directory as the parent of GOOGLE_TOKEN_FILE.")
        elif not checks["token_parent_owner_only"]:
            actions.append("Restrict the token directory to owner-only permissions (0700).")
    if not checks["token_path_is_absolute"]:
        actions.append("Set GOOGLE_TOKEN_FILE to an absolute protected path.")
    try:
        status = path.lstat()
    except FileNotFoundError:
        actions.append("Run google-tasks-mcp-auth with a local OAuth Desktop client JSON path.")
    except OSError as error:
        actions.append(f"Inspect the local token path ({type(error).__name__}); it was not read.")
    else:
        checks["token_file_exists"] = True
        checks["token_file_is_not_symlink"] = not stat.S_ISLNK(status.st_mode)
        checks["token_file_is_regular"] = stat.S_ISREG(status.st_mode)
        if checks["token_file_is_regular"] and checks["token_file_is_not_symlink"]:
            checks["token_file_owned_by_current_user"] = status.st_uid == os.geteuid()
            checks["token_file_owner_readable"] = bool(stat.S_IMODE(status.st_mode) & stat.S_IRUSR)
            checks["token_file_owner_only"] = (stat.S_IMODE(status.st_mode) & 0o077) == 0
        if not checks["token_file_is_not_symlink"]:
            actions.append("Replace the token symlink with an owner-owned regular token file.")
        elif not checks["token_file_is_regular"]:
            actions.append("Use an owner-owned regular file for GOOGLE_TOKEN_FILE.")
        elif not checks["token_file_owned_by_current_user"]:
            actions.append("Use a token file owned by the current user.")
        elif not checks["token_file_owner_readable"]:
            actions.append("Make the token file readable by its owner.")
        elif not checks["token_file_owner_only"]:
            actions.append("Restrict the token file to owner-only permissions (0600).")

    local_ready = all(checks.values())
    return {
        "ok": local_ready,
        "checks": checks,
        "token_path": str(path),
        "authentication": "unverified",
        "mcp_discovery": "unverified",
        "note": (
            "This check only inspects token-path metadata. It does not read credentials, contact "
            "Google, or prove authentication or MCP tool discovery."
        ),
        "actions": actions,
    }
