// Fails the build on the two class patterns that broke screens on a phone (F7.2):
// a fixed width a 375px screen cannot hold, and a grid whose fixed-pixel columns add
// up to one. Either is fine behind a tablet or desktop variant (`md:`, `lg:`, …),
// because the phone layout underneath is then something else. A fast static guard,
// not a layout test: it reads class names, it does not render anything.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

/** The widest fixed size, in px, that still leaves room on a 375px phone. */
export const PHONE_BUDGET = 200;

const WIDER_SCREENS = new Set(["sm", "md", "lg", "xl", "2xl"]);
const SIZED = /(?<![\w-])((?:[\w-]+:)*)(min-w|w|grid-cols)-\[([^\]\s]+)\]/g;

/**
 * Every phone-breaking class in one file's source, as `{ line, token, reason }`.
 * A class behind a wider-screen variant is ignored: it never applies on a phone.
 */
export function findProblems(source) {
  const problems = [];
  source.split("\n").forEach((text, index) => {
    for (const match of text.matchAll(SIZED)) {
      const [token, variants, utility, value] = match;
      const onPhone = !variants
        .split(":")
        .filter(Boolean)
        .some((variant) => WIDER_SCREENS.has(variant));
      if (!onPhone) continue;
      // Tracks are joined by "_" in arbitrary values, so only a digit or dot may not precede.
      const pixels = [...value.matchAll(/(?<![\d.])(\d+(?:\.\d+)?)px/g)]
        .map(([, n]) => Number(n))
        .reduce((sum, n) => sum + n, 0);
      if (pixels <= PHONE_BUDGET) continue;
      const reason =
        utility === "grid-cols"
          ? `grid columns fix ${String(pixels)}px on a phone`
          : `a ${String(pixels)}px width on a phone`;
      problems.push({ line: index + 1, token, reason });
    }
  });
  return problems;
}

function componentFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return componentFiles(path);
    return path.endsWith(".tsx") && !path.endsWith(".test.tsx") ? [path] : [];
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const root = new URL("../src", import.meta.url).pathname;
  let failures = 0;
  for (const file of componentFiles(root)) {
    for (const { line, token, reason } of findProblems(readFileSync(file, "utf8"))) {
      failures += 1;
      console.error(`${relative(process.cwd(), file)}:${String(line)}  ${token}  — ${reason}`);
    }
  }
  if (failures > 0) {
    console.error(
      `\n${String(failures)} class(es) would break a phone layout. Give the phone its own` +
        " layout and move the fixed size behind md: or lg: (see CLAUDE.md, TypeScript / React).",
    );
    process.exit(1);
  }
  console.log("No phone-breaking fixed widths or grids.");
}
