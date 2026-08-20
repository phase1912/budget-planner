# BRD BR-1 — Receipt Digitization (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Receipt photo parsing and storage

  @A9 @A12 @A13 @A15
  Scenario: Successfully parse and store a valid receipt photo
    Given the user is logged in
    And the user has a clear JPEG photo of a grocery store receipt
    When the user submits the photo to the agent
    Then the agent should extract merchant name, date, line items, and total amount
    And the agent should store the parsed receipt in the database
    And the agent should link the original photo to the stored record

  @A1 @A2
  Scenario: Reject unsupported file format
    Given the user is logged in
    When the user submits a ".docx" file instead of a photo
    Then the agent should reject the upload
    And the agent should return an error stating supported formats are JPEG, PNG, HEIC, and PDF-scan

  @A3 @A4
  Scenario: Upload a single receipt within limits
    Given the user selects "single receipt" upload mode
    When the user uploads 4 photos totaling 20 MB for that receipt
    Then the agent should accept all 4 photos
    And process them as one receipt

  @A4 @A7
  Scenario: Reject exceeding photo count in single receipt mode
    Given the user selects "single receipt" upload mode
    When the user attempts to upload 11 photos for that receipt
    Then the agent should reject the 11th photo
    And inform the user of the 10-photo limit

  @A4 @A8
  Scenario: Reject exceeding size limit in single receipt mode
    Given the user selects "single receipt" upload mode
    When the user attempts to upload photos totaling 55 MB for that receipt
    Then the agent should reject the upload
    And inform the user of the 50 MB limit

  @A3 @A5 @A6
  Scenario: Upload multiple receipts across separate lines
    Given the user selects "multiple receipts" upload mode
    When the user adds two upload lines, one for a grocery receipt and one for a restaurant receipt
    And uploads 3 photos totaling 15 MB to the first line
    And uploads 2 photos totaling 10 MB to the second line
    Then the agent should accept both lines
    And process each line as a separate receipt

  @A5 @A7
  Scenario: Reject exceeding limits on one line in multiple receipts mode
    Given the user selects "multiple receipts" upload mode
    And has added two upload lines
    When the user attempts to upload 12 photos to the first line
    Then the agent should reject the additional photos on that line
    And inform the user of the 10-photo limit
    And the second line should remain unaffected

  @A10
  Scenario: Flag low-confidence extraction
    Given the user submits a blurry receipt photo
    When the agent parses the photo
    And the confidence score for the total amount is below the acceptable threshold
    Then the agent should mark the total amount field as "low confidence"
    And the agent should prompt the user to confirm or correct the value

  @A11
  Scenario: Handle missing critical fields
    Given the user submits a photo where the total amount is not visible
    When the agent attempts to parse the photo
    Then the agent should mark the receipt as "requires manual review"
    And the receipt should be excluded from automatic budget calculations

  @A14
  Scenario: Detect potential duplicate upload
    Given a receipt from "Fresh Market" dated 2026-07-20 for 84.50 PLN already exists in the database
    When the user uploads another photo with the same merchant, date, and total
    Then the agent should notify the user of a potential duplicate
    And the agent should ask the user to confirm whether to store it as a new receipt
