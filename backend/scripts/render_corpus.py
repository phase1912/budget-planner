#!/usr/bin/env python
"""Draw the synthetic corpus cases' photos from their case.json (F0.11.3).

A synthetic case (``"synthetic": true``) describes invented documents; this draws them as
receipt-like photos, so the committed corpus holds no one's real receipt. A case's
``layout`` says how its documents are photographed:

    "single"    one photo per document (the default)
    "together"  every document side by side on one photo, as receipts laid on a table
    "parts"     one long document in ``parts`` overlapping photos, as a long receipt is shot

The photos are written next to case.json and listed in its ``files``. Run it after
adding or changing a synthetic case, then commit both:

    uv run python scripts/render_corpus.py evaluation/corpus
"""

import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

FONTS = (
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
)
WIDTH = 420
LINE = 26
MARGIN = 24


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("No monospace font with Cyrillic found; add one to FONTS.")


def _text_lines(document: dict[str, Any]) -> list[str]:
    """A document as the lines a till or a bank app would print."""
    currency = document.get("currency", "")
    if document.get("kind", "receipt") != "receipt":
        heading = {"money_sent": "TRANSFER SENT", "money_received": "MONEY RECEIVED"}
        return [
            document.get("bank", "BANK"),
            heading.get(document.get("kind", ""), "DOCUMENT"),
            "",
            f"{document.get('total', '')} {currency}",
            document.get("date", ""),
            "",
            f"To: {document.get('merchant', '')}" if document.get("kind") == "money_sent" else "",
            f"From: {document.get('payer', '')}"
            if document.get("kind") == "money_received"
            else "",
            document.get("note", ""),
        ]
    lines = [document.get("merchant", ""), document.get("address", ""), ""]
    for line in document.get("lines", []):
        name = line["name"][:22]
        lines.append(f"{name:<22}{line['total']:>10}")
        if str(line.get("quantity", "1")) != "1":
            lines.append(f"  {line['quantity']} x {line.get('unit_price', '')}")
    lines += [
        "-" * 32,
        f"{'SUMA' if currency == 'PLN' else 'TOTAL':<20}{document.get('total', ''):>12}",
    ]
    lines += [currency, document.get("date", "")]
    return [line for line in lines if line is not None]


def _draw(lines: list[str]) -> Image.Image:
    font = _font(18)
    image = Image.new("RGB", (WIDTH, MARGIN * 2 + LINE * len(lines)), "white")
    pen = ImageDraw.Draw(image)
    for row, text in enumerate(lines):
        pen.text((MARGIN, MARGIN + row * LINE), text, fill="black", font=font)
    return image


def render(case_dir: Path) -> None:
    """Draw one synthetic case's photos and list them in its case.json."""
    path = case_dir / "case.json"
    case = json.loads(path.read_text(encoding="utf-8"))
    if not case.get("synthetic"):
        return
    documents = case["documents"]
    layout = case.get("layout", "single")
    images: list[Image.Image]
    if layout == "together":
        drawn = [_draw(_text_lines(d)) for d in documents]
        sheet = Image.new(
            "RGB",
            (
                sum(i.width for i in drawn) + 20 * (len(drawn) + 1),
                max(i.height for i in drawn) + 40,
            ),
            (205, 200, 190),
        )
        x = 20
        for image in drawn:
            sheet.paste(image, (x, 20))
            x += image.width + 20
        images = [sheet]
    elif layout == "parts":
        whole = _draw(_text_lines(documents[0]))
        parts = int(case.get("parts", 2))
        step = whole.height // parts
        overlap = LINE * 3
        images = [
            whole.crop(
                (0, max(0, i * step - overlap), whole.width, min(whole.height, (i + 1) * step))
            )
            for i in range(parts)
        ]
    else:
        images = [_draw(_text_lines(d)) for d in documents]
    names = []
    for index, image in enumerate(images, start=1):
        name = f"{index}.jpg"
        image.save(case_dir / name, "JPEG", quality=88)
        names.append(name)
    case["files"] = names
    path.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(root: Path) -> None:
    for path in sorted(root.rglob("case.json")):
        render(path.parent)
        print(f"drew {path.parent.relative_to(root)}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "evaluation/corpus"))
