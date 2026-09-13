from __future__ import annotations

import json
from pathlib import Path

import pytest

from google_tasks_mcp import skill_install


@pytest.fixture
def installed_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime with spaces" / "bin"
    runtime.mkdir(parents=True)
    for name in ("python", "google-tasks-mcp", "google-tasks-mcp-auth"):
        (runtime / name).write_text("fixture")
    monkeypatch.setattr(skill_install.sys, "executable", str(runtime / "python"))
    return runtime


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_default_destination(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert skill_install.default_skill_root() == tmp_path / ".agents" / "skills"
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "custom codex"))
    assert skill_install.default_skill_root() == tmp_path / "custom codex" / "skills"


@pytest.mark.parametrize("flags", [{"check": True}, {"dry_run": True}])
def test_inspection_does_not_create_destination(
    installed_runtime: Path, tmp_path: Path, flags: dict[str, bool]
) -> None:
    root = tmp_path / "absent" / "skills"
    report, code = skill_install.install_skills(root, **flags)
    assert code == (2 if flags.get("check") else 0)
    assert all(item["state"] == "missing" for item in report["skills"])
    assert not root.parent.exists()


def test_installs_idempotently_and_preserves_unrelated_files(
    installed_runtime: Path, tmp_path: Path
) -> None:
    root = tmp_path / "skills with spaces"
    report, code = skill_install.install_skills(root)
    assert code == 0 and report["ok"]
    notes = root / skill_install.SKILLS[0] / "personal-notes.txt"
    notes.write_text("keep")
    before = snapshot(root)
    assert skill_install.install_skills(root)[1] == 0
    assert skill_install.install_skills(root, check=True)[1] == 0
    assert snapshot(root) == before
    runtime = json.loads((root / skill_install.SKILLS[0] / "references/runtime.json").read_text())
    assert runtime == {
        "distribution": skill_install.DISTRIBUTION,
        "version": "0.4.0",
        "python": str(installed_runtime / "python"),
        "server": str(installed_runtime / "google-tasks-mcp"),
        "auth": str(installed_runtime / "google-tasks-mcp-auth"),
    }


def test_managed_replacement_requires_flag_and_preserves_unrelated_files(
    installed_runtime: Path, tmp_path: Path
) -> None:
    root = tmp_path / "skills"
    assert skill_install.install_skills(root)[1] == 0
    target = root / skill_install.SKILLS[1]
    (target / "SKILL.md").write_text("personal revision")
    (target / "notes.txt").write_text("keep")
    before = snapshot(root)
    assert skill_install.install_skills(root)[1] == 2
    assert skill_install.install_skills(root, check=True)[1] == 2
    assert skill_install.install_skills(root, dry_run=True, replace=True)[1] == 0
    assert snapshot(root) == before
    assert skill_install.install_skills(root, replace=True)[1] == 0
    assert (target / "SKILL.md").read_text().startswith("---")
    assert (target / "notes.txt").read_text() == "keep"
    assert skill_install.install_skills(root, check=True)[1] == 0


def test_unmanaged_or_symlinked_destinations_block_all_writes(
    installed_runtime: Path, tmp_path: Path
) -> None:
    root = tmp_path / "skills"
    target = root / skill_install.SKILLS[1]
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("not ours")
    before = snapshot(root)
    assert skill_install.install_skills(root, replace=True)[1] == 2
    assert snapshot(root) == before
    assert not (root / skill_install.SKILLS[0]).exists()

    safe = tmp_path / "safe"
    safe.mkdir()
    linked = tmp_path / "linked-skills"
    linked.symlink_to(safe, target_is_directory=True)
    assert skill_install.install_skills(linked, replace=True)[1] == 2
    assert list(safe.iterdir()) == []


def test_future_packaged_path_cannot_overwrite_an_unmanaged_file(
    installed_runtime: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "skills"
    assert skill_install.install_skills(root)[1] == 0
    target = root / skill_install.SKILLS[0]
    (target / "future.md").write_text("personal")
    original = skill_install._files

    def future(skill: str) -> dict[str, bytes]:
        files = original(skill)
        if skill == skill_install.SKILLS[0]:
            files["future.md"] = b"packaged"
        return files

    monkeypatch.setattr(skill_install, "_files", future)
    before = snapshot(root)
    report, code = skill_install.install_skills(root, replace=True)
    assert code == 2
    assert report["skills"][0]["state"] == "conflict"
    assert snapshot(root) == before


def test_unmanaged_file_cannot_occupy_a_future_packaged_path_parent(
    installed_runtime: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "skills"
    assert skill_install.install_skills(root)[1] == 0
    target = root / skill_install.SKILLS[0]
    (target / "future").write_text("personal")
    original = skill_install._files

    def future(skill: str) -> dict[str, bytes]:
        files = original(skill)
        if skill == skill_install.SKILLS[0]:
            files["future/asset.md"] = b"packaged"
        return files

    monkeypatch.setattr(skill_install, "_files", future)
    before = snapshot(root)
    assert skill_install.install_skills(root, dry_run=True, replace=True)[1] == 2
    assert snapshot(root) == before


def test_apply_failure_rolls_back_every_skill(
    installed_runtime: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "skills"
    assert skill_install.install_skills(root)[1] == 0
    for skill in skill_install.SKILLS:
        (root / skill / "SKILL.md").write_text("changed")
    before = snapshot(root)
    original_rename = Path.rename

    def fail_second_stage(self: Path, destination: Path) -> Path:
        if (
            self.name == skill_install.SKILLS[1]
            and destination == root / skill_install.SKILLS[1]
            and self.parent.parent == root
        ):
            raise OSError("fixture stage failure")
        return original_rename(self, destination)

    monkeypatch.setattr(Path, "rename", fail_second_stage)
    with pytest.raises(OSError, match="fixture stage failure"):
        skill_install.install_skills(root, replace=True)
    assert snapshot(root) == before
