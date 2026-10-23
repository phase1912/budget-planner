# ADR 0033: Store apps from the web client, through Capacitor and one platform module

**Date:** 2026-10-24
**Status:** Accepted — F22.2.1, F25.2.1

## Context

The service goes to Google Play (E22) and possibly the App Store first (E25), depending on
which developer account clears. A native app per platform is the long-term aim (E26), but
three codebases before either store has accepted anything is a cost paid for nothing.
App Review rejects a website in a wrapper (4.2), so the apps must behave like apps: safe
areas, the system back gesture, the camera, sharing in — not a page with a frame.

## Decision

- **One client, three builds.** The Vite build is served from the device by Capacitor 8 in
  an Android project (`frontend/android/`) and an iOS project (`frontend/ios/`), committed
  with their generated output ignored. The API stays where it is; the apps call it from
  `https://localhost` (Android) and `capacitor://localhost` (iOS), both in `CORS_ORIGINS`.
- **The app id is `app.budgetagent`**, chosen by the author on 2026-10-24. It is permanent
  once a store has published it.
- **One platform module asks the device** (`frontend/src/platform/`): a `Device` with a web
  and a native implementation, chosen once at start. Screens ask it — is this an app, go back,
  colour the bars — and never test for Capacitor themselves, so the website is unchanged.
- **Edge to edge everywhere.** `viewport-fit=cover` and the device's safe-area insets pad the
  page, the tab bar and sheets, on the site and in both apps; a solid strip sits under the
  status bar so the page scrolls beneath it.
- **The apps open on signing in**, not the website's landing, and never offer to be added to
  the home screen or register the service worker: their files are on the device already.

## Consequences

- A release of the client is a release of three things; the store apps update only when a
  new build is published (F22.3), while the site updates on every deploy.
- Native code is kept to what the web cannot do. On iOS, the swipe from the left edge is a
  native edge-pan gesture in `AppViewController` (`ios/App/App/AppDelegate.swift`, made the
  root by `SceneDelegate`) that asks the router to go back: the web view's own back-forward
  gesture does not follow a single-page router.
- Moving a screen to native code later (E26) replaces its use of the platform module, not
  the API.
