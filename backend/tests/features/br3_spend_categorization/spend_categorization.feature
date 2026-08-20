# BRD BR-3 — Spend Categorization (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Categorization of receipt line items

  @C1
  Scenario: Automatically categorize a recognized item
    Given a parsed receipt contains the item "Bananas 1kg"
    When the agent categorizes the receipt
    Then the item should be assigned to the "Groceries" category
    And the categorization confidence should be recorded

  @C2 @C3
  Scenario: Fallback to Uncategorized for unrecognized item
    Given a parsed receipt contains an item with an ambiguous or unknown name
    When the agent attempts to categorize it
    And the categorization confidence is below the threshold
    Then the item should be assigned to "Uncategorized"
    And flagged for user review

  @C4 @C5
  Scenario: User corrects a category and agent learns from it
    Given the item "Protein Bar XL" was categorized as "Groceries"
    When the user reassigns it to "Health"
    Then the agent should update the category for that item
    And future receipts from the same merchant with the same item name should be categorized as "Health"

  @C6 @C7
  Scenario: User creates a custom category
    Given the user wants to track "Pet Supplies" separately
    When the user creates a new category named "Pet Supplies"
    Then the category should be added to the available taxonomy
    And it should be selectable for manual or automatic assignment on future receipts
