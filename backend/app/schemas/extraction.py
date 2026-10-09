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

import re
import uuid
from decimal import Decimal, InvalidOperation

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.config import get_settings
from app.domain.categories import is_low_confidence
from app.domain.position_matching import MatchResult
from app.domain.receipt_totals import lines_match_total

_TRAILING_LETTERS = re.compile(r"(?<=\d)\s*[A-Za-z]+\.?$")


def normalise_amount(value: str) -> str:
    """Drop the unit or tax-class letter receipts print next to a number.

    Polish receipts tag each line with its VAT class, so the LLM faithfully
    reports "7,49A" or "10szt" when asked to extract the printed value.  Those
    strings raise ``InvalidOperation`` the moment anything converts them to
    ``Decimal``, and the conversions downstream swallow that and substitute
    zero, so an entire receipt is stored priced at nothing.

    A discount's minus sign is kept and put in front, however it was printed:
    "- 4,99", or "10,04-" as some tills print it, both become a negative amount.

    Returns "" when nothing numeric is left, which callers already treat as a
    missing value rather than as zero.
    """
    stripped = "".join(_TRAILING_LETTERS.sub("", value).split())
    if stripped.endswith("-") and not stripped.startswith("-"):
        stripped = "-" + stripped[:-1]
    return stripped if any(char.isdigit() for char in stripped) else ""


class PositionMatch(BaseModel):
    """Result of comparing two line items (BRD B2-B4)."""

    item_a_index: int = Field(description="Index of the first item in the line_items array")
    item_b_index: int = Field(description="Index of the second item in the line_items array")
    result: MatchResult = Field(
        description="Comparison result ('same', 'different', or 'not_possible')"
    )
    reason: str | None = Field(default=None, description="Reason if comparison not possible")
    user_overridden: bool = Field(
        default=False, description="True if the user manually changed this result"
    )


class ExtractedLineItem(BaseModel):
    """A single line item on a receipt (BRD A9).

    All monetary values are strings to avoid floating-point representation
    issues in the JSON round-trip from the LLM.  Models routinely answer with
    a bare number anyway (``"quantity": 1``), so numbers are coerced rather
    than rejected — losing a whole receipt over JSON's number/string
    distinction helps nobody.
    """

    model_config = ConfigDict(coerce_numbers_to_str=True)

    name: str = Field(description="Item name as printed on the receipt")
    quantity: str = Field(description="Quantity purchased, e.g. '1' or '0.5'")
    unit_price: str = Field(description="Price per unit, e.g. '3.20'")
    total_price: str = Field(description="Line total (quantity x unit price), e.g. '6.40'")
    confidence: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Extraction confidence for this line item (0-100, e.g. 100) (BRD A10)",
    )
    file_id: str | None = Field(
        default=None,
        description=(
            "The ID of the file (image) this line item was extracted from. "
            "Populated by the backend, not the LLM."
        ),
    )
    category_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "The assigned category's UUID. Populated by the backend from the "
            "categoriser's answer, not by the extracting LLM."
        ),
    )
    category_name: str | None = Field(
        default=None,
        description="The assigned category's name. Populated by the backend, not the LLM.",
    )
    category_confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Categorisation confidence (0-100), or None when nothing categorised "
            "this item — which is not the same as categorising it badly (BRD C3)."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category_is_low_confidence(self) -> bool:
        """Whether the category needs a human look before it is trusted (BRD C3).

        Decided here, against `Settings.categorization_confidence_threshold`,
        because ADR-0005 forbids the number being restated at a call site — and
        a browser is the last place a threshold should live.
        """
        return is_low_confidence(
            self.category_confidence,
            get_settings().categorization_confidence_threshold,
        )

    @field_validator("quantity", "unit_price", "total_price", mode="after")
    @classmethod
    def _strip_printed_suffix(cls, value: str) -> str:
        return normalise_amount(value)


class ExtractedReceipt(BaseModel):
    """Structured output from parsing one receipt image set (BRD A9).

    The LLM fills this schema from the receipt photos.  Fields that could
    not be read are set to ``None`` and flagged via the corresponding
    confidence field, triggering the manual-review path (BRD A11).
    """

    model_config = ConfigDict(coerce_numbers_to_str=True)

    merchant_name: str | None = Field(
        default=None, description="Store or merchant name from the receipt header"
    )
    merchant_name_confidence: int = Field(
        default=100, ge=0, le=100, description="Confidence score between 0 and 100 (e.g. 100)"
    )

    fiscal_register_id: str | None = Field(
        default=None,
        description=(
            "The cash register's unique number as printed: in Poland the ECA/EAO… number "
            "beside the fiscal logo, in Ukraine the register's fiscal number (FN). Null if "
            "not printed."
        ),
    )
    fiscal_receipt_number: str | None = Field(
        default=None,
        description=(
            "This receipt's number on that register: in Poland the printout number (nr:…) "
            "of the fiscal receipt, in Ukraine the receipt's fiscal number (ФН чека). Null "
            "if not printed."
        ),
    )

    transaction_date: str | None = Field(
        default=None,
        description="Transaction date in ISO 8601 format (YYYY-MM-DD)",
    )
    transaction_date_confidence: int = Field(
        default=100, ge=0, le=100, description="Confidence score between 0 and 100 (e.g. 100)"
    )

    transaction_time: str | None = Field(
        default=None,
        description="Transaction time in HH:MM format (24-hour)",
    )
    transaction_time_confidence: int = Field(
        default=100, ge=0, le=100, description="Confidence score between 0 and 100 (e.g. 100)"
    )

    currency: str = Field(
        default="PLN",
        description="ISO 4217 currency code, e.g. 'PLN', 'USD', 'EUR'",
    )

    line_items: list[ExtractedLineItem] = Field(
        default_factory=list,
        description="Every line item found on the receipt",
    )

    position_matches: list[PositionMatch] = Field(
        default_factory=list,
        description="Results of comparing overlapping line items across photos (BRD B2-B4).",
    )

    receipt_total: str | None = Field(
        default=None,
        description="Printed total from the receipt footer, e.g. '84.50'",
    )
    receipt_total_confidence: int = Field(
        default=100, ge=0, le=100, description="Confidence score between 0 and 100 (e.g. 100)"
    )

    is_receipt_confidence: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Confidence score (0-100) indicating if the image is actually a receipt.",
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

    transaction_date_assumed: bool = Field(
        default=False,
        description=(
            "Set by the backend, never by the reader: no date could be read, so the "
            "upload day was used (app.domain.receipt_dates)."
        ),
    )

    total_reconciled_by: str | None = Field(
        default=None,
        description=(
            "Set by the backend, never by the reader: how the lines were made to agree "
            "with the total, or 'unresolved' (app.domain.receipt_reconciliation)."
        ),
    )

    requires_manual_review: bool | None = Field(
        default=False,
        description="True if critical fields missing, requiring manual review (BRD A11).",
    )

    @field_validator("receipt_total", mode="after")
    @classmethod
    def _strip_printed_suffix(cls, value: str | None) -> str | None:
        return normalise_amount(value) or None if value else value

    @model_validator(mode="after")
    def validate_arithmetic(self) -> ExtractedReceipt:
        """Validate whether the printed total matches the sum of line items (BRD A9).

        Discount lines count with their minus sign, and a grosz of rounding is
        forgiven (`lines_match_total`).
        """
        self.requires_manual_review = not self.receipt_total or not self.transaction_date

        if not self.line_items:
            self.items_sum_matches_total = None
            return self

        try:
            computed_total_dec = Decimal("0")

            duplicate_indices = {
                match.item_b_index
                for match in self.position_matches
                if match.result == MatchResult.SAME
            }

            for i, item in enumerate(self.line_items):
                if i in duplicate_indices:
                    continue
                if not item.total_price:
                    self.items_sum_matches_total = None
                    return self
                computed_total_dec += Decimal(item.total_price.replace(",", "."))

            self.computed_total = str(computed_total_dec)

            if not self.receipt_total:
                self.items_sum_matches_total = None
                return self

            printed_total = Decimal(self.receipt_total.replace(",", "."))
            self.items_sum_matches_total = lines_match_total(computed_total_dec, printed_total)
        except InvalidOperation:
            self.items_sum_matches_total = None

        return self
