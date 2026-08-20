# BRD BR-5 — Category Statistics (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Category-based spending statistics

  @E1 @E4
  Scenario: Retrieve category breakdown for a month
    Given the user has categorized receipts for July 2026
    When the user requests category statistics for July 2026
    Then the agent should return total spend, percentage share, and transaction count for each category
    And categories should be ranked from highest to lowest spend

  @E3
  Scenario: Compare spending across two months
    Given the user has categorized receipts for both June 2026 and July 2026
    When the user requests a comparison between June and July 2026
    Then the agent should return the absolute and percentage change in spend for each category

  @E5
  Scenario: Request statistics for a period with no data
    Given the user has no receipts dated in March 2025
    When the user requests category statistics for March 2025
    Then the agent should inform the user that no receipts were found for that period

  @E2
  Scenario: Request a custom date range
    Given the user has receipts spanning multiple months
    When the user requests statistics from July 10, 2026 to July 24, 2026
    Then the agent should return category totals limited to that date range
