# BRD BR-2 — Multi-Photo Receipt Continuity (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Same-position detection across two check photos

  @B1 @B2 @B3
  Scenario: Identify identical position split across two photos of the same long receipt
    Given the user photographs a long receipt in two overlapping shots because it does not fit in one frame
    And the item "Bananas 1kg" priced at 3.20 PLN, quantity 1, appears near the bottom of photo one
    And the same item "Bananas 1kg" priced at 3.20 PLN, quantity 1, also appears near the top of photo two
    When the agent compares the line items from both photos
    Then the pair should be classified as "same position"

  @B2 @B4
  Scenario: Any differing field results in a different position
    Given a position named "Milk 2% 1L" priced at 4.50 PLN appears on photo one
    And a position named "Milk 2% 1L" priced at 4.60 PLN appears on photo two
    When the agent compares the two positions
    Then the agent should classify the pair as "different position"

  @B5
  Scenario: Identify different positions across two different receipts
    Given the user uploads a photo of a grocery receipt
    And a photo of a restaurant receipt
    When the agent compares the line items between the two photos
    Then no items should be classified as "same position"

  @B9
  Scenario: Recurring purchase across different receipts is not treated as same position
    Given the user has a receipt dated July 1, 2026 containing "Milk 2% 1L" priced at 4.50 PLN
    And a separate receipt dated July 8, 2026 containing "Milk 2% 1L" priced at 4.50 PLN
    When the agent compares positions across these two distinct receipts
    Then the agent should not classify the pair as "same position"
    And the agent should treat them as two independent purchases

  @B6
  Scenario: Comparison not possible due to parsing failure
    Given one of the two uploaded photos fails to parse
    When the user requests a same-position comparison
    Then the agent should return "comparison not possible"
    And the agent should state the reason as a parsing failure

  @B7 @B8
  Scenario: User overrides an automatic match decision
    Given the agent classified two positions as "same position"
    When the user marks the pair as "different position"
    Then the agent should update the stored classification to "different position"
    And the agent should log the correction for future tuning
