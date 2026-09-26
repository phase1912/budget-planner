import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Meter } from "./Meter";

function bar(ui: React.ReactElement) {
  const { container } = render(ui);
  const [fill, mark] = Array.from(container.firstElementChild?.children ?? []) as HTMLElement[];
  return { fill, mark };
}

describe("Meter", () => {
  it("fills to its value", () => {
    expect(bar(<Meter value={60} />).fill?.style.width).toBe("60%");
  });

  it("draws a value past 100 as a full bar, notched where the mark is", () => {
    const { fill, mark } = bar(<Meter value={108} tone="error" mark={92.6} />);
    expect(fill?.style.width).toBe("100%");
    expect(fill).toHaveClass("bg-error");
    expect(mark?.style.left).toBe("92.6%");
  });
});
