"""Pydantic models for structured receipt extraction (BRD A9).

These schemas define the shape of the data the vision LLM must return when
parsing a receipt image.  They serve double duty:

1. **LLM output schema** — passed to ``Agent.run_structured`` so the
   provider returns JSON matching this shape.
2. **API response body** — serialised into ``UploadJob.result_data`` and
   returned to the frontend on the polling endpoint.

Money fields use ``str`` (not ``Decimal``) in the extraction schema because
JSON has no decimal type and the LLM returns string-encoded numbers.  The
service layer converts to ``Decimal`` when persisting to domain entities.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, model_validator


class ExtractedLineItem(BaseModel):
    """A single line item on a receipt (BRD A9).

    All monetary values are strings to avoid floating-point representation
    issues in the JSON round-trip from the LLM.
    """

    name: str = Field(description="Item name as printed on the receipt")
    quantity: str = Field(description="Quantity purchased, e.g. '1' or '0.5'")
    unit_price: str = Field(description="Price per unit, e.g. '3.20'")
    total_price: str = Field(description="Line total (quantity x unit price), e.g. '6.40'")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence for this line item (e.g. 1.0) (BRD A10)",
    )


class ExtractedReceipt(BaseModel):
    """Structured output from parsing one receipt image set (BRD A9).

    The LLM fills this schema from the receipt photos.  Fields that could
    not be read are set to ``None`` and flagged via the corresponding
    confidence field, triggering the manual-review path (BRD A11).
    """

    merchant_name: str | None = Field(
        default=None, description="Store or merchant name from the receipt header"
    )
    merchant_name_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 (e.g. 1.0)"
    )

    transaction_date: str | None = Field(
        default=None,
        description="Transaction date in ISO 8601 format (YYYY-MM-DD)",
    )
    transaction_date_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 (e.g. 1.0)"
    )

    transaction_time: str | None = Field(
        default=None,
        description="Transaction time in HH:MM format (24-hour)",
    )
    transaction_time_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 (e.g. 1.0)"
    )

    currency: str = Field(
        default="PLN",
        description="ISO 4217 currency code, e.g. 'PLN', 'USD', 'EUR'",
    )

    line_items: list[ExtractedLineItem] = Field(
        default_factory=list,
        description="Every line item found on the receipt",
    )

    receipt_total: str | None = Field(
        default=None,
        description="Printed total from the receipt footer, e.g. '84.50'",
    )
    receipt_total_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 (e.g. 1.0)"
    )

    items_sum_matches_total: bool | None = Field(
        default=None,
        description=(
            "True when the sum of line-item totals equals the printed receipt total. "
            "None when either side is missing."
        ),
    )

    computed_total: str | None = Field(
        default=None,
        description="The calculated sum of line-item totals. Set by backend validation.",
    )

    @model_validator(mode="after")
    def validate_arithmetic(self) -> ExtractedReceipt:
        """Validate whether the printed total matches the sum of line items (BRD A9)."""
        if not self.line_items:
            self.items_sum_matches_total = None
            return self

        try:
            computed_total_dec = Decimal("0")
            for item in self.line_items:
                if not item.total_price:
                    self.items_sum_matches_total = None
                    return self
                computed_total_dec += Decimal(item.total_price.replace(",", "."))

            self.computed_total = str(computed_total_dec)

            if not self.receipt_total:
                self.items_sum_matches_total = None
                return self

            printed_total = Decimal(self.receipt_total.replace(",", "."))
            self.items_sum_matches_total = computed_total_dec == printed_total
        except InvalidOperation:
            self.items_sum_matches_total = None

        return self
