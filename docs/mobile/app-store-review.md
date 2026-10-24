# App Review checklist — the iOS app (F25.3.1)

Checked against Apple's [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
as published on **2026-10-23** (the page carries no revision date; this is the day it was
read). Re-read the guidelines and update this table before every submission — the
"Checked" column is the date the row was last true.

| Guideline | What it asks | The app's answer | Checked |
|---|---|---|---|
| **2.1** App completeness | Final build, working links, a demo account, the backend live during review | Production build (`App (Production)` scheme, backend on Cloud Run). **To do before submitting:** a review account in production with a few receipts, its email and password in App Store Connect's review notes — never the owner's account. | 2026-10-23 |
| **2.3** Accurate metadata | Screenshots of the app in use, fictional data only (2.3.9), name ≤ 30 characters (2.3.7), 4+ metadata (2.3.8) | Name "Budget Agent". Screenshots from the demo account (`demo@example.com`, seed data), never real receipts. No country or currency in the copy (positioning rule). | 2026-10-23 |
| **3.1.1 / 3.1.3(f)** Payments | Digital features unlocked only through In-App Purchase; no purchase calls to action outside it | The store app names no price, no plan and no way to buy one, and links to none (F25.3.3); what is left of the AI credits is still shown. The paid plan is bought on the web only. | 2026-10-23 |
| **4.2** Minimum functionality | More than a repackaged website | Native camera with the system's access question first (F25.2.3), "Share → Budget Agent" for photos and PDFs from any app (F25.2.2), haptics, swipe back from the screen's edge, safe areas and native scroll bounce. | 2026-10-23 |
| **4.8** Login services | A third-party login as the primary one needs an equivalent privacy-minded option | Email and password are the app's own accounts. When Google sign-in is switched on (F1.6), Sign in with Apple is switched on with it — the buttons only appear together. | 2026-10-23 |
| **1.2 / 4.7** Generated content | Filtering, reporting offensive output, contact details | Every assistant reply can be reported (offensive, wrong, other) and admins see the reports (F22.4.2); the Help page's contact form (F17.10). | 2026-10-23 |
| **5.1.1** Data collection | Privacy policy in the metadata and in the app; purpose strings; data minimisation; account deletion in the app | `/privacy` linked from Settings and the store listing; purpose strings in en/uk/pl (`InfoPlist.strings`); photos come through the picker or the share sheet, not the whole library; Settings › Your data › Delete account (F17.9.1). | 2026-10-23 |
| **5.1.2(i)** Data shared with a third-party AI | Say what goes to which AI and ask explicitly first | The consent dialog names Google's Gemini on Vertex AI, what is sent and why; nothing goes to the model before "Allow", and it can be withdrawn in Settings (F25.3.2, ADR-0034). | 2026-10-23 |
| **Export compliance** | Declare non-exempt encryption | Only HTTPS through the system's own stack: `ITSAppUsesNonExemptEncryption` is `false` in `Info.plist`, so no question at each upload. | 2026-10-23 |

## Privacy manifest

`frontend/ios/App/App/PrivacyInfo.xcprivacy` follows the record of processing
(ADR-0020):

- **Tracking:** none, and no tracking domains.
- **Required-reason APIs in the app's own code:** none.
  - `SharedInbox.swift` lists its folder without reading file dates.
  - The web layer's storage is the web view's, not `UserDefaults`.
- **Plugins:**
  - Capacitor and Cordova ship empty manifests.
  - The camera library (`ion-ios-camera`) declares the file timestamp API (C617.1, 3B52.1) and photos for app functionality.
  - Haptics, status bar, splash screen and app plugins use none.
- **Collected, all linked to the account, none for tracking:**
  - for app functionality: name, email, other financial info (incomes, balances), photos, other user content (receipts, conversations) and customer support;
  - for analytics: product interaction (F17.3.1).

Re-check with *Product › Archive › Generate Privacy Report* after adding a plugin.

## The share extension

The app and its extension share the App Group `group.app.budgetagent`.

- **Signing:** automatic signing registers the group on a paid Apple Developer team. A free personal team cannot use App Groups.
- **What the extension takes:** images and PDFs only.
- **What it sends:** nothing leaves the phone from it.
