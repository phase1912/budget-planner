"""Single source of truth for the receipt parser's version (BRD A15).

Every stored receipt must record the parser version that produced it, so a
later change to parsing logic doesn't retroactively look like it applies to
receipts parsed under the old behaviour. Bump this when parsing logic changes
in a way that could alter extraction results.
"""

CURRENT_PARSER_VERSION = "1"
