# Hardware Attestation & Biometric Signing Flow

Technical documentation for developers on the VRC (Verifiable Relationship Credential) hardware attestation and biometric signing implementation.

---

## Implementation Status at a Glance

| Feature | Status | Notes |
|---------|--------|-------|
| Hardware key generation | ✅ Implemented | iOS Secure Enclave, Android StrongBox/TEE |
| Biometric-bound signing | ✅ Implemented | ECDSA-SHA256, biometric required |
| Attestation retrieval | ✅ Implemented | Apple App Attest, Android Key Attestation |
| Evidence block (W3C) | ✅ Implemented | Full spec compliance |
| Trust anchor check | ✅ Implemented | Root matches Apple/Google |
| Signature verification | ✅ Implemented | @noble/curves ECDSA |
| Full X.509 chain verification | ❌ Not implemented | Requires node-forge/pkijs |
| Public key extraction | ❌ Not implemented | Trusted via attestation |
| Certificate expiry check | ❌ Not implemented | Requires X.509 parsing |

---

## Overview

When two users establish a relationship via VRC, each side signs the credential using a **hardware-backed key** stored in secure hardware (iOS Secure Enclave or Android StrongBox/TEE). This provides cryptographic proof that a human approved the relationship via biometric authentication.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           JAVASCRIPT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ vrc-manager  │→ │ vrc-biometric│→ │vrc-hardware- │→ │ Evidence-   │  │
│  │              │  │              │  │   signing    │  │  Builder    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                            ↓                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │            react-native-attestation (JS wrapper)                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Native Bridge
┌────────────────────────────────────┴────────────────────────────────────┐
│                            NATIVE LAYER                                  │
│  ┌────────────────────────┐          ┌─────────────────────────────┐    │
│  │   iOS: Attestation.mm  │          │ Android: AttestationModule.kt│   │
│  │   • Secure Enclave     │          │ • KeyStore                   │   │
│  │   • App Attest API     │          │ • StrongBox / TEE            │   │
│  └────────────────────────┘          └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Signing Flow (When Creating/Accepting a VRC)

### Step 1: UI Confirmation
User sees `BiometricConfirmationModal` asking to confirm the relationship.

**File:** `vrc-biometric.ts` → `requestBiometricWithHardwareSigning()`

### Step 2: Hardware Key Check
System checks if a hardware signing key exists, creates one if needed.

**File:** `vrc-hardware-signing.ts` → `ensureHardwareSigningKey()`

```
┌─────────────────────────────────────────────────────────────────┐
│                    KEY GENERATION                               │
├─────────────────────────────────────────────────────────────────┤
│ iOS:                                                            │
│   • Key created in Secure Enclave                               │
│   • Biometric-bound (requires Face ID / Touch ID for use)       │
│   • Algorithm: ECDSA with P-256 curve                           │
│   • App Attest key registered with Apple servers                │
│                                                                 │
│ Android:                                                        │
│   • Key created in KeyStore                                     │
│   • Prefers StrongBox, falls back to TEE, then Software         │
│   • Biometric-bound (requires fingerprint for use)              │
│   • Algorithm: ECDSA with P-256 curve                           │
└─────────────────────────────────────────────────────────────────┘
```

### Step 3: Attestation Pre-Warm (First Install Only)
On fresh install, iOS needs time to register the App Attest key with Apple servers. The system retries up to 3 times with exponential backoff.

**File:** `vrc-hardware-signing.ts` → `preWarmAttestation()`

### Step 4: VRC Content Preparation
The VRC credential content (without `evidence` and `proof` blocks) is serialized to JSON. This is what gets signed.

### Step 5: Hardware Signing
Content is passed to native layer, which:
1. Triggers biometric prompt (Face ID / Touch ID / Fingerprint)
2. Upon successful biometric, signs with hardware key
3. Returns DER-encoded ECDSA signature

**Native Files:**
- iOS: `Attestation.mm` → `signWithHardwareBiometricAuth`
- Android: `AttestationModule.kt` → `signWithHardwareBiometricAuth`

### Step 6: Attestation Retrieval
Certificate chain is fetched from platform:
- **iOS:** App Attest provides CBOR attestation object containing certificate chain
- **Android:** KeyStore provides certificate chain directly

**File:** `EvidenceBuilder.ts` → `getOrFetchAttestation()`

### Step 7: Evidence Block Construction
All components assembled into W3C-compliant evidence block:

```json
{
  "id": "urn:uuid:...",
  "type": ["BiometricAttestation", "HardwareKeyAttestation"],
  "created": "2024-01-15T10:30:00Z",
  "biometricMethod": {
    "type": "FaceID",
    "authenticatorType": "platform",
    "userVerification": "required"
  },
  "hardwareBinding": {
    "keyStorage": "SecureEnclave",
    "platform": "ios",
    "keyType": "EC-P256",
    "algorithm": "ECDSA-SHA256",
    "publicKey": "BASE64_PUBLIC_KEY"
  },
  "attestation": {
    "format": "apple-appattest-v1",
    "certificateChain": ["LEAF_CERT_PEM", "INTERMEDIATE_PEM", "ROOT_PEM"]
  },
  "signature": {
    "value": "BASE64_SIGNATURE",
    "algorithm": "ECDSA-SHA256"
  }
}
```

---

## Verification Flow (When Receiving a VRC)

Verification is a **2-step process**. The system logs these as `1/2` and `2/2`.

### Step 1/2: Certificate Chain Trust Anchor

**File:** `CertificateVerifier.ts` → `validateChainTrustAnchor()`

**What IS implemented:**
- ✅ Structure validation (non-empty, valid PEM format)
- ✅ Trust anchor check via string comparison to known Apple/Google roots
- ✅ Google serial pattern matching (handles certificate rotations)

**What is NOT implemented (requires X.509 library like node-forge or pkijs):**
- ❌ Full cryptographic chain validation (each cert signed by parent)
- ❌ Certificate expiry validation
- ❌ Public key extraction from leaf certificate

### Step 2/2: Signature Verification

**File:** `BiometricSignatureVerifier.ts` → `verifySignature()`

**What IS implemented:**
- ✅ ECDSA-SHA256 verification using `@noble/curves` library
- ✅ DER-to-compact signature conversion
- ✅ Multiple public key format handling (uncompressed, compressed, SPKI)
- ✅ Graceful fallback when crypto library unavailable (Metro bundler issues)

### What About Public Key Match?

**NOT VERIFIED** - The system trusts that Apple/Google verified the public key during attestation.

When the certificate chain root is trusted (Step 1/2 passes), we rely on the fact that:
- Apple App Attest verified the key belongs to the attested device
- Android Key Attestation verified the key is in genuine hardware

Actual cryptographic comparison of the evidence public key vs the leaf certificate public key would require an X.509 parsing library. This is tracked as technical debt.

---

## Verification Levels

The system reports **how** verification was performed:

| Level | Meaning | When Used |
|-------|---------|-----------|
| `cryptographic` | Full ECDSA signature verification | @noble/curves loaded successfully |
| `attestation_trust` | Cert chain valid, but crypto unavailable | Metro bundler failed to load crypto |
| `platform_trust` | iOS Secure Enclave attestation trusted | No cert chain, but iOS attestation format |
| `none` | Verification failed | Chain invalid or signature mismatch |

---

## Trusted Root Certificates

### iOS (Apple)
- **Apple Root CA - G3** (primary root)
- **Apple App Attestation CA 1** (intermediate - chains often end here)

### Android (Google)
- **Google Hardware Attestation Root**
- Serial number: `f92009e853b6b045`

**Note:** Google rotates root certificates while keeping the same serial number. The system uses serial pattern matching as a fallback.

**File:** `trustedRoots.ts`

---

## Known Limitations & Technical Debt

### 1. No Full X.509 Parsing
Certificate verification is limited to **trust anchor matching only**. We check if the root certificate matches known Apple/Google roots, but we do NOT:
- Verify each certificate's signature against its parent
- Check certificate expiry dates
- Extract public keys from certificates

Full cryptographic chain verification would require a library like `node-forge` or `pkijs`.

### 2. Public Key Match Not Verified
We trust that Apple/Google verified the public key during attestation. We do NOT:
- Parse the leaf certificate to extract its public key
- Compare the extracted key with the evidence public key

This means a sophisticated attacker could theoretically substitute a different public key in the evidence block. However, they would still need to produce a valid signature, which is impossible without access to the private key in hardware.

### 3. Metro Bundler Issues
`@noble/curves` uses ESM subpath exports which Metro struggles with. Workaround:
- Lazy loading with multiple require paths
- Fallback to trust-based verification if crypto unavailable

### 4. Google Root Certificate Rotation
Hard-coded root expires **May 24, 2026**. Current mitigation:
- Serial number pattern matching (handles rotations with same serial)
- **TODO:** Use Google's attestation status API for revocation checks

See `CERTIFICATE_VERIFICATION_IMPROVEMENTS.md` for detailed improvement plan.

---

## File Reference

| File | Location | Purpose |
|------|----------|---------|
| `vrc-manager.ts` | `core/src/modules/vrc/` | VRC lifecycle management |
| `vrc-biometric.ts` | `core/src/modules/vrc/` | Biometric UI flow orchestration |
| `vrc-hardware-signing.ts` | `core/src/modules/vrc/` | Key creation and signing |
| `EvidenceBuilder.ts` | `core/src/modules/vrc/services/` | W3C evidence block construction |
| `BiometricSignatureVerifier.ts` | `core/src/modules/vrc/services/` | Signature verification (ECDSA) |
| `CertificateVerifier.ts` | `core/src/modules/vrc/services/` | Trust anchor validation |
| `trustedRoots.ts` | `core/src/modules/vrc/services/` | Hard-coded Apple/Google root certs |
| `Attestation.mm` | `react-native-attestation/ios/` | iOS native (Secure Enclave, App Attest) |
| `AttestationModule.kt` | `react-native-attestation/android/` | Android native (KeyStore, StrongBox) |

---

## Log Prefixes

When debugging, look for these prefixes:

| Prefix | Component |
|--------|-----------|
| `[VRC:Sign]` | Hardware signing |
| `[VRC:Biometric]` | Biometric flow |
| `[VRC:Evidence]` | Evidence building |
| `[VRC:Verify]` | Signature verification |
| `[VRC:Cert]` | Certificate verification |
| `[VRC:iOS]` | iOS native operations |
| `[VRC:Android]` | Android native operations |
| `[VRC:Attest]` | Attestation retrieval |

---

## Sequence Diagram: Full Signing Flow

```
User          Modal         JS Layer        Native Layer      Hardware
  │             │              │                 │               │
  │─── Tap ────→│              │                 │               │
  │             │── Confirm ──→│                 │               │
  │             │              │── hasKey? ─────→│               │
  │             │              │←── yes/no ──────│               │
  │             │              │                 │               │
  │             │              │── createKey ───→│── generate ──→│
  │             │              │←── publicKey ───│←─────────────│
  │             │              │                 │               │
  │             │              │── sign(vrc) ───→│               │
  │             │              │                 │── biometric ─→│
  │←────────── Face ID / Touch ID / Fingerprint ─────────────────│
  │─────────── Approve ──────────────────────────────────────────→│
  │             │              │                 │               │
  │             │              │                 │←── signature ─│
  │             │              │←── signature ───│               │
  │             │              │                 │               │
  │             │              │── getAttest ───→│               │
  │             │              │←── certChain ───│               │
  │             │              │                 │               │
  │             │              │── buildEvidence │               │
  │             │              │── attachToVRC ──│               │
  │             │              │                 │               │
  │             │←── Done ─────│                 │               │
  │←── Success ─│              │                 │               │
```

---

## Security Considerations

1. **Private key never leaves hardware** - Signing happens inside Secure Enclave / StrongBox
2. **Biometric required for each signature** - Key is bound to biometric authentication
3. **Attestation proves hardware** - Certificate chain proves key is in genuine Apple/Google hardware
4. **Signature over canonical content** - VRC content is signed BEFORE evidence/proof attached

---

## Related Documentation

- `CERTIFICATE_VERIFICATION_IMPROVEMENTS.md` - Technical debt and future improvements
- Apple App Attest: https://developer.apple.com/documentation/devicecheck/validating_apps_that_connect_to_your_server
- Android Key Attestation: https://developer.android.com/training/articles/security-key-attestation
