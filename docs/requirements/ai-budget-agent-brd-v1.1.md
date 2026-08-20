# Business Requirements Document (BRD)
## AI Budget Agent

| | |
|---|---|
| **Document status** | Draft v1.2 |
| **Prepared for** | Product / Engineering stakeholders |
| **Change log** | BR-7 (Identity & Access) and Gherkin for the section 8 NFRs added — F0.10 |

---

## 1. Executive Summary

The business proposes to build an AI-powered agent that helps individual users understand and control their personal spending by automatically digitizing paper receipts ("checks"), organizing that data into budget categories, and delivering personalized, goal-driven financial advice. Today, users who want to track spending from paper receipts must either manually log purchases (high effort, low adoption) or rely on bank/card transaction feeds, which do not capture item-level detail (e.g., what was actually bought, not just the merchant and total). This product closes that gap by turning a simple photo of a receipt into structured, categorized, and actionable financial insight.

## 2. Business Objectives

| ID | Objective |
|---|---|
| BO-1 | Reduce the effort required for a user to track personal spending to a single action: photographing a receipt. |
| BO-2 | Provide users with item-level ("position-level") visibility into their spending, not just merchant/total-level visibility. |
| BO-3 | Help users understand where their money goes by category, on a monthly basis. |
| BO-4 | Increase user engagement and retention by delivering proactive, personalized budget guidance tied to the user's own goals. |
| BO-5 | Support both explicit financial goals (e.g., savings targets) and everyday lifestyle goals (e.g., losing weight, saving for a purchase), broadening the product's relevance beyond finance-focused users. |

## 3. Background & Problem Statement

Manual expense tracking has a well-known adoption problem: users abandon budgeting apps because logging every purchase by hand is tedious. Bank/card transaction data solves part of this but loses the detail of *what* was purchased — a single "Fresh Market — 84.50 PLN" line tells the user nothing about whether that was groceries, alcohol, or household goods. Receipts already contain this detail; the business opportunity is to extract it automatically via photo capture and turn it into a low-effort, high-insight budgeting experience.

## 4. Scope

### 4.1 In Scope

| Ref | Business Capability |
|---|---|
| BR-1 | Digitize receipt photos into structured purchase data |
| BR-2 | Recognize when a single long receipt has been captured across multiple photos, so items are not double-counted |
| BR-3 | Classify individual purchased items into spending categories |
| BR-4 | Calculate a user's total monthly spend from their digitized receipts |
| BR-5 | Provide spend breakdowns and comparisons by category |
| BR-6 | Provide personalized budget optimization advice based on a user-defined goal (financial or lifestyle) |
| BR-7 | Register and authenticate a user account, including sign-in via a linked identity provider, so every other capability above operates on a specific, verified user |

### 4.2 Out of Scope (for this phase)

- Direct integration with bank accounts or card transaction feeds.
- Multi-currency conversion (single-currency operation assumed; currency is configurable per user).
- Shared/household budgets across multiple user accounts.
- Automated bill payment or financial transactions of any kind — the agent advises, it does not act on the user's finances.
- Tax filing or tax-advice functionality.

## 5. Stakeholders

| Role | Interest |
|---|---|
| End user | Wants low-effort, accurate insight into personal spending and actionable advice toward their goals. |
| Product owner | Wants a differentiated, engaging budgeting product that drives retention. |
| Development team | Needs unambiguous, testable requirements to build against. |
| QA | Needs defined acceptance scenarios to validate behavior. |
| Compliance / Data privacy | Needs assurance that financial and personal data are handled securely (see Section 10). |

## 6. Glossary

| Term | Definition |
|---|---|
| Check / Receipt | A photographed proof-of-purchase document |
| Position | A single line item on a receipt (product/service + price + quantity) |
| Position match | Determination that a position on one photo is the same real-world item as a position on another photo of the same receipt |
| Category | A budget classification assigned to a position (e.g., Groceries, Transport, Utilities) |
| Budget period | The monthly window (calendar month by default) used for aggregation |
| Goal | A user-declared objective, either financial (e.g., "save 500 PLN/month") or lifestyle-based (e.g., "lose weight", "save up to buy a car"), which the agent maps to relevant spending categories or items |
| Identity provider | A third-party service (Google, Facebook) a user can authenticate through instead of a password, linked to their account on a verified email match |
| Administrator | An account role limited to product operation; never grants access to an individual user's own receipts or statistics (N2) |

### 6.1 EARS Pattern Reference

Detailed requirements below use **EARS** (Easy Approach to Requirements Syntax):

| Pattern | Form | Use case |
|---|---|---|
| Ubiquitous | The system shall `<response>` | Always-true behavior |
| Event-driven | When `<trigger>`, the system shall `<response>` | Triggered by an event |
| State-driven | While `<state>`, the system shall `<response>` | Behavior tied to a mode/state |
| Unwanted behavior | If `<trigger/condition>`, then the system shall `<response>` | Error/exception handling |
| Optional feature | Where `<feature is included>`, the system shall `<response>` | Conditional on configuration |

Acceptance criteria are illustrated using **BDD** (Gherkin: Given/When/Then).

---

## 7. Business Requirements (Detailed)

### BR-1 — Receipt Digitization

**Business intent:** A user can submit a photo of a receipt and receive back a structured, storable record of that purchase (merchant, date, items, prices, total), with clear handling for illegible or incomplete photos so that bad data does not silently corrupt the user's budget.

**Detailed requirements (EARS):**

- **A1 (Event-driven):** When a user submits a check photo, the agent shall validate that the file is a supported image format (JPEG, PNG, HEIC, PDF-scan) before processing.
- **A2 (Unwanted behavior):** If the submitted file is not a supported format, then the agent shall reject the upload and return an error message specifying accepted formats.
- **A3 (Ubiquitous):** The agent shall allow the user to choose between two upload modes: "single receipt" (one receipt, captured across one or more photos) and "multiple receipts" (several distinct receipts submitted in the same session).
- **A4 (State-driven):** While the user is in "single receipt" mode, the agent shall accept up to 10 photos and a combined file size of up to 50 MB for that receipt.
- **A5 (State-driven):** While the user is in "multiple receipts" mode, the agent shall present one upload line per receipt, and for each line shall independently accept up to 10 photos and a combined file size of up to 50 MB.
- **A6 (Ubiquitous):** The agent shall allow the user to add additional upload lines in "multiple receipts" mode, each subject independently to the 10-photo and 50 MB limits.
- **A7 (Unwanted behavior):** If the number of photos submitted for a single receipt (in either mode, or for a given line in "multiple receipts" mode) exceeds 10, then the agent shall reject the additional photos and inform the user of the 10-photo limit.
- **A8 (Unwanted behavior):** If the combined file size submitted for a single receipt (in either mode, or for a given line in "multiple receipts" mode) exceeds 50 MB, then the agent shall reject the upload and inform the user of the 50 MB limit.
- **A9 (Event-driven):** When a valid check photo is received, the agent shall extract, at minimum, merchant name, transaction date, transaction time, line items (name, quantity, unit price, total price), and total amount.
- **A10 (Unwanted behavior):** If the OCR/parsing confidence for a required field falls below a defined threshold, then the agent shall flag that field as "low confidence" rather than silently accepting it.
- **A11 (Unwanted behavior):** If the agent cannot extract a total amount or transaction date, then the agent shall mark the receipt as "requires manual review" and shall not include it in automated budget calculations until resolved.
- **A12 (Event-driven):** When parsing succeeds, the agent shall persist the extracted receipt (header + line items + original image reference) to the database with a unique receipt ID.
- **A13 (Event-driven):** When a receipt is persisted, the agent shall associate it with the submitting user's account ID.
- **A14 (Unwanted behavior):** If a duplicate receipt (same merchant, date, and total) is detected on ingestion, then the agent shall prompt the user to confirm whether this is a new purchase or a duplicate upload before storing.
- **A15 (Ubiquitous):** The agent shall record a processing timestamp and parser version for every stored receipt.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Receipt photo parsing and storage

  Scenario: Successfully parse and store a valid receipt photo
    Given the user is logged in
    And the user has a clear JPEG photo of a grocery store receipt
    When the user submits the photo to the agent
    Then the agent should extract merchant name, date, line items, and total amount
    And the agent should store the parsed receipt in the database
    And the agent should link the original photo to the stored record

  Scenario: Reject unsupported file format
    Given the user is logged in
    When the user submits a ".docx" file instead of a photo
    Then the agent should reject the upload
    And the agent should return an error stating supported formats are JPEG, PNG, HEIC, and PDF-scan

  Scenario: Upload a single receipt within limits
    Given the user selects "single receipt" upload mode
    When the user uploads 4 photos totaling 20 MB for that receipt
    Then the agent should accept all 4 photos
    And process them as one receipt

  Scenario: Reject exceeding photo count in single receipt mode
    Given the user selects "single receipt" upload mode
    When the user attempts to upload 11 photos for that receipt
    Then the agent should reject the 11th photo
    And inform the user of the 10-photo limit

  Scenario: Reject exceeding size limit in single receipt mode
    Given the user selects "single receipt" upload mode
    When the user attempts to upload photos totaling 55 MB for that receipt
    Then the agent should reject the upload
    And inform the user of the 50 MB limit

  Scenario: Upload multiple receipts across separate lines
    Given the user selects "multiple receipts" upload mode
    When the user adds two upload lines, one for a grocery receipt and one for a restaurant receipt
    And uploads 3 photos totaling 15 MB to the first line
    And uploads 2 photos totaling 10 MB to the second line
    Then the agent should accept both lines
    And process each line as a separate receipt

  Scenario: Reject exceeding limits on one line in multiple receipts mode
    Given the user selects "multiple receipts" upload mode
    And has added two upload lines
    When the user attempts to upload 12 photos to the first line
    Then the agent should reject the additional photos on that line
    And inform the user of the 10-photo limit
    And the second line should remain unaffected

  Scenario: Flag low-confidence extraction
    Given the user submits a blurry receipt photo
    When the agent parses the photo
    And the confidence score for the total amount is below the acceptable threshold
    Then the agent should mark the total amount field as "low confidence"
    And the agent should prompt the user to confirm or correct the value

  Scenario: Handle missing critical fields
    Given the user submits a photo where the total amount is not visible
    When the agent attempts to parse the photo
    Then the agent should mark the receipt as "requires manual review"
    And the receipt should be excluded from automatic budget calculations

  Scenario: Detect potential duplicate upload
    Given a receipt from "Fresh Market" dated 2026-07-20 for 84.50 PLN already exists in the database
    When the user uploads another photo with the same merchant, date, and total
    Then the agent should notify the user of a potential duplicate
    And the agent should ask the user to confirm whether to store it as a new receipt
```

---

### BR-2 — Multi-Photo Receipt Continuity

**Business intent:** When a single receipt is too long for one photo and is captured across multiple photos, the agent recognizes items that appear in more than one photo so they are counted only once in the user's spending.

**Detailed requirements (EARS):**

*Use case: a single receipt is too long to fit in one photo, so the user captures it across two (or more) overlapping photos. The agent must determine whether a given line item ("position") extracted from one photo is the exact same line item also captured in another photo of that same receipt, so it is not counted twice.*

- **B1 (Event-driven):** When two check photos are provided for comparison, the agent shall extract line-item data from both photos independently before comparison.
- **B2 (Event-driven):** When comparing two extracted positions, the agent shall check whether item name, unit price, quantity, and total price match exactly between the two positions.
- **B3 (State-driven):** While the two positions are known to originate from the same physical receipt and item name, unit price, quantity, and total price all match exactly, the agent shall classify the pair as "same position."
- **B4 (Unwanted behavior):** If any of item name, unit price, quantity, or total price differs between the two positions, then the agent shall classify the pair as "different position."
- **B5 (Ubiquitous):** The agent shall only perform same-position comparison between photos suspected to be of the same physical receipt (e.g., multiple overlapping photos of one long check), not across separate receipts or transactions.
- **B6 (Unwanted behavior):** If one or both photos fail parsing, then the agent shall not attempt a position match and shall return a "comparison not possible" result with the reason.
- **B7 (Ubiquitous):** The agent shall allow the user to manually override an automatic same-position/different-position determination.
- **B8 (Event-driven):** When a user overrides a match determination, the agent shall store the corrected label for future model evaluation/tuning.
- **B9 (Ubiquitous):** The agent shall not classify matching items found on two separate receipts (distinct purchase transactions) as "same position," even when item name, price, and quantity are identical, since recurring purchases across different checks are expected and are not duplicates.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Same-position detection across two check photos

  Scenario: Identify identical position split across two photos of the same long receipt
    Given the user photographs a long receipt in two overlapping shots because it does not fit in one frame
    And the item "Bananas 1kg" priced at 3.20 PLN, quantity 1, appears near the bottom of photo one
    And the same item "Bananas 1kg" priced at 3.20 PLN, quantity 1, also appears near the top of photo two
    When the agent compares the line items from both photos
    Then the pair should be classified as "same position"

  Scenario: Any differing field results in a different position
    Given a position named "Milk 2% 1L" priced at 4.50 PLN appears on photo one
    And a position named "Milk 2% 1L" priced at 4.60 PLN appears on photo two
    When the agent compares the two positions
    Then the agent should classify the pair as "different position"

  Scenario: Identify different positions across two different receipts
    Given the user uploads a photo of a grocery receipt
    And a photo of a restaurant receipt
    When the agent compares the line items between the two photos
    Then no items should be classified as "same position"

  Scenario: Recurring purchase across different receipts is not treated as same position
    Given the user has a receipt dated July 1, 2026 containing "Milk 2% 1L" priced at 4.50 PLN
    And a separate receipt dated July 8, 2026 containing "Milk 2% 1L" priced at 4.50 PLN
    When the agent compares positions across these two distinct receipts
    Then the agent should not classify the pair as "same position"
    And the agent should treat them as two independent purchases

  Scenario: Comparison not possible due to parsing failure
    Given one of the two uploaded photos fails to parse
    When the user requests a same-position comparison
    Then the agent should return "comparison not possible"
    And the agent should state the reason as a parsing failure

  Scenario: User overrides an automatic match decision
    Given the agent classified two positions as "same position"
    When the user marks the pair as "different position"
    Then the agent should update the stored classification to "different position"
    And the agent should log the correction for future tuning
```

---

### BR-3 — Spend Categorization

**Business intent:** Every purchased item is classified into a spending category (e.g., Groceries, Dining, Transport), with the ability for users to correct categorization and define their own custom categories, so that budget reporting is meaningful and personalized.

**Detailed requirements (EARS):**

- **C1 (Event-driven):** When a receipt is successfully parsed, the agent shall assign a category to each line item from a predefined category taxonomy (e.g., Groceries, Dining, Transport, Utilities, Health, Entertainment, Other).
- **C2 (Ubiquitous):** The agent shall support at least one "Other/Uncategorized" fallback category for items it cannot confidently classify.
- **C3 (State-driven):** While the categorization confidence for an item is below the configured threshold, the agent shall assign it to "Uncategorized" and flag it for user review.
- **C4 (Ubiquitous):** The agent shall allow the user to manually reassign the category of any line item.
- **C5 (Event-driven):** When a user manually reassigns a category, the agent shall store the correction and apply it to future items with the same or highly similar name from the same merchant.
- **C6 (Ubiquitous):** The agent shall support user-defined custom categories in addition to the default taxonomy.
- **C7 (Event-driven):** When a new custom category is created, the agent shall make it available for both manual and automatic assignment going forward.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Categorization of receipt line items

  Scenario: Automatically categorize a recognized item
    Given a parsed receipt contains the item "Bananas 1kg"
    When the agent categorizes the receipt
    Then the item should be assigned to the "Groceries" category
    And the categorization confidence should be recorded

  Scenario: Fallback to Uncategorized for unrecognized item
    Given a parsed receipt contains an item with an ambiguous or unknown name
    When the agent attempts to categorize it
    And the categorization confidence is below the threshold
    Then the item should be assigned to "Uncategorized"
    And flagged for user review

  Scenario: User corrects a category and agent learns from it
    Given the item "Protein Bar XL" was categorized as "Groceries"
    When the user reassigns it to "Health"
    Then the agent should update the category for that item
    And future receipts from the same merchant with the same item name should be categorized as "Health"

  Scenario: User creates a custom category
    Given the user wants to track "Pet Supplies" separately
    When the user creates a new category named "Pet Supplies"
    Then the category should be added to the available taxonomy
    And it should be selectable for manual or automatic assignment on future receipts
```

---

### BR-4 — Monthly Budget Calculation

**Business intent:** The user can see their total spend for the current month (in progress) and for any completed month, based on when purchases actually occurred, so they understand their real spending pace.

**Detailed requirements (EARS):**

- **D1 (Event-driven):** When the user requests a monthly budget summary, the agent shall aggregate the total amount of all categorized, non-flagged receipts within the selected month.
- **D2 (Ubiquitous):** The agent shall calculate the monthly total as the sum of all line-item totals across all receipts dated within that calendar month, using the receipt's transaction date, not the upload date.
- **D3 (Unwanted behavior):** If a receipt is marked "requires manual review," then the agent shall exclude it from the monthly budget total and shall indicate the number/value of excluded receipts in the summary.
- **D4 (State-driven):** While the current date is within an in-progress month, the agent shall present the budget total as a "month-to-date" figure and shall clearly label it as incomplete.
- **D5 (Event-driven):** When a month is complete, the agent shall generate and persist a finalized monthly budget snapshot.
- **D6 (Ubiquitous):** The agent shall support recalculation of a monthly budget if a receipt within that month is edited, added, or removed after the initial calculation.
- **D7 (Optional feature):** Where the user has defined a target monthly budget limit, the agent shall show the current spend as a percentage of that limit.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Monthly budget calculation

  Scenario: Calculate completed month's budget
    Given the user has 15 fully parsed and categorized receipts dated in June 2026
    When the user requests the June 2026 budget summary
    Then the agent should return the sum of all line-item totals for June 2026
    And label the summary as finalized

  Scenario: Calculate in-progress month's budget
    Given the current date is July 27, 2026
    And the user has receipts dated from July 1 to July 27, 2026
    When the user requests the July 2026 budget summary
    Then the agent should return a month-to-date total
    And clearly label it as incomplete

  Scenario: Exclude receipts requiring manual review
    Given the user has 10 valid receipts and 2 receipts flagged "requires manual review" in July 2026
    When the agent calculates the July 2026 budget
    Then the total should only include the 10 valid receipts
    And the summary should note that 2 receipts were excluded pending review

  Scenario: Recalculate budget after receipt edit
    Given a finalized budget snapshot exists for June 2026
    When the user edits the total amount of a receipt dated in June 2026
    Then the agent should recalculate the June 2026 budget
    And update the stored snapshot

  Scenario: Show spend against a user-defined budget limit
    Given the user has set a monthly budget limit of 3000 PLN
    And month-to-date spend is 1800 PLN
    When the user requests the current budget status
    Then the agent should display the spend as 60% of the defined limit
```

---

### BR-5 — Category Statistics

**Business intent:** The user can view and compare their spending by category across any given time period, so they can identify where their money is going and how that changes over time.

**Detailed requirements (EARS):**

- **E1 (Event-driven):** When the user requests category statistics for a period, the agent shall calculate the total spend, percentage of overall spend, and transaction count per category.
- **E2 (Ubiquitous):** The agent shall support statistics requests for arbitrary date ranges, not only calendar months.
- **E3 (Event-driven):** When the user requests a comparison between two periods, the agent shall calculate the change in spend (absolute and percentage) per category between the two periods.
- **E4 (Ubiquitous):** The agent shall rank categories by total spend, from highest to lowest, in the default statistics view.
- **E5 (Unwanted behavior):** If a requested period contains no data, then the agent shall inform the user that no receipts were found for that period rather than returning an empty or zero-filled report silently.
- **E6 (Optional feature):** Where the user requests it, the agent shall present statistics visually (e.g., chart-ready data) in addition to tabular/numeric form.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Category-based spending statistics

  Scenario: Retrieve category breakdown for a month
    Given the user has categorized receipts for July 2026
    When the user requests category statistics for July 2026
    Then the agent should return total spend, percentage share, and transaction count for each category
    And categories should be ranked from highest to lowest spend

  Scenario: Compare spending across two months
    Given the user has categorized receipts for both June 2026 and July 2026
    When the user requests a comparison between June and July 2026
    Then the agent should return the absolute and percentage change in spend for each category

  Scenario: Request statistics for a period with no data
    Given the user has no receipts dated in March 2025
    When the user requests category statistics for March 2025
    Then the agent should inform the user that no receipts were found for that period

  Scenario: Request a custom date range
    Given the user has receipts spanning multiple months
    When the user requests statistics from July 10, 2026 to July 24, 2026
    Then the agent should return category totals limited to that date range
```

---

### BR-6 — Goal-Based Optimization Advice

**Business intent:** The user can state a goal — financial (e.g., a savings target) or lifestyle-based (e.g., losing weight, saving for a car) — and receive specific, actionable, item- or category-level recommendations tied to that goal, with proactive warnings if the user's current spending puts the goal at risk.

**Detailed requirements (EARS):**

- **F1 (Ubiquitous):** The agent shall allow the user to define a goal, including purely financial goals (e.g., target savings amount, spending reduction target for a specific category, target overall budget ceiling) and lifestyle goals (e.g., losing weight, saving toward a large purchase such as a car).
- **F2 (Event-driven):** When the user requests optimization advice, the agent shall analyze historical category- and position-level statistics to identify the categories or specific recurring items with the highest spend, the largest recent increase, or the strongest relevance to the stated goal.
- **F3 (Event-driven):** When generating advice, the agent shall produce specific, actionable recommendations tied to at least one identified category or individual recurring position (e.g., "reduce Dining spend by X to meet your goal" for a savings goal, or "stop buying cookies" for a weight-loss goal), not only generic tips.
- **F4 (Ubiquitous):** The agent shall quantify the projected impact of each recommendation on the user's stated goal (e.g., expected monthly savings, or reduction in relevant purchases, if followed).
- **F5 (Unwanted behavior):** If the user has insufficient historical data (e.g., fewer than a configured minimum number of receipts or less than one full month), then the agent shall inform the user that more data is needed for reliable advice rather than generating a low-confidence recommendation.
- **F6 (State-driven):** While the user's actual spend is on track to meet their stated goal, the agent shall report positive progress rather than suggesting unnecessary changes.
- **F7 (Event-driven):** When the user's actual spend puts the goal at risk, the agent shall proactively surface a warning along with recommendations before the month ends.
- **F8 (Optional feature):** Where the user provides feedback that a recommendation was not followed or not helpful, the agent shall take that feedback into account when generating future recommendations.
- **F9 (Optional feature):** Where the user's stated goal is a lifestyle goal rather than a purely financial one, the agent shall translate the goal into relevant spending categories and/or specific recurring items (e.g., mapping "lose weight" to snacks, sweets, and alcohol purchases, or mapping "buy a car" to a savings target) before generating recommendations.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Budget optimization advice

  Scenario: Generate advice tied to a savings goal
    Given the user has set a goal to save 500 PLN this month
    And category statistics show Dining is the highest and fastest-growing category
    When the user requests optimization advice
    Then the agent should recommend a specific reduction in Dining spend
    And state the projected monthly savings if the recommendation is followed

  Scenario: Generate position-based advice tied to a lifestyle goal
    Given the user has set a goal to lose weight
    And purchase history shows recurring purchases of cookies and sugary snacks
    When the user requests optimization advice
    Then the agent should translate the weight-loss goal into relevant spending items
    And recommend reducing or stopping purchases of cookies specifically
    And state the relevance of this recommendation to the user's stated goal

  Scenario: Insufficient data for advice
    Given the user has only 3 receipts total, all from the current week
    When the user requests optimization advice
    Then the agent should inform the user that more historical data is needed
    And should not generate a specific recommendation

  Scenario: User is already on track to meet their goal
    Given the user's goal is to stay under 3000 PLN this month
    And month-to-date spend is proportionally on pace to finish under 3000 PLN
    When the user requests optimization advice
    Then the agent should report that the user is on track
    And should not suggest unnecessary spending cuts

  Scenario: Proactive warning when goal is at risk
    Given the user's goal is to stay under 3000 PLN this month
    And month-to-date spend is on pace to exceed 3400 PLN by month end
    When the agent evaluates progress mid-month
    Then the agent should proactively notify the user that the goal is at risk
    And provide at least one specific recommendation to course-correct

  Scenario: Agent incorporates user feedback on past advice
    Given the agent previously recommended reducing "Entertainment" spend
    And the user marked that recommendation as "not helpful"
    When the agent generates new optimization advice
    Then the agent should deprioritize similar "Entertainment"-focused recommendations
    And consider alternative categories for suggestions
```

---

### BR-7 — Identity & Access

**Business intent:** A person can create an account and authenticate with it — with an email
and password, or by signing in through a linked Google or Facebook identity — so that every
other capability in this document operates on a specific, verified user rather than an
anonymous session. An administrator can operate the product without that access ever
extending to an individual user's own financial data (N2).

**Detailed requirements (EARS):**

- **G1 (Ubiquitous):** The system shall allow a person to register an account with an email
  address and a password.
- **G2 (Event-driven):** When a registration is submitted for an email address already
  associated with an account, the system shall reject it without revealing whether that
  address is registered.
- **G3 (Event-driven):** When valid credentials are submitted, the system shall authenticate
  the person and establish a session.
- **G4 (Unwanted behavior):** If submitted credentials are invalid, whether the email is
  unknown or the password is wrong, then the system shall return the same generic error for
  both cases.
- **G5 (Event-driven):** When an access token expires, the system shall allow it to be
  refreshed using a valid, unexpired, unrevoked refresh token, without requiring the person
  to log in again.
- **G6 (Unwanted behavior):** If a refresh token is presented a second time after already
  being exchanged once, then the system shall revoke every token issued from that session and
  require the person to log in again.
- **G7 (Event-driven):** When a person logs out, the system shall revoke the current session
  so its access and refresh tokens can no longer be used.
- **G8 (Ubiquitous):** The system shall support an administrator role, limited to product
  operation (e.g. default category taxonomy, system health, audit logs), to which N2's
  per-user data isolation applies exactly as it does to any other account — an administrator
  shall never be able to read an individual user's receipts, line items or statistics.
- **G9 (Optional feature):** Where a person chooses to sign in via Google or Facebook, the
  system shall authenticate them through that provider's OpenID Connect flow as an
  alternative to a password.
- **G10 (Event-driven):** When a person completes an OIDC sign-in for the first time, the
  system shall link that identity to an existing account only if the provider reports a
  verified email matching that account's email.
- **G11 (Unwanted behavior):** If the provider's email is not reported as verified, then the
  system shall not link the identity to any existing account and shall require the person to
  complete an explicit verification step before it can be linked.
- **G12 (Ubiquitous):** The system shall allow a person to authenticate with either their
  password or any identity provider linked to their account, and to link or unlink a provider
  from an existing account.

**Acceptance scenarios (BDD):**

```gherkin
Feature: Registration, authentication and identity linking

  Scenario: Register a new account
    Given no account exists for "new.user@example.com"
    When the person registers with that email and a password
    Then the system should create the account
    And establish an authenticated session

  Scenario: Reject registration with an email already in use
    Given an account already exists for "existing.user@example.com"
    When someone registers using that same email address
    Then the system should reject the registration
    And the response should not reveal that the address is already registered

  Scenario: Log in with valid credentials
    Given a registered account with a known email and password
    When the person submits the correct email and password
    Then the system should authenticate them
    And establish a session

  Scenario: Reject login with invalid credentials
    Given a registered account
    When the person submits an unknown email, or the correct email with the wrong password
    Then the system should return the same generic authentication error in both cases

  Scenario: Refresh an expired access token
    Given the person has an authenticated session and an unexpired refresh token
    When their access token expires and they present the refresh token
    Then the system should issue a new access token
    And the person should not be required to log in again

  Scenario: Detect reuse of an already-exchanged refresh token
    Given a refresh token that has already been exchanged once
    When that same refresh token is presented again
    Then the system should revoke every token issued from that session
    And require the person to log in again

  Scenario: Log out revokes the session
    Given the person has an authenticated session
    When the person logs out
    Then the system should revoke that session's access and refresh tokens

  Scenario: Administrator access does not extend to a user's financial data
    Given an administrator account and a separate user account with stored receipts
    When the administrator uses the product
    Then the administrator should not be able to read that user's receipts, line items or statistics

  Scenario: Sign in via Google for the first time, linking to a matching verified account
    Given a registered account exists for "person@example.com"
    And Google reports "person@example.com" as a verified email for the signing-in identity
    When the person signs in with Google for the first time
    Then the system should link the Google identity to the existing account
    And establish an authenticated session

  Scenario: Reject linking on an unverified provider email
    Given a registered account exists for "person@example.com"
    And Google reports "person@example.com" as an unverified email for the signing-in identity
    When the person attempts to sign in with Google for the first time
    Then the system should not link the Google identity to the existing account
    And should require an explicit verification step before linking

  Scenario: Sign in with either a linked provider or a password
    Given an account with both a password and a linked Google identity
    When the person authenticates with the password, or separately with Google
    Then the system should authenticate them in either case
```

---

## 8. Cross-Cutting Non-Functional Requirements

- **N1 (Ubiquitous):** The agent shall store all receipt images and extracted data encrypted at rest.
- **N2 (Ubiquitous):** The agent shall associate all stored data with a specific user account and shall not expose one user's receipts or statistics to another user.
- **N3 (Event-driven):** When a user deletes a receipt, the agent shall remove it from all budget and statistics calculations within the same session.
- **N4 (Performance/Event-driven):** When a check photo is submitted, the agent shall return a parsing result (success, flagged, or failure) within a defined maximum response time (target: under 10 seconds for a single receipt).
- **N5 (Ubiquitous):** The agent shall log all automatic classification decisions (category, position match) with confidence scores to support auditing and model improvement.
- **N6 (Ubiquitous):** The agent shall provide a way to export the user's stored receipt and statistics data (e.g., CSV/JSON export).

**Acceptance scenarios (BDD):**

```gherkin
Feature: Cross-cutting non-functional requirements

  Scenario: Receipt images and extracted data are encrypted at rest
    Given a receipt has been parsed and stored
    When the underlying storage is inspected directly, bypassing the application
    Then the receipt image and the extracted financial fields should not be readable as plain text

  Scenario: A user cannot access another user's data
    Given user A has stored receipts and statistics
    When user B requests user A's receipts or statistics
    Then the system should deny access
    And should not reveal whether the requested records exist

  Scenario: Deleting a receipt removes it from budget and statistics immediately
    Given a receipt contributes to the current month's budget total and category statistics
    When the user deletes that receipt
    Then the budget total and category statistics should exclude it within the same session

  Scenario: Parsing responds within the performance target
    Given a user submits a single receipt photo
    When the agent processes it
    Then the agent should return a parsing result — success, flagged, or failure — within the defined maximum response time

  Scenario: Automatic classification decisions are logged with confidence scores
    Given the agent assigns a category to a line item or matches two positions automatically
    When that decision is made
    Then the agent should log the decision with its confidence score

  Scenario: A user exports their stored data
    Given a user has receipts and statistics stored
    When the user requests an export
    Then the agent should provide their receipt and statistics data in a structured format (e.g. CSV or JSON)
```

## 9. Suggested Data Model (for development reference)

| Entity | Key Fields |
|---|---|
| User | user_id, email, password_hash (nullable — a provider-only account has none), role (user / admin), currency, budget_limit, goal |
| IdentityLink | link_id, user_id, provider (google / facebook), provider_user_id, provider_email, linked_at |
| Receipt | receipt_id, user_id, image_ref, merchant, transaction_date, transaction_time, total_amount, status (parsed / flagged / manual_review), parser_version, created_at |
| LineItem | line_item_id, receipt_id, name, quantity, unit_price, total_price, category_id, category_confidence, is_manual_override |
| Category | category_id, name, is_custom, user_id (nullable for default categories) |
| PositionMatch | match_id, item_a_id, item_b_id, result (same/different), is_manual_override |
| MonthlySnapshot | snapshot_id, user_id, period_start, period_end, total_spend, status (in_progress/finalized) |
| Recommendation | recommendation_id, user_id, goal_id, category_id, message, projected_impact, user_feedback |

## 10. Assumptions

- Users have a smartphone or device capable of taking a legible photo of a receipt.
- Users operate in a single home currency per account (PLN used in illustrative examples).
- Receipts are itemized (list individual purchased items), not just a single total — item-level features (categorization, position matching, item-based advice) depend on this.
- A default spending category taxonomy will be provided by the business prior to development; users may extend it with custom categories.
- The business will define initial confidence thresholds (for OCR extraction, categorization, and manual-review triggers) in collaboration with the development team during design.

## 11. Constraints

- All receipt images and extracted financial data must be encrypted at rest and scoped strictly to the owning user account.
- The agent may only offer advice and insight; it must not initiate or execute any financial transaction on the user's behalf.
- Recommendations must remain specific and evidence-based (tied to the user's actual purchase history) rather than generic financial tips, to preserve product differentiation and user trust.

## 12. Success Criteria

| Metric | Target (indicative — to be finalized with stakeholders) |
|---|---|
| Receipt parsing accuracy | High extraction accuracy on required fields (merchant, date, items, total) on legible photos |
| Manual review rate | Low proportion of receipts requiring manual review |
| Categorization accuracy | High proportion of items correctly auto-categorized without user correction |
| User goal engagement | Meaningful proportion of active users define at least one goal and receive advice |
| Retention impact | Measurable improvement in monthly active usage among users who receive goal-based advice vs. those who do not |

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Poor photo quality leads to inaccurate parsing | Incorrect budget figures erode user trust | Confidence thresholds + manual-review flagging (BR-1) |
| Miscategorized items skew statistics and advice | Misleading insights | User correction + learning from corrections (BR-3) |
| Over-frequent or generic advice reduces engagement | Users disengage from the advice feature | Advice must be specific, position/category-based, and respect user feedback (BR-6) |
| Sensitive financial data exposure | Legal/reputational risk, user trust loss | Encryption at rest, strict per-user data scoping (Section 8) |

## 14. Open Questions for Stakeholders

1. What are the target values for the success metrics in Section 12 (e.g., acceptable manual-review rate)?
2. Which markets/currencies must be supported at launch, and is multi-currency truly out of scope for phase 1?
3. Should household/shared budgets be considered for a future phase, and would that change the current single-user data model assumption?
4. What is the business's tolerance for advice based on limited data (see requirement F5) — should the agent still offer softer, lower-confidence suggestions, or withhold advice entirely?
5. What confidence threshold values should be used for OCR fields, category assignment, and manual-review triggers?
6. Should budget periods be strictly calendar months, or should custom billing cycles be supported?
