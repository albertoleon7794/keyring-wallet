# Keyring Wallet — QA & CI Pipeline Onboarding

## Architecture

```
┌─ EC2 (AWS t3.medium, Ubuntu) ───────────────────────────────┐
│                                                               │
│  • QA Agent (Hermes profile: qa)                              │
│  • Repo: ~/keyring-wallet/ + ~/keyring-bifold/ (submodule)   │
│  • Can run: yarn test, typecheck, lint, git, gh CLI           │
│  • CANNOT: native iOS/Android builds (no Xcode, no SDK)      │
│  • Node 20.19.2 via nvm, Yarn 4.9.2                          │
│                                                               │
│  ── SSH (Tailscale, keyring-mac) ────────────────────┐       │
└───────────────────────────────────────────────────────┼───────┘
                                                        │
┌─ Mac (Alberto's, Apple Silicon) ──────────────────────┼───────┐
│                                                        ▼       │
│  • Repo: ~/keyring-wallet/ (SEPARATE clone)                    │
│  • Has Xcode, Android SDK, real devices                        │
│  • iPhone de Alberto: wireless, UDID 00008140-...              │
│  • Samsung SM-A037U: USB, UDID R9TT803DGWK                     │
│  • Appium server runs here (port 4723)                         │
│  • ~/.hermes/smoke-test.sh — orchestrates build+test           │
│  • ~/.hermes/smoke-runner.js — WebDriverIO + Appium            │
│  • Brew tools at /opt/homebrew/bin (not on SSH PATH by default) │
└────────────────────────────────────────────────────────────────┘
```

## Roles

| Role | System | What it does |
|------|--------|--------------|
| **Engineer** | Mac/EC2 | Writes code, creates PRs, runs Cmd+B in Xcode |
| **QA Agent** | EC2 + Mac (SSH) | Checks out PRs, runs unit tests, builds on Mac, runs Appium E2E, posts reviews |
| **Alberto** | Mac | Final review, merge, manual device testing |

## Prerequisites

### On the Mac
```bash
# Tools needed (all installed):
brew install libimobiledevice    # idevice_id, ideviceinfo
npm install -g webdriverio       # Appium client
npm install -g appium            # Appium server
appium driver install xcuitest   # iOS driver
appium driver install uiautomator2  # Android driver
```

### RemoteXPC tunnel (needed for wireless iPhone)
```bash
# Run once per login session:
cd ~/keyring-wallet/app/node_modules/appium-xcuitest-driver
sudo node scripts/tunnel-creation.mjs
# Must be running before any Appium session
```

### Keychain (for code signing)
```bash
# SSH sessions can't unlock keychain — build in Xcode GUI instead
# Or run before SSH build:
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

## Full QA Workflow (per PR)

### 1. Checkout & JS tests (on EC2)
```bash
cd ~/keyring-wallet
git fetch origin pull/<NUMBER>/head:pr-<NUMBER>
git checkout pr-<NUMBER>
yarn install

# Run tests at both levels
yarn test --verbose          # wallet level
cd keyring-bifold && yarn test --verbose  # bifold level

# Types + lint
yarn typecheck
yarn lint
```

### 2. Sync to Mac
```bash
# EC2 commits must be pushed and pulled on Mac
git push origin <branch>
ssh keyring-mac 'cd ~/keyring-wallet && git fetch && git checkout <branch> && git pull'
```

### 3. Build for device (on Mac)
```bash
# Option A: Build via SSH (requires unlocked keychain)
ssh keyring-mac 'bash -s' < ~/.hermes/keys/smoke-test.sh ios

# Option B: Build in Xcode GUI (Cmd+B) — recommended
# Open ~/keyring-wallet/app/ios/AriesBifold.xcworkspace
# Select scheme AriesBifold, destination iPhone de Alberto
# Cmd+B — this handles signing automatically
```

### 4. Run Appium smoke test (after Cmd+B)
```bash
ssh keyring-mac 'bash -s' << 'EOF'
set -eo pipefail
source ~/.nvm/nvm.sh
export PATH="$HOME/.nvm/versions/node/v20.19.2/bin:/opt/homebrew/bin:$PATH"
export NODE_PATH="$HOME/.nvm/versions/node/v20.19.2/lib/node_modules"

pkill -f "appium.*4723" 2>/dev/null || true
sleep 1

appium --port 4723 --log-level error &
APPIUM_PID=$!
sleep 3
curl -s "http://localhost:4723/status" | grep -q "ready" || { echo "Appium failed"; exit 1; }

export SMOKE_DEVICE="ios"
node "$HOME/.hermes/smoke-runner.js"
EXIT=$?

kill $APPIUM_PID 2>/dev/null || true
wait $APPIUM_PID 2>/dev/null || true
exit $EXIT
EOF
```

### 5. Post review on PR
```bash
# QA review format (post as PR comment)
HOME=/home/ubuntu gh pr comment <NUMBER> \
  --repo albertoleon7794/keyring-wallet \
  --body '## QA Review...
  ...
  **Verdict:** ✅ / ⚠️ / ❌'
```

## Common Issues & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Unknown device or simulator UDID` | iPhone not reachable | Reconnect phone, restart tunnel |
| `errSecInternalComponent` (codesign) | Keychain locked in SSH | Build in Xcode GUI (Cmd+B) instead |
| Build hangs at codegen | `Record<>` type in NativeModule spec | Change to `{[key: string]: unknown}` |
| `idevice_id: command not found` | Brew not on SSH PATH | Add `/opt/homebrew/bin` to PATH |
| Mac on wrong branch | Separate clones, not synced | Push from EC2, pull on Mac |
| `webdriverio` module not found | Not installed or NODE_PATH not set | `npm install -g webdriverio`, set NODE_PATH |
| Tests timeout on push | Pre-push hook runs test suite | Use `git push --no-verify` |
| gh CLI not authed | QA profile has isolated HOME | Use `HOME=/home/ubuntu gh ...` |

## Smoke Test Expected Output

```
📱 Auto-detected: iPhone de Alberto (iOS 18.6.2) — 00008140-...
📦 Auto-detected app: .../KeyRing.app
✅ PASS: App launched & rendered
✅ PASS: Keyring branding visible
✅ PASS: Interactive elements present

═══════════════════════════════════
  ✅ SMOKE TEST PASSED
═══════════════════════════════════
```

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| `smoke-test.sh` | EC2: `~/.hermes/keys/`, Mac: `~/.hermes/` | Orchestrates build + Appium |
| `smoke-runner.js` | Mac: `~/.hermes/smoke-runner.js` | WebDriverIO + Appium test |
| `smoke-runner-v2.js` | EC2: `/tmp/smoke-runner-v2.js` | Source copy of runner |
| QA profile config | `~/.hermes/profiles/qa/` | QA agent settings |
| `keyring-preflight-checklist.md` | `~/.hermes/` | Daily pre-flight checks |
| `react-native-testid-pattern.md` | `~/.hermes/skills/.../appium-real-device-testing/references/` | How to add testIDs |

## Pre-Flight Checklist (Daily)

Before running any tests:

1. **Plug in iPhone** via USB (or ensure wireless tunnel is up)
2. **Unlock iPhone** — home screen visible (WDA can't tap passcode)
3. **Start tunnel** (in Mac GUI Terminal, NOT SSH):
   ```
   sudo appium driver run xcuitest tunnel-creation
   ```
4. **Verify Appium**: `curl http://localhost:4723/status`
5. **Build** (if code changed): Cmd+B in Xcode

## Port Map

| Port | Service | Context |
|------|---------|---------|
| 4723 | Appium HTTP server | User LaunchAgent |
| 42314 | Tunnel registry | Root, manual start |
| 50000 | Packet stream | Root, manual start |

## Pipeline Automation (Kanban Labels)

| Label | Who sets | Meaning |
|-------|----------|---------|
| `speced` | Alberto | PM approved, ready for engineer |
| `in-progress` | Engineer (auto) | Working on it |
| `in-review` | Engineer (auto) | PR open, ready for QA |
| `done` | QA (auto) | QA passed |
| `needs-work` | QA (auto) | QA failed, needs fixes |

## TestID Pattern (for Appium accessibility)

When adding testIDs for Appium automation, use the **zero-size sibling View alias** pattern:

```tsx
{/* Accessibility alias for QA automation */}
<View
  testID={testIdWithKey('PinField1')}
  accessible={true}
  accessibilityLabel={t('PINCreate.EnterPIN')}
  style={{ width: 0, height: 0 }}
/>
<PINInput
  testID={testIdWithKey('EnterPIN')}   // unchanged — Jest tests still pass
  ...
/>
```

**Rules:**
- If element has **no testID**: add directly
- If element **already has matching testID**: leave alone
- If element has testID that **disagrees with spec** AND tests reference it: add sibling View alias
- If component returns fragment `<>...</>`: wrap in `<View style={{flex:1}} testID={...}>`
- System keyboard keys and native OS modals **cannot** have testIDs

Full reference: `~/.hermes/skills/software-development/appium-real-device-testing/references/react-native-testid-pattern.md`

The testID branch is `feat/add-testids-issue-21` (3 commits: root view testIDs on onboarding screens + SetupCard prop fix).

## Environment Variables

```bash
# On Mac for Appium
SMOKE_DEVICE="ios"          # or "android"
SMOKE_UDID=""              # auto-detected if empty
SMOKE_DEVICE_NAME=""        # auto-detected if empty
SMOKE_PLATFORM_VERSION=""   # auto-detected if empty
SMOKE_APP=""               # auto-detected from DerivedData
NODE_PATH="$HOME/.nvm/versions/node/v20.19.2/lib/node_modules"
PATH="$HOME/.nvm/versions/node/v20.19.2/bin:/opt/homebrew/bin:$PATH"
```
