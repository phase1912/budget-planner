# BRD BR-4 — Monthly Budget Calculation (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Monthly budget calculation

  @D1 @D2 @D5
  Scenario: Calculate completed month's budget
    Given the user has 15 fully parsed and categorized receipts dated in June 2026
    When the user requests the June 2026 budget summary
    Then the agent should return the sum of all line-item totals for June 2026
    And label the summary as finalized

  @D4
  Scenario: Calculate in-progress month's budget
    Given the current date is July 27, 2026
    And the user has receipts dated from July 1 to July 27, 2026
    When the user requests the July 2026 budget summary
    Then the agent should return a month-to-date total
    And clearly label it as incomplete

  @D3
  Scenario: Exclude receipts requiring manual review
    Given the user has 10 valid receipts and 2 receipts flagged "requires manual review" in July 2026
    When the agent calculates the July 2026 budget
    Then the total should only include the 10 valid receipts
    And the summary should note that 2 receipts were excluded pending review

  @D6
  Scenario: Recalculate budget after receipt edit
    Given a finalized budget snapshot exists for June 2026
    When the user edits the total amount of a receipt dated in June 2026
    Then the agent should recalculate the June 2026 budget
    And update the stored snapshot

  @D7
  Scenario: Show spend against a user-defined budget limit
    Given the user has set a monthly budget limit of 3000 PLN
    And month-to-date spend is 1800 PLN
    When the user requests the current budget status
    Then the agent should display the spend as 60% of the defined limit
