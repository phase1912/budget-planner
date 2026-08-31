Feature: Viewing and paging receipts

  @A12 @A13
  Scenario: User views the first page of their receipts
    Given the user is logged in
    And the user has 25 stored receipts
    When the user requests the first page of receipts with a limit of 20
    Then the agent should return exactly 20 receipts
    And the total count of receipts should be 25
    And the receipts should be ordered by date descending

  @N2
  Scenario: User cannot view another user's receipt
    Given the user is logged in
    And another user has a stored receipt
    When the user requests the details for the other user's receipt
    Then the agent should return a "not found" error
