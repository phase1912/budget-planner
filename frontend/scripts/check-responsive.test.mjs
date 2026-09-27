import { describe, expect, it } from "vitest";

import { findProblems } from "./check-responsive.mjs";

describe("check-responsive", () => {
  it("flags a width a phone cannot hold", () => {
    expect(findProblems('<div className="relative w-[250px]">')).toEqual([
      { line: 1, token: "w-[250px]", reason: "a 250px width on a phone" },
    ]);
  });

  it("flags grid columns whose fixed pixels add up past a phone's room", () => {
    const [problem] = findProblems(
      '<div className="grid grid-cols-[minmax(0,1fr)_120px_92px_120px_170px_28px]">',
    );
    expect(problem?.reason).toBe("grid columns fix 530px on a phone");
  });

  it("lets a fixed size through behind a tablet or desktop variant", () => {
    expect(
      findProblems('<div className="w-full md:w-[660px] lg:grid-cols-[132px_1fr_104px]">'),
    ).toEqual([]);
  });

  it("lets small fixed sizes through, such as icons and short columns", () => {
    expect(findProblems('<span className="w-[34px] grid-cols-[minmax(0,1fr)_78px_40px]">')).toEqual(
      [],
    );
  });
});
