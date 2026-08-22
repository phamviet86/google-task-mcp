## Summary

Describe the problem and the approach taken.

## Verification

List the commands or manual MCP checks you ran. Use fake clients and sanitized data; never attach
OAuth tokens, client secrets, authorization codes, or real task contents.

## Checklist

- [ ] The change is focused and preserves unrelated behavior.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy` passes.
- [ ] `uv run pytest` passes.
- [ ] Tests cover new behavior or the reason they are unnecessary is explained.
- [ ] README and community documentation are updated when contracts or setup change.
- [ ] No credentials, generated tokens, personal task data, or sensitive logs are included.
- [ ] Security-sensitive findings were reported privately according to `SECURITY.md`.
