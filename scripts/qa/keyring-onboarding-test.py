#!/usr/bin/env python3
"""
KeyRing Full Onboarding Test — iOS
Navigates: Welcome → Onboarding screens → PIN Create → PIN Confirm →
           Agent Name → Terms → Home Screen
Uses Appium WebDriver protocol directly via requests.
Test data is mocked.

Prerequisites on Mac:
  - iPhone plugged in and unlocked (USB)
  - Tunnel running: sudo appium driver run xcuitest tunnel-creation
  - Appium running: appium --relaxed-security
  - KeyRing app installed: asml.bkc.harvard.wallet
"""
import requests
import time
import os
import json
import sys
import base64
import re
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────
APPIUM_URL = "http://localhost:4723"
SCREENSHOT_DIR = "/tmp/keyring-screenshots"
MOCK_PIN = "123456"
MOCK_AGENT_NAME = "TestAgent"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── testID mappings (from app/src/screens/ + bifold packages) ───────
# React Native testID props → accessibility identifiers with prefix:
#   com.ariesbifold:id/<testID>
# Strategy: try testID FIRST, fall back to xpath label matching

TEST_IDS = {
    # Buttons
    "Get Started":     "com.ariesbifold:id/GetStarted",
    "Continue":        "com.ariesbifold:id/Continue",
    "Create PIN":      "com.ariesbifold:id/CreatePIN",
    "Agree":           "com.ariesbifold:id/Agree",
    # Screens (root views)
    "WelcomeScreen":   "com.ariesbifold:id/WelcomeScreen",
    "PinIntroScreen":  "com.ariesbifold:id/PinIntroScreen",
    "PinEntryScreen":  "com.ariesbifold:id/PinEntryScreen",
    "BiometricScreen": "com.ariesbifold:id/BiometricScreen",
    "AgentSetupScreen":"com.ariesbifold:id/AgentSetupScreen",
    "RCardProfileScreen": "com.ariesbifold:id/RCardProfileScreen",
    # PIN fields
    "EnterPIN":        "com.ariesbifold:id/EnterPIN",
    "CreatePIN":       "com.ariesbifold:id/CreatePIN",
}

def find_by_testid(sid, key, timeout=5):
    """Find element by testID mapping key. Falls back to xpath label."""
    testid = TEST_IDS.get(key)
    if testid:
        el = find_element(sid, "accessibility id", testid, timeout=2)
        if el:
            return el
    # Fallback: xpath by label
    return find_element(sid, "xpath", f"//*[@label='{key}']", timeout=timeout)

CAPS = {
    "platformName": "iOS",
    "appium:automationName": "XCUITest",
    "appium:udid": "00008140-00064C4621B8801C",
    "appium:bundleId": "asml.bkc.harvard.wallet",
    "appium:updatedWDABundleId": "com.alberto.wda",
    "appium:noReset": True,
    "appium:useNewWDA": True,
    "appium:usePrebuiltWDA": False,
    "appium:wdaLaunchTimeout": 300000,
    "appium:wdaStartupRetries": 2,
    "appium:newCommandTimeout": 300,
    "appium:autoAcceptAlerts": True,
}

# ── WebDriver Protocol Helpers (using="strategy", value="selector") ──
# CRITICAL: Appium expects "using" not "strategy", "value" not "selector"

def _post(path, data=None, timeout=60):
    try:
        return requests.post(f"{APPIUM_URL}{path}", json=data, timeout=timeout)
    except Exception as e:
        print(f"  [!] POST {path}: {e}")
        return None

def _get(path, timeout=60):
    try:
        return requests.get(f"{APPIUM_URL}{path}", timeout=timeout)
    except Exception as e:
        print(f"  [!] GET {path}: {e}")
        return None

def _delete(path, timeout=10):
    try:
        return requests.delete(f"{APPIUM_URL}{path}", timeout=timeout)
    except:
        pass

# ── Session ──────────────────────────────────────────────────────────

def create_session():
    """Create Appium session. Returns session_id or None."""
    print("[1] Creating Appium session (3-5 min for first WDA build)...")
    t0 = time.time()
    r = _post("/session", {"capabilities": {"alwaysMatch": CAPS}}, timeout=300)

    if not r:
        print("  ❌ No response from Appium")
        return None
    if not r.ok:
        err = r.json().get("value", {}).get("message", r.text[:300])
        print(f"  ❌ Session failed [{r.status_code}]: {err}")
        return None

    val = r.json().get("value", {})
    sid = val.get("sessionId", "")
    if not sid:
        print(f"  ❌ No sessionId: {json.dumps(r.json(), indent=2)[:500]}")
        return None

    print(f"  ✅ Session: {sid} ({time.time()-t0:.1f}s)")
    return sid


def close_session(sid):
    if sid:
        _delete(f"/session/{sid}")


# ── Element Finding (fixed protocol: using + value) ──────────────────

def find_element(sid, using, value, timeout=10):
    """Find a single element. Returns element_id string or None."""
    data = {"using": using, "value": value}
    r = _post(f"/session/{sid}/element", data, timeout=timeout)
    if not r or not r.ok:
        return None
    elem = r.json().get("value", {})
    if isinstance(elem, dict):
        return elem.get("element-6066-11e4-a52e-4f735466cecf") or elem.get("ELEMENT")
    return elem


def find_elements(sid, using, value, timeout=10):
    """Find multiple elements. Returns list of element_ids."""
    data = {"using": using, "value": value}
    r = _post(f"/session/{sid}/elements", data, timeout=timeout)
    if not r or not r.ok:
        return []
    elems = r.json().get("value", [])
    result = []
    for e in elems:
        if isinstance(e, dict):
            eid = e.get("element-6066-11e4-a52e-4f735466cecf") or e.get("ELEMENT")
            if eid:
                result.append(eid)
        elif isinstance(e, str):
            result.append(e)
    return result


def click_element(sid, element_id):
    r = _post(f"/session/{sid}/element/{element_id}/click")
    return r and r.ok


def send_keys(sid, element_id, text):
    data = {"value": list(text), "text": text}
    r = _post(f"/session/{sid}/element/{element_id}/value", data)
    return r and r.ok


def clear_field(sid, element_id):
    r = _post(f"/session/{sid}/element/{element_id}/clear")
    return r and r.ok


def get_text(sid, element_id):
    r = _get(f"/session/{sid}/element/{element_id}/text")
    if r and r.ok:
        return r.json().get("value", "")
    return None


def get_page_source(sid):
    r = _get(f"/session/{sid}/source")
    if r and r.ok:
        return r.json().get("value", "")
    return None


def take_screenshot(sid, name):
    r = _get(f"/session/{sid}/screenshot")
    if not r or not r.ok:
        return None
    b64 = r.json().get("value", "")
    if not b64:
        return None
    ts = datetime.now().strftime("%H%M%S")
    fname = f"{ts}_{name}.png"
    fpath = os.path.join(SCREENSHOT_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(base64.b64decode(b64))
    print(f"  [📸] {fpath}")
    return fpath


# ── Smart Finders ────────────────────────────────────────────────────

def find_button_by_label(sid, label, timeout=5):
    """
    Find a button by its label text. Tries multiple strategies.
    React Native buttons expose testID as accessibility id.
    """
    strategies = [
        ("accessibility id", label),
        ("name", label),
        ("-ios predicate string", f"type == 'XCUIElementTypeButton' AND label == '{label}'"),
        ("xpath", f"//XCUIElementTypeButton[@label='{label}']"),
        ("xpath", f"//XCUIElementTypeButton[contains(@label, '{label}')]"),
    ]
    for using, value in strategies:
        el = find_element(sid, using, value, timeout=timeout)
        if el:
            return el
    return None


def find_text_field(sid, timeout=5):
    """Find first text or secure text field."""
    el = find_element(sid, "xpath", "//XCUIElementTypeSecureTextField", timeout=timeout)
    if el:
        return el
    el = find_element(sid, "xpath", "//XCUIElementTypeTextField", timeout=timeout)
    return el


def tap_button_by_label(sid, label, timeout=5):
    """Find and tap a button by label. Returns True/False."""
    el = find_button_by_label(sid, label, timeout=timeout)
    if el:
        ok = click_element(sid, el)
        print(f"  🔘 Tapped: '{label}' {'✅' if ok else '❌'}")
        return ok
    print(f"  [!] Button not found: '{label}'")
    return False


def tap_first_visible_button(sid, timeout=5):
    """Try to tap the most prominent action button."""
    priority = [
        "Get Started", "Get started", "Continue", "Next", "Agree", "Accept",
        "I Agree", "Confirm", "Done", "Start", "Begin", "OK", "Yes",
        "Create", "Initialize", "Setup", "Go", "Proceed", "Skip", "Later",
    ]
    for label in priority:
        if tap_button_by_label(sid, label, timeout=2):
            return True
    return False


def enter_pin(sid, pin):
    """
    Enter PIN. Handles two PIN screen variants:
    A) PIN intro: "Create a PIN that is:" + Continue (no text fields)
    B) PIN entry: "Enter a 6 digit PIN" + 2 fields + Create PIN button
    """
    # First, check if this is the PIN intro screen (no text fields)
    source = get_page_source(sid) or ""
    if "Enter a 6 digit PIN" in source or "Re-enter PIN" in source:
        # Screen B: Actual PIN entry with text fields
        print("  🔐 PIN entry screen — typing PIN...")
        # Find all text/secure fields
        fields = find_elements(sid, "xpath",
            "//XCUIElementTypeSecureTextField | //XCUIElementTypeTextField", timeout=3)

        if not fields:
            print("  [!] No text fields on PIN entry screen!")
            return False

        # Enter PIN in first field
        print(f"  ⌨️  First field: '{pin}'")
        if not send_keys(sid, fields[0], pin):
            print("  [!] Failed to type PIN")
            return False
        time.sleep(0.3)

        # Enter PIN in second field (confirm)
        if len(fields) > 1:
            print(f"  ⌨️  Confirm field: '{pin}'")
            if not send_keys(sid, fields[1], pin):
                print("  [!] Failed to type confirm PIN")
                return False
            time.sleep(0.3)

        # Tap "Create PIN" button
        print("  🔘 Tapping Create PIN...")
        btn = find_button_by_label(sid, "Create PIN", timeout=3)
        if not btn:
            btn = find_element(sid, "accessibility id", "Create PIN", timeout=2)
        if btn:
            time.sleep(0.5)  # Let the button enable
            return click_element(sid, btn)
        print("  [!] Create PIN button not found")
        return False

    elif "Create a PIN" in source or "pin" in source.lower():
        # Screen A: PIN intro — just tap Continue
        print("  📜 PIN intro screen — tapping Continue...")
        return tap_button_by_label(sid, "Continue")
    else:
        print("  [!] Not a PIN screen?")
        return False


def detect_screen_type(source_text):
    """Detect what screen we're on from page source text."""
    text = source_text.lower() if source_text else ""

    # Welcome/Start screen — has "Welcome" or "Get Started" button
    if "get started" in text and ("welcome" in text or "secure by design" in text or "take control" in text):
        return "welcome"

    # Home screen indicators — actual wallet functionality terms
    # Must NOT have welcome marketing copy
    home_kw = ["scan", "my wallet", "add credential", "credential offer",
               "receive", "activity", "notifications", "settings",
               "home", "connections", "credentials"]
    # Count home keywords
    home_count = sum(1 for kw in home_kw if kw in text)
    welcome_kw = ["welcome", "get started", "secure by design", "take control",
                  "both parties confirm", "no middleman", "under your control"]
    welcome_count = sum(1 for kw in welcome_kw if kw in text)

    if home_count >= 2 and welcome_count == 0:
        return "home"
    elif welcome_count >= 1:
        return "welcome"

    # Biometric — check BEFORE pin (text often mentions "PIN" in biometric prompts)
    if "face id" in text or "touch id" in text or "biometric" in text or "fingerprint" in text:
        return "biometric"

    # PIN entry or unlock
    if "pin" in text or "passcode" in text or "enter your" in text:
        if "unlock" in text or "enter your pin" in text:
            return "unlock"
        return "pin"

    # R-Card profile: has "Create Your Profile" or First/Last name fields
    if "create your profile" in text or ("first name" in text and "last name" in text):
        return "rcard_profile"

    # Terms
    if "terms" in text or "privacy policy" in text or "agree" in text:
        return "terms"

    # Loading — check before agent (text may contain "agent")
    if "loading" in text or "initializing" in text or "setting up" in text:
        return "loading"

    # Agent/Name setup
    if "name your" in text or "what should we call" in text or ("agent" in text and "initializ" not in text):
        return "agent_setup"

    # Biometric
    if "face id" in text or "touch id" in text or "biometric" in text:
        return "biometric"

    return "unknown"


def summarize_screen(source_text):
    """Print a summary of what's on screen."""
    if not source_text:
        print("  [!] No source")
        return

    # Extract button labels
    buttons = set(re.findall(r'label="([^"]*)"', source_text))
    # Extract type=Button elements specifically
    button_labels = set()
    for m in re.finditer(r'<XCUIElementTypeButton[^>]*label="([^"]*)"', source_text):
        button_labels.add(m.group(1))

    labels = set(re.findall(r'type="XCUIElementTypeStaticText"[^>]*name="([^"]*)"', source_text))
    if not labels:
        labels = set(re.findall(r'label="([^"]*)"', source_text))

    screen_type = detect_screen_type(source_text)

    print(f"  🖥️  Screen: {screen_type} | Source: {len(source_text):,} chars")
    if button_labels:
        print(f"  🔘 Buttons: {sorted(button_labels)[:10]}")
    if labels:
        label_list = sorted(labels)[:8]
        print(f"  📝 Labels: {label_list}")


# ── Main Flow ────────────────────────────────────────────────────────

def run_onboarding():
    print("=" * 60)
    print("  KeyRing Full Onboarding Test")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. Session
    sid = create_session()
    if not sid:
        return 1

    try:
        step_count = 0
        MAX_STEPS = 40

        for step in range(MAX_STEPS):
            step_count = step + 1
            print(f"\n--- Step {step_count}/{MAX_STEPS} ---")

            # Get page source
            source = get_page_source(sid)
            if not source:
                print("  [!] No page source — session may be dead")
                break

            if len(source) < 100:
                print(f"  [!] Source too small ({len(source)} chars) — app may not be visible")
                take_screenshot(sid, f"step{step_count:02d}_empty")
                break

            # Summarize
            summarize_screen(source)

            # Screenshot
            take_screenshot(sid, f"step{step_count:02d}")

            # Detect screen type
            screen_type = detect_screen_type(source)

            if screen_type == "home":
                print("\n" + "🎉" * 30)
                print("  HOME SCREEN REACHED!")
                print("🎉" * 30)
                take_screenshot(sid, "HOME_SCREEN_FINAL")
                break

            elif screen_type == "welcome":
                print("  👋 Welcome screen — tapping 'Get Started'...")
                if not tap_button_by_label(sid, "Get Started"):
                    tap_first_visible_button(sid)

            elif screen_type == "pin":
                print(f"  🔐 PIN screen — entering '{MOCK_PIN}'...")
                enter_pin(sid, MOCK_PIN)

            elif screen_type == "terms":
                print("  📜 Terms screen — trying to accept...")
                for label in ["Agree", "I Agree", "Accept", "Continue"]:
                    if tap_button_by_label(sid, label, timeout=2):
                        break
                else:
                    tap_first_visible_button(sid)

            elif screen_type == "agent_setup":
                print(f"  🤖 Agent setup — entering '{MOCK_AGENT_NAME}'...")
                # Find any text field and type
                el = find_text_field(sid, timeout=3)
                if el:
                    clear_field(sid, el)
                    send_keys(sid, el, MOCK_AGENT_NAME)
                    print(f"  ⌨️  Typed: '{MOCK_AGENT_NAME}'")
                    time.sleep(0.5)
                    # Dismiss keyboard by tapping "return" key
                    ret = find_button_by_label(sid, "return", timeout=2)
                    if ret:
                        click_element(sid, ret)
                        time.sleep(0.3)
                    else:
                        # Try finding return via xpath
                        ret2 = find_element(sid, "xpath", "//XCUIElementTypeButton[@label='return']", timeout=2)
                        if ret2:
                            click_element(sid, ret2)
                            time.sleep(0.3)
                # Now tap Continue (keyboard dismissed)
                time.sleep(0.5)
                cont = find_button_by_label(sid, "Continue", timeout=3)
                if cont:
                    click_element(sid, cont)
                else:
                    # Try by xpath
                    cont = find_element(sid, "xpath", "//XCUIElementTypeButton[@label='Continue']", timeout=2)
                    if cont:
                        click_element(sid, cont)

            elif screen_type == "rcard_profile":
                print("  🪪 R-Card profile — filling fields...")
                profile_fields = [
                    ("First name", "Alberto"),
                    ("Last name", "Leon"),
                    ("Email", "alberto@tessero.network"),
                    ("Organization", "Tessero"),
                ]
                for label, value in profile_fields:
                    el = find_element(sid, "accessibility id", label, timeout=3)
                    if not el:
                        el = find_element(sid, "-ios predicate string", f"label == '{label}'", timeout=2)
                    if el:
                        send_keys(sid, el, value)
                        time.sleep(0.2)
                        # Dismiss keyboard
                        ret = find_element(sid, "xpath", "//XCUIElementTypeButton[@label='return']", timeout=2)
                        if ret:
                            click_element(sid, ret)
                            time.sleep(0.2)
                    else:
                        print(f"  [!] Field '{label}' not found")
                # Tap Continue
                cont = find_button_by_label(sid, "Continue", timeout=3)
                if cont:
                    click_element(sid, cont)

            elif screen_type == "unlock":
                print(f"  🔓 Unlock screen — entering '{MOCK_PIN}'...")
                # Find a single PIN field and enter
                fields = find_elements(sid, "xpath",
                    "//XCUIElementTypeSecureTextField | //XCUIElementTypeTextField", timeout=3)
                if fields:
                    send_keys(sid, fields[0], MOCK_PIN)
                    print(f"  ⌨️  PIN entered — waiting for unlock...")
                    time.sleep(2)  # Wait for wallet to unlock
                else:
                    print("  [!] No PIN field on unlock screen")

            elif screen_type == "biometric":
                print("  👆 Biometric prompt — trying to skip...")
                for label in ["Skip", "Later", "Not Now", "Maybe Later"]:
                    if tap_button_by_label(sid, label, timeout=2):
                        break
                else:
                    tap_first_visible_button(sid)

            elif screen_type == "loading":
                print("  ⏳ Loading/initializing — waiting 5s...")
                time.sleep(5)

            else:
                print("  ❓ Unknown screen — trying first available button...")
                if not tap_first_visible_button(sid):
                    print("  [!] No tappable element found — may be stuck")
                    take_screenshot(sid, f"step{step_count:02d}_STUCK")
                    # Save source for debugging
                    with open(f"/tmp/keyring_source_step{step_count}.xml", "w") as f:
                        f.write(source[:50000])
                    print(f"  📄 Source saved to /tmp/keyring_source_step{step_count}.xml")
                    break

            # Wait for transition
            time.sleep(2)

        else:
            print(f"\n⚠️  Reached max steps ({MAX_STEPS}) without detecting home screen")
            take_screenshot(sid, "FINAL_STATE")

        # Final report
        print(f"\n[Summary] {step_count} steps, screenshots in {SCREENSHOT_DIR}/")
        source = get_page_source(sid)
        if source:
            screen_type = detect_screen_type(source)
            print(f"  Final screen: {screen_type}")
            if screen_type == "home":
                print("  ✅ SUCCESS: Home screen reached!")
                # Save final source
                with open("/tmp/keyring_final_source.xml", "w") as f:
                    f.write(source[:50000])
                return 0
            else:
                print(f"  ❌ Did not reach home screen (stuck on: {screen_type})")
                with open("/tmp/keyring_final_source.xml", "w") as f:
                    f.write(source[:50000])
                return 1

    except KeyboardInterrupt:
        print("\n  ⏹️  Interrupted")
        return 1
    except Exception as e:
        print(f"\n  💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        print("\n[Cleanup] Closing session...")
        close_session(sid)
        print("  Session closed.")

    return 1


if __name__ == "__main__":
    sys.exit(run_onboarding())
