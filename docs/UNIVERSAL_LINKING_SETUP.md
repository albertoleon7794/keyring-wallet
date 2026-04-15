# Universal Linking Setup

Universal links allow the wallet to be opened directly from shared URLs on both iOS and Android, bypassing the browser. Two link paths are configured:

- `/invite` — wallet-to-wallet VRC exchange invitations
- `/connect` — remote witness server connections

## Static Site Files

These files must be hosted on each domain's static site at the root level. They tell iOS and Android which app is authorized to handle URLs from that domain.

### Apple App Site Association

Hosted at `https://<your-domain>/.well-known/apple-app-site-association` (no file extension). Must be served as `application/json` with no redirects.

```json
{
  "applinks": {
    "apps": [],
    "details": [
      {
        "appIDs": ["<TEAM_ID>.<BUNDLE_ID>"],
        "components": [
          {
            "/": "/invite*",
            "comment": "Wallet-to-wallet invitation links"
          }
        ]
      }
    ]
  }
}
```

For the witness domain, replace `/invite*` with `/connect*`.

### Android Asset Links

Hosted at `https://<your-domain>/.well-known/assetlinks.json`. This file tells Android which app is allowed to handle links from the domain. It must be served as `application/json` at the exact path `/.well-known/assetlinks.json` with no redirects.

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "<your-android-package-name>",
      "sha256_cert_fingerprints": [
        "<SHA-256-FINGERPRINT-OF-YOUR-SIGNING-KEY>"
      ]
    }
  }
]
```

Each domain (`wallet` and `witness`) needs its own copy of this file with the same content.

**Where the values come from:**

- `package_name` — your app's `applicationId` from `app/android/app/build.gradle`
- `sha256_cert_fingerprints` — the SHA-256 fingerprint of the signing key used to build the APK/AAB. For debug builds this is the debug keystore; for production it's the upload key registered in the Play Console.

To get the fingerprint from a keystore:

```bash
keytool -list -v -keystore <your-keystore>.jks | grep SHA256
```

Or from an installed APK on a device:

```bash
adb shell pm get-app-links <your-android-package-name>
```

If domain verification shows state `1024`, the fingerprint in `assetlinks.json` doesn't match the signing key — regenerate the file with the correct fingerprint.

### Fallback HTML

Each domain has a fallback `index.html` page (at `/invite/` and `/connect/`) that displays when the app is not installed. It includes Open Graph metadata for link previews, app store download buttons, and a direct "Open in App" link.

## iOS Configuration

**Entitlements** (`app/ios/AriesBifold/AriesBifold.entitlements`):

Both domains are registered with the `applinks:` prefix. The `?mode=developer` variants are for local development builds only.

```xml
<key>com.apple.developer.associated-domains</key>
<array>
  <string>applinks:<your-wallet-domain></string>
  <string>applinks:<your-wallet-domain>?mode=developer</string>
  <string>applinks:<your-witness-domain></string>
  <string>applinks:<your-witness-domain>?mode=developer</string>
</array>
```

**Native handling** (`app/ios/AriesBifold/AppDelegate.mm`):

The `continueUserActivity:restorationHandler:` delegate method forwards universal link URLs to React Native's `Linking` API.

## Android Configuration

**AndroidManifest.xml** (`app/android/app/src/main/AndroidManifest.xml`):

Intent filters with `autoVerify="true"` are registered for both domains:

```xml
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https" android:host="<your-wallet-domain>" android:pathPrefix="/invite" />
</intent-filter>

<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https" android:host="<your-witness-domain>" android:pathPrefix="/connect" />
</intent-filter>
```

**Native handling** (`app/android/.../MainActivity.kt`):

`onNewIntent` override ensures App Links are delivered when the app is already running (`singleTask` launch mode).

## CI / Provisioning

The iOS App Store provisioning profile must include the **Associated Domains** capability. The profile is stored as a base64-encoded GitHub Actions secret. If the profile is regenerated in the Apple Developer portal, update both:

1. The GitHub Actions secret with the new base64-encoded profile
2. The profile UUID in the export options plist used during archive export

To get the UUID from a downloaded `.mobileprovision` file:

```bash
security cms -D -i <profile>.mobileprovision | grep -A1 UUID
```

## React Native Side

- **Wallet invitations**: The universal link domain is defined in `bifold/packages/core/src/constants.ts` as the `domain` export. The app's deep link handler parses the `oob` query parameter to initiate a DIDComm connection.
- **Witness connections**: The witness server generates universal link URLs by rewriting its invitation URL to use the `/connect` path (see `bifold/packages/witness-server/src/WebServer.ts`).

## Troubleshooting

- **iOS not opening the app**: Check Settings → Developer → Universal Links → Diagnostics with the full URL. If it says "not a Universal Link for any installed app", the provisioning profile likely doesn't include Associated Domains — regenerate it and rebuild.
- **Android not verifying**: Run `adb shell pm get-app-links <your-package-name>` and check the domain verification state. A state of `1024` means verification failed — check that `assetlinks.json` is accessible and the SHA-256 fingerprint matches.
- **WhatsApp / in-app browsers**: Universal links may not trigger from third-party in-app browsers. The fallback HTML page handles this case with a manual "Open in App" button.
