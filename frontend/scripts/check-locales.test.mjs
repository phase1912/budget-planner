import { describe, expect, it } from "vitest";

import { compare, flatten } from "./check-locales.mjs";

describe("check-locales", () => {
  it("reads nested keys as dotted paths", () => {
    expect(flatten({ a: { b: "x", c: { d: "y" } } })).toEqual({ "a.b": "x", "a.c.d": "y" });
  });

  it("passes a complete translation", () => {
    expect(compare("pl", { "a.title": "Hi {{name}}" }, { "a.title": "Cześć {{name}}" })).toEqual(
      [],
    );
  });

  it("flags a key the translation lacks and one English no longer has", () => {
    expect(compare("uk", { kept: "x", added: "y" }, { kept: "х", removed: "z" })).toEqual([
      'missing "added"',
      '"removed" is not in English',
    ]);
  });

  it("flags a placeholder the translation dropped", () => {
    expect(compare("uk", { join: "Join {{name}}" }, { join: "Приєднатися" })).toEqual([
      '"join" has other placeholders than English',
    ]);
  });

  it("asks for every plural form the language has, not English's two", () => {
    const english = { receipts_one: "{{count}} receipt", receipts_other: "{{count}} receipts" };
    const polish = { receipts_one: "{{count}} paragon", receipts_other: "{{count}} paragonu" };

    expect(compare("pl", english, polish)).toEqual([
      'missing "receipts_few"',
      'missing "receipts_many"',
    ]);
  });
});
