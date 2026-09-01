"""Verify the release files and metadata produced by ``uv build``.

This intentionally uses only the Python standard library so it can run before
the freshly built package is installed.
"""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

DIST_NAME = "phamviet-google-tasks-mcp"
PACKAGE_NAME = "google_tasks_mcp"
REQUIRED_PACKAGE_FILES = (
    "__init__.py",
    "auth.py",
    "google.py",
    "server.py",
    "py.typed",
)


def metadata_from_bytes(contents: bytes) -> tuple[str, str]:
    message = BytesParser(policy=default).parsebytes(contents)
    name = message["Name"]
    version = message["Version"]
    if name is None or version is None:
        raise AssertionError("distribution metadata must contain Name and Version")
    return name, version


def assert_metadata(actual: tuple[str, str], version: str, artifact: Path) -> None:
    expected = (DIST_NAME, version)
    if actual != expected:
        raise AssertionError(f"{artifact}: expected metadata {expected!r}, got {actual!r}")


def verify_wheel(wheel: Path, version: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_paths = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_paths) != 1:
            raise AssertionError(f"{wheel}: expected one wheel METADATA file")
        assert_metadata(metadata_from_bytes(archive.read(metadata_paths[0])), version, wheel)
        required = {f"{PACKAGE_NAME}/{name}" for name in REQUIRED_PACKAGE_FILES}
        missing = sorted(required - names)
        if missing:
            raise AssertionError(f"{wheel}: missing required package files: {', '.join(missing)}")


def verify_sdist(sdist: Path, version: str) -> None:
    root = f"{DIST_NAME.replace('-', '_')}-{version}"
    with tarfile.open(sdist, "r:gz") as archive:
        members = {member.name for member in archive.getmembers() if member.isfile()}
        metadata_path = f"{root}/PKG-INFO"
        if metadata_path not in members:
            raise AssertionError(f"{sdist}: missing {metadata_path}")
        file_object = archive.extractfile(metadata_path)
        if file_object is None:
            raise AssertionError(f"{sdist}: unable to read {metadata_path}")
        assert_metadata(metadata_from_bytes(file_object.read()), version, sdist)
        required = {
            f"{root}/pyproject.toml",
            f"{root}/README.md",
            f"{root}/LICENSE",
            *{f"{root}/src/{PACKAGE_NAME}/{name}" for name in REQUIRED_PACKAGE_FILES},
        }
        missing = sorted(required - members)
        if missing:
            raise AssertionError(f"{sdist}: missing required release files: {', '.join(missing)}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Verify built wheel and sdist release contents.")
    result.add_argument("dist_dir", type=Path)
    result.add_argument("--version", default="0.3.1")
    return result


def main() -> None:
    args = parser().parse_args()
    wheel = args.dist_dir / f"{DIST_NAME.replace('-', '_')}-{args.version}-py3-none-any.whl"
    sdist = args.dist_dir / f"{DIST_NAME.replace('-', '_')}-{args.version}.tar.gz"
    missing = [path for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise SystemExit(f"missing expected release artifacts: {', '.join(map(str, missing))}")
    verify_wheel(wheel, args.version)
    verify_sdist(sdist, args.version)
    print(f"verified {wheel.name} and {sdist.name}")


if __name__ == "__main__":
    main()
