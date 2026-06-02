# Acme Mobile Banking — Mobile Client Technical Plan (v1)

## 1. Overview

Acme Mobile Banking is a native mobile application shipping on **Android** (min
SDK 26) and **iOS** (min iOS 15). It fronts the Acme banking backend (a REST API
documented separately) and lets a member view balances, move funds between
accounts, and pay bills. This document covers the **mobile client** design; the
backend authorization model is owned by the backend team and is out of scope
here except where the client interacts with it.

## 2. Authentication and session

- First login is username + password against the backend `/auth/login` endpoint,
  which returns an OAuth access token (1 hour) and a refresh token.
- **The refresh token is valid for 90 days. The client refreshes the access
  token transparently; there is no server-side revocation list and the token is
  not bound to the device.**
- On subsequent launches the member unlocks the app with **Face ID / fingerprint;
  the biometric check is a UI gate via `LAContext.evaluatePolicy` (iOS) and
  `BiometricPrompt` (Android) that, on success, loads the saved refresh token and
  resumes the session.** No Keystore/Keychain key is bound to the biometric.

## 3. On-device storage

- The access token and refresh token are persisted in **`SharedPreferences`
  (Android) and `NSUserDefaults` (iOS) so the session survives app restarts.**
- Cached account balances and the member profile (name, email, masked account
  numbers) are stored in a local SQLite database for offline viewing.
- **The client signs each API request with an HMAC using a shared secret
  `ACME_CLIENT_HMAC_KEY` that is compiled into the app; the same key ships in
  every install** so the backend can verify the request came from "the Acme app."

## 4. Network

- All API traffic is HTTPS. The Android `network_security_config.xml` pins the
  production leaf certificate; **a single pin is configured with no backup pin
  and no documented rotation procedure.** iOS uses App Transport Security with
  the default system trust store (no pinning on iOS).

## 5. Transfers and limits

- The transfer screen enforces the member's **daily transfer limit in the client:
  the app reads `dailyLimit` from the profile and refuses transfers above it. The
  backend accepts whatever amount the client submits** and records the transfer.
- Bill-pay and transfer can also be triggered by a deep link of the form
  `acmebank://transfer?to=<acct>&amount=<n>`. **The deep link handler performs the
  pre-filled transfer screen with no verification of which app or link invoked
  it** and the custom scheme is not an Android App Link.

## 6. Integrity and platform

- There is **no root/jailbreak detection, no anti-tampering, and no hardware
  attestation (Play Integrity / App Attest); the backend has no way to tell a
  genuine app on a stock device from a repackaged build on a rooted device.**
- A WebView renders the in-app marketing and statements PDF viewer.

## 7. Audit and privacy

- **Consequential actions (transfers, bill-pay, profile edits) are written to a
  local on-device audit log for support to read if the member calls in;** the
  backend logs only raw HTTP access lines without the device or app version.
- The app bundles the Acme analytics SDK and a third-party crash-reporting SDK.
- The app collects the advertising identifier (IDFA / GAID) on first launch for
  attribution.

## 8. Updates

- There is no forced-update or minimum-version mechanism; **old client versions
  keep working against the backend indefinitely.**
