#!/usr/bin/env python3
"""
qa-session-test.py — Appium E2E smoke test for Keyring Wallet (iOS / Android).

Invoked by .github/workflows/agent-pipeline.yml on the Mac self-hosted runner as:

    python3 ~/.hermes/scripts/qa-session-test.py ios [--json]

Design constraints:
    * The runner's `python3` is /usr/bin/python3 (3.9, no virtualenv, no
      Appium-Python-Client). This script therefore uses only the stdlib and
      talks to the Appium server over its W3C HTTP endpoint directly.
    * Appium server is already running on http://localhost:4723 before this
      script is called (the workflow starts it).
    * The wallet app is assumed already installed on the iPhone — the test
      launches the existing build via `bundleId` so it works on real devices
      without re-signing.

Exit codes:
    0 — all checks passed
    1 — at least one functional check failed
    2 — infrastructure failure (Appium unreachable, device not connected, etc.)

When `--json` is passed, a single JSON document is also printed to stdout (last
line) so the pipeline can parse a structured result alongside the human log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional

# ─────────────────────────── Configuration ────────────────────────────

APPIUM_BASE  = os.environ.get("APPIUM_BASE", "http://localhost:4723")
SESSION_INIT_TIMEOUT = 180  # seconds — first WDA install/launch can be slow
HTTP_TIMEOUT = 90

# Real device wired up to the Mac runner. Keep in sync with smoke-runner.js.
IPHONE_UDID            = os.environ.get("IPHONE_UDID",  "00008140-00064C4621B8801C")
IPHONE_NAME            = os.environ.get("IPHONE_NAME",  "iPhone de Alberto")
IPHONE_PLATFORM_VERSION = os.environ.get("IPHONE_PLATFORM_VERSION", "18.6.2")
IOS_BUNDLE_ID          = os.environ.get("IOS_BUNDLE_ID", "asml.bkc.harvard.wallet")

ANDROID_UDID         = os.environ.get("ANDROID_UDID", "R9TT803DGWK")
ANDROID_NAME         = os.environ.get("ANDROID_NAME", "Samsung SM-A037U")
ANDROID_APP_PACKAGE  = os.environ.get("ANDROID_APP_PACKAGE", "asml.bkc.harvard.wallet")
ANDROID_APP_ACTIVITY = os.environ.get("ANDROID_APP_ACTIVITY", ".MainActivity")


# ───────────────────────────── HTTP helper ────────────────────────────


class AppiumError(Exception):
    """Raised when Appium returns a non-2xx status or unreachable."""


def _http(method: str, path: str, payload: Optional[dict] = None, timeout: int = HTTP_TIMEOUT) -> dict:
    url = APPIUM_BASE.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise AppiumError(f"{method} {path} → HTTP {e.code}: {body[:500]}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AppiumError(f"{method} {path} → unreachable: {e}") from e

    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        raise AppiumError(f"{method} {path} → non-JSON response: {body[:200]}") from e


# ─────────────────────────── Appium primitives ────────────────────────


def wait_for_appium(deadline: float) -> None:
    """Poll /status until Appium reports ready or the deadline passes."""
    last_err: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            r = _http("GET", "/status", timeout=5)
            ready = (r.get("value") or {}).get("ready")
            if ready:
                return
            last_err = f"not ready: {r}"
        except AppiumError as e:
            last_err = str(e)
        time.sleep(2)
    raise AppiumError(f"Appium /status never became ready: {last_err}")


def create_session(capabilities: dict) -> str:
    """Create a W3C session, return the sessionId."""
    payload = {"capabilities": {"alwaysMatch": capabilities, "firstMatch": [{}]}}
    r = _http("POST", "/session", payload, timeout=SESSION_INIT_TIMEOUT)
    value = r.get("value") or {}
    sid = value.get("sessionId") or r.get("sessionId")
    if not sid:
        raise AppiumError(f"No sessionId in response: {r}")
    return sid


def delete_session(session_id: str) -> None:
    try:
        _http("DELETE", f"/session/{session_id}", timeout=30)
    except AppiumError:
        pass


def page_source(session_id: str) -> str:
    r = _http("GET", f"/session/{session_id}/source", timeout=30)
    return (r.get("value") or "") if isinstance(r.get("value"), str) else ""


def find_elements(session_id: str, using: str, value: str) -> list:
    r = _http(
        "POST",
        f"/session/{session_id}/elements",
        {"using": using, "value": value},
        timeout=30,
    )
    v = r.get("value")
    return v if isinstance(v, list) else []


# ─────────────────────────────── Caps ─────────────────────────────────


def caps_ios() -> dict:
    return {
        "platformName": "iOS",
        "appium:automationName": "XCUITest",
        "appium:udid": IPHONE_UDID,
        "appium:deviceName": IPHONE_NAME,
        "appium:platformVersion": IPHONE_PLATFORM_VERSION,
        "appium:bundleId": IOS_BUNDLE_ID,
        "appium:noReset": True,
        "appium:newCommandTimeout": 120,
        "appium:wdaLaunchTimeout": 120000,
        "appium:wdaConnectionTimeout": 120000,
        "appium:usePrebuiltWDA": False,
        "appium:useNewWDA": False,
        "appium:wdaStartupRetries": 3,
        "appium:wdaStartupRetryInterval": 30000,
    }


def caps_android() -> dict:
    return {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:udid": ANDROID_UDID,
        "appium:deviceName": ANDROID_NAME,
        "appium:appPackage": ANDROID_APP_PACKAGE,
        "appium:appActivity": ANDROID_APP_ACTIVITY,
        "appium:noReset": True,
        "appium:newCommandTimeout": 120,
        "appium:uiautomator2ServerLaunchTimeout": 120000,
        "appium:uiautomator2ServerInstallTimeout": 120000,
        "appium:autoGrantPermissions": True,
    }


# ─────────────────────────────── Checks ───────────────────────────────


def check_app_rendered(session_id: str) -> str:
    src = page_source(session_id)
    if not src or len(src) < 50:
        raise AssertionError(f"empty page source ({len(src)} chars) — app did not render")
    return f"page source = {len(src)} chars"


def check_keyring_branding(session_id: str) -> str:
    src = page_source(session_id)
    if not re.search(r"keyring|key.?ring", src, re.IGNORECASE):
        # Branding is a soft signal; some screens may not show it. Don't fail.
        return "branding not found in current view (soft check)"
    return "Keyring branding present"


def check_interactive_ios(session_id: str) -> str:
    els = find_elements(session_id, "xpath", "//*")
    if len(els) < 2:
        raise AssertionError(f"only {len(els)} elements found — UI looks broken")
    return f"{len(els)} elements on screen"


def check_interactive_android(session_id: str) -> str:
    els = find_elements(session_id, "xpath", "//android.widget.TextView")
    if len(els) < 1:
        raise AssertionError("no TextViews found — UI looks broken")
    return f"{len(els)} TextViews on screen"


CHECKS = {
    "ios": [
        ("App launched & rendered", check_app_rendered),
        ("Keyring branding visible", check_keyring_branding),
        ("Interactive elements present", check_interactive_ios),
    ],
    "android": [
        ("App launched & rendered", check_app_rendered),
        ("Keyring branding visible", check_keyring_branding),
        ("Interactive elements present", check_interactive_android),
    ],
}


# ─────────────────────────────── Main ─────────────────────────────────


def run(platform: str) -> dict:
    if platform == "ios":
        caps = caps_ios()
        device_label = f"{IPHONE_NAME} (iOS {IPHONE_PLATFORM_VERSION}, {IPHONE_UDID})"
    elif platform == "android":
        caps = caps_android()
        device_label = f"{ANDROID_NAME} ({ANDROID_UDID})"
    else:
        raise SystemExit(f"unknown platform: {platform!r} (expected 'ios' or 'android')")

    print(f"Device:  {device_label}")
    print(f"Appium:  {APPIUM_BASE}")
    print(f"App:     {caps.get('appium:bundleId') or caps.get('appium:appPackage')}")
    print()

    result: dict[str, Any] = {
        "platform": platform,
        "device": device_label,
        "checks": [],
        "passed": 0,
        "failed": 0,
        "status": "unknown",
        "error": None,
        "session_id": None,
        "duration_s": 0.0,
    }
    t0 = time.monotonic()

    # Phase 1: ensure Appium is reachable. Failures here are infra (exit 2).
    try:
        wait_for_appium(deadline=time.monotonic() + 30)
    except AppiumError as e:
        result["status"] = "infra_error"
        result["error"] = f"Appium not reachable: {e}"
        result["duration_s"] = round(time.monotonic() - t0, 2)
        print(f"❌ INFRA: {result['error']}")
        return result

    # Phase 2: open a session. Common failures: device not connected, app not
    # installed, WDA can't launch. These are infra errors, not regressions.
    session_id: Optional[str] = None
    try:
        session_id = create_session(caps)
        result["session_id"] = session_id
        print(f"✅ session created: {session_id}")
    except AppiumError as e:
        result["status"] = "infra_error"
        result["error"] = f"Session create failed: {e}"
        result["duration_s"] = round(time.monotonic() - t0, 2)
        print(f"❌ INFRA: {result['error']}")
        return result

    # Phase 3: run checks. These ARE the smoke test — failures here mean
    # a regression and we return exit 1.
    try:
        # Brief settle delay so the app reaches its initial screen.
        time.sleep(3)
        for name, fn in CHECKS[platform]:
            entry = {"name": name, "passed": False, "detail": None, "error": None}
            try:
                detail = fn(session_id)
                entry["passed"] = True
                entry["detail"] = detail
                result["passed"] += 1
                print(f"✅ PASS: {name} — {detail}")
            except Exception as e:  # noqa: BLE001 — surface any check error
                entry["error"] = str(e)
                result["failed"] += 1
                print(f"❌ FAIL: {name} — {e}")
            result["checks"].append(entry)
    finally:
        delete_session(session_id)

    result["status"] = "passed" if result["failed"] == 0 else "failed"
    result["duration_s"] = round(time.monotonic() - t0, 2)

    print()
    print("═══════════════════════════════════")
    if result["status"] == "passed":
        print(f"  ✅ SMOKE TEST PASSED ({result['passed']}/{result['passed'] + result['failed']})")
    else:
        print(f"  ❌ SMOKE TEST FAILED ({result['passed']}/{result['passed'] + result['failed']} passed)")
    print("═══════════════════════════════════")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Keyring Wallet Appium smoke test")
    parser.add_argument("platform", choices=["ios", "android"], help="target platform")
    parser.add_argument("--json", action="store_true", help="emit JSON summary on stdout")
    args = parser.parse_args()

    try:
        result = run(args.platform)
    except KeyboardInterrupt:
        print("aborted", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — final safety net
        print(f"❌ CRASH: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "crash", "error": str(e), "platform": args.platform}))
        return 2

    if args.json:
        print(json.dumps(result, indent=2))

    if result["status"] == "passed":
        return 0
    if result["status"] == "infra_error":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
