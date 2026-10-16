import { describe, expect, it } from "vitest";

import { constantsIn, findProblems } from "./check-privacy.mjs";

describe("check-privacy (F17.7.2)", () => {
  it("lets the strictly needed storage through, by literal or by constant", () => {
    const constants = constantsIn(['const LIST_VIEW_KEY = "budget_receipts_view";']);
    const source =
      'localStorage.setItem("budget_language", "pl");\nlocalStorage.setItem(\n  LIST_VIEW_KEY,\n  x,\n);';

    expect(findProblems(source, constants)).toEqual([]);
  });

  it("flags anything else kept on the device, on the line it starts", () => {
    expect(findProblems('\nlocalStorage.setItem("visitor_id", id);')).toEqual([
      { line: 2, finding: 'keeps "visitor_id" on the device, not on the list' },
    ]);
  });

  it("flags a cookie and a script from another origin", () => {
    const problems = findProblems(
      'document.cookie = "a=1";\n<script src="https://www.googletagmanager.com/gtag.js"></script>',
    );

    expect(problems.map((p) => p.finding)).toEqual([
      "sets a cookie",
      "names https://www.googletagmanager.com, another origin",
    ]);
  });

  it("lets the service's own address and local development through", () => {
    expect(
      findProblems('const SITE = "https://budget-agent.web.app";\nfetch("http://localhost:8000")'),
    ).toEqual([]);
  });
});
