// Fails the build when the website starts doing something that needs the visitor's
// consent (F17.7.2, ePrivacy art. 5(3)): loading anything from another origin, setting a
// cookie, or keeping something on the device that is not strictly needed. Today it does
// none of these, so it asks no consent; the day one arrives, it must come with its banner
// (F19.3) — and with an entry here, and in the privacy policy, saying why.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

/**
 * What the client keeps on the device, each strictly needed or chosen by the user, as the
 * privacy policy lists them. A key added in code but not here fails the build.
 */
export const DEVICE_STORAGE = {
  budget_access_token: "the signed-in session",
  budget_refresh_token: "the signed-in session",
  budget_user: "the signed-in account, so a reload does not sign out",
  "budget-planner.theme": "the palette the user chose",
  "budget-planner.dark-at-night": "whether the user wants the dark look at night",
  budget_language: "the language the user chose",
  budget_receipts_view: "the receipts list's period and order the user chose",
  budget_chart_view: "how the user chose to draw the spending chart",
  budget_install_hint_dismissed: "that the user closed the install hint",
  budget_trip_suggestions_dismissed: "trip suggestions the user dismissed",
};

/** Other origins the client may name, and why each loads nothing into a visitor's page. */
export const ALLOWED_ORIGINS = [
  "http://localhost", // local development only
  "http://127.0.0.1", // local development only
  "http://www.w3.org", // XML namespaces in inline SVG, never fetched
  "https://budget-agent.web.app", // the service's own address
];

const SET_ITEM = /(?:localStorage|sessionStorage)\.setItem\(\s*([^,]+),/g;
const CONSTANT = /(?:const|let)\s+([A-Z_][A-Z0-9_]*)\s*=\s*["'`]([^"'`]+)["'`]/g;
const ORIGIN = /\bhttps?:\/\/[a-z0-9.-]+(?::\d+)?/gi;

/** Every consent-needing thing in one file's source, as `{ line, finding }`. */
export function findProblems(source, constants = {}) {
  const problems = [];
  const lineOf = (offset) => source.slice(0, offset).split("\n").length;
  // Across lines: a formatter puts a long call's key on the line after `setItem(`.
  for (const match of source.matchAll(SET_ITEM)) {
    const raw = match[1].trim();
    const literal = /^["'`]([^"'`]+)["'`]$/.exec(raw);
    const key = literal ? literal[1] : constants[raw];
    if (key === undefined || !(key in DEVICE_STORAGE)) {
      problems.push({
        line: lineOf(match.index),
        finding: `keeps ${raw} on the device, not on the list`,
      });
    }
  }
  source.split("\n").forEach((text, index) => {
    const line = index + 1;
    if (/document\.cookie\s*=/.test(text)) problems.push({ line, finding: "sets a cookie" });
    for (const [origin] of text.matchAll(ORIGIN)) {
      if (!ALLOWED_ORIGINS.some((allowed) => origin.toLowerCase().startsWith(allowed))) {
        problems.push({ line, finding: `names ${origin}, another origin` });
      }
    }
  });
  return problems;
}

/** String constants defined anywhere in the sources, so `setItem(SOME_KEY, …)` resolves. */
export function constantsIn(sources) {
  const found = {};
  for (const source of sources) {
    for (const [, name, value] of source.matchAll(CONSTANT)) found[name] = value;
  }
  return found;
}

function clientFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return clientFiles(path);
    const shipped = /\.(tsx?|js|css|html)$/.test(path) && !/\.test\.tsx?$/.test(path);
    return shipped ? [path] : [];
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const root = new URL("..", import.meta.url).pathname;
  const files = [
    join(root, "index.html"),
    ...clientFiles(join(root, "src")),
    ...clientFiles(join(root, "public")),
  ];
  const sources = files.map((file) => readFileSync(file, "utf8"));
  const constants = constantsIn(sources);
  let failures = 0;
  files.forEach((file, i) => {
    for (const { line, finding } of findProblems(sources[i], constants)) {
      failures += 1;
      console.error(`${relative(process.cwd(), file)}:${String(line)}  ${finding}`);
    }
  });
  if (failures > 0) {
    console.error(
      `\n${String(failures)} place(s) would need the visitor's consent. Either drop it, or add` +
        " it to scripts/check-privacy.mjs with why it is strictly needed, update the privacy" +
        " policy and ADR-0020 — and if it is not strictly needed, it needs the consent banner" +
        " (F19.3) first.",
    );
    process.exit(1);
  }
  console.log("Nothing that needs consent: no cookies, no other origins, known storage only.");
}
