# QA scripts

Scripts used by the QA pipeline (`.github/workflows/agent-pipeline.yml`)
running on the Mac self-hosted runner.

## `qa-session-test.py`

Appium-based E2E smoke test. Invoked from the workflow as:

```
python3 ~/.hermes/scripts/qa-session-test.py {ios|android} [--json]
```

The workflow copies this file from `scripts/qa/` into `~/.hermes/scripts/`
before each Appium run, so the script always matches the PR being tested.

### Contract

- Stdlib-only: the runner's `python3` is `/usr/bin/python3` (3.9) with no
  virtualenv, so we talk directly to Appium's W3C HTTP API and avoid the
  `Appium-Python-Client` dependency.
- Appium server is started by the workflow before this script runs
  (`appium --port 4723`).
- The wallet app is assumed already installed on the iPhone — we launch by
  `bundleId` (`asml.bkc.harvard.wallet`) so the test works on real devices
  without re-signing.
- iPhone UDID, iOS version, bundle id, and Android equivalents can be
  overridden via env vars (`IPHONE_UDID`, `IPHONE_PLATFORM_VERSION`,
  `IOS_BUNDLE_ID`, `ANDROID_UDID`, etc.) — see the constants at the top
  of the script.

### Exit codes

| Code | Meaning                                                     |
|------|-------------------------------------------------------------|
| `0`  | All smoke checks passed                                     |
| `1`  | A functional check failed (real regression)                 |
| `2`  | Infrastructure failure (Appium unreachable, device offline) |

The pipeline's PR-comment formatter distinguishes infra (`2`) from
regression (`1`) so device flakes don't blame innocent PRs.

### Checks

For each platform the script runs three checks against the launched session:

1. **App launched & rendered** — page source is non-empty.
2. **Keyring branding visible** — soft check, regex on page source.
3. **Interactive elements present** — at least N elements / TextViews found.

These mirror the legacy JS smoke runner (`~/.hermes/smoke-runner.js`) but
without the WebDriverIO dependency.
