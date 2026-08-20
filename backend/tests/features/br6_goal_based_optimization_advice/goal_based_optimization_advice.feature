# BRD BR-6 — Goal-Based Optimization Advice (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Budget optimization advice

  @F1 @F2 @F3 @F4
  Scenario: Generate advice tied to a savings goal
    Given the user has set a goal to save 500 PLN this month
    And category statistics show Dining is the highest and fastest-growing category
    When the user requests optimization advice
    Then the agent should recommend a specific reduction in Dining spend
    And state the projected monthly savings if the recommendation is followed

  @F3 @F9
  Scenario: Generate position-based advice tied to a lifestyle goal
    Given the user has set a goal to lose weight
    And purchase history shows recurring purchases of cookies and sugary snacks
    When the user requests optimization advice
    Then the agent should translate the weight-loss goal into relevant spending items
    And recommend reducing or stopping purchases of cookies specifically
    And state the relevance of this recommendation to the user's stated goal

  @F5
  Scenario: Insufficient data for advice
    Given the user has only 3 receipts total, all from the current week
    When the user requests optimization advice
    Then the agent should inform the user that more historical data is needed
    And should not generate a specific recommendation

  @F6
  Scenario: User is already on track to meet their goal
    Given the user's goal is to stay under 3000 PLN this month
    And month-to-date spend is proportionally on pace to finish under 3000 PLN
    When the user requests optimization advice
    Then the agent should report that the user is on track
    And should not suggest unnecessary spending cuts

  @F7
  Scenario: Proactive warning when goal is at risk
    Given the user's goal is to stay under 3000 PLN this month
    And month-to-date spend is on pace to exceed 3400 PLN by month end
    When the agent evaluates progress mid-month
    Then the agent should proactively notify the user that the goal is at risk
    And provide at least one specific recommendation to course-correct

  @F8
  Scenario: Agent incorporates user feedback on past advice
    Given the agent previously recommended reducing "Entertainment" spend
    And the user marked that recommendation as "not helpful"
    When the agent generates new optimization advice
    Then the agent should deprioritize similar "Entertainment"-focused recommendations
    And consider alternative categories for suggestions
