# Security Policy

## Supported versions

Before the first published release, security fixes are developed on `main`; no released version is
currently supported because no Git tag or GitHub Release has been published. Once releases exist,
only the latest published minor release line will receive security fixes.

| Version | Supported |
| --- | --- |
| Unreleased `main` / `0.3.0` release candidate | Best-effort only; not a published supported release |
| Published releases | None at the time this policy was checked |
| Older published minor releases | No, unless explicitly stated here |

Security fixes are developed on `main` before release, but `main` is not a supported release. For
the release candidate, pin an audited commit and plan to update when a security release is published.

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
