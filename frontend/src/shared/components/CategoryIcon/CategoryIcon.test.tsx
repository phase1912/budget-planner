import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CategoryIcon } from "./CategoryIcon";

describe("CategoryIcon", () => {
  it("draws a built-in category's own glyph in its colour", () => {
    const { container } = render(<CategoryIcon name="Dining" />);
    const mark = container.firstElementChild as HTMLElement;

    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(mark.style.color).toBe("var(--cat-dining)");
    expect(container.querySelector("svg.lucide-utensils-crossed")).not.toBeNull();
  });

  it("gives every category the user made the same tag, in the colour for Other", () => {
    const { container } = render(<CategoryIcon name="Kids' clubs" />);

    expect((container.firstElementChild as HTMLElement).style.color).toBe("var(--cat-other)");
    expect(container.querySelector("svg.lucide-tag")).not.toBeNull();
  });
});
