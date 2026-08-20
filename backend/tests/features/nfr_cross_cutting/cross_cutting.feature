# BRD section 8 — Cross-Cutting Non-Functional Requirements
# (docs/requirements/ai-budget-agent-brd-v1.1.md). Scenario wording is copied
# verbatim from the BRD so the two stay comparable; only the leading @-tags
# (BRD requirement IDs, F0.6.4's traceability report) are additions not
# present in the BRD itself.
Feature: Cross-cutting non-functional requirements

  @N1
  Scenario: Receipt images and extracted data are encrypted at rest
    Given a receipt has been parsed and stored
    When the underlying storage is inspected directly, bypassing the application
    Then the receipt image and the extracted financial fields should not be readable as plain text

  @N2
  Scenario: A user cannot access another user's data
    Given user A has stored receipts and statistics
    When user B requests user A's receipts or statistics
    Then the system should deny access
    And should not reveal whether the requested records exist

  @N3
  Scenario: Deleting a receipt removes it from budget and statistics immediately
    Given a receipt contributes to the current month's budget total and category statistics
    When the user deletes that receipt
    Then the budget total and category statistics should exclude it within the same session

  @N4
  Scenario: Parsing responds within the performance target
    Given a user submits a single receipt photo
    When the agent processes it
    Then the agent should return a parsing result — success, flagged, or failure — within the defined maximum response time

  @N5
  Scenario: Automatic classification decisions are logged with confidence scores
    Given the agent assigns a category to a line item or matches two positions automatically
    When that decision is made
    Then the agent should log the decision with its confidence score

  @N6
  Scenario: A user exports their stored data
    Given a user has receipts and statistics stored
    When the user requests an export
    Then the agent should provide their receipt and statistics data in a structured format (e.g. CSV or JSON)
