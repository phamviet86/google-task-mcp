# Security Policy

## Supported versions

Only the latest published minor release line receives security fixes.

| Version | Supported |
| --- | --- |
| `0.2.x` (latest published minor) | Yes |
| Older minor releases | No |

Security fixes are developed on `main` before release, but the `main` branch is not itself a
supported release. Users should run the latest published release.

## Report a vulnerability privately

Use GitHub's **Report a vulnerability** flow to open a private report:

<https://github.com/phamviet86/google-task-mcp/security/advisories/new>

If private vulnerability reporting is not available, use a private contact method published on the
[repository owner's GitHub profile](https://github.com/phamviet86). Do not open a public issue with
vulnerability details.

Include only the minimum information needed to reproduce and assess the issue:

- the affected version or commit;
- the security impact and affected component;
- sanitized reproduction steps or a minimal proof of concept;
- any mitigations you have already identified.

Never send Google OAuth tokens, refresh tokens, client secrets, authorization codes, real task
contents, unredacted configuration files, or logs containing account data. Maintainers do not need
your credentials to investigate a report. Use synthetic data and redact local paths and identifiers.

Maintainers will review the report privately, coordinate a fix and disclosure when appropriate, and
credit reporters who want attribution. Please allow time for investigation before publishing
details.

For non-security bugs, use the repository's bug report template instead.
