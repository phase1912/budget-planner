// Fails the build when a translation falls behind English (F9.9): a key Ukrainian or
// Polish lacks, a key English no longer has, a placeholder ({{name}}) one side drops, or a
// plural form the language needs ("1 чек / 2 чеки / 5 чеків") missing. English is the
// source; a missing key would otherwise show in English without anyone noticing.

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const SOURCE = "en";
const PLURAL = /_(zero|one|two|few|many|other)$/;

/** Every leaf of a translation file as `{ "a.b.c": "text" }`. */
export function flatten(tree, prefix = "") {
  return Object.entries(tree).reduce((leaves, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "object" && value !== null
      ? { ...leaves, ...flatten(value, path) }
      : { ...leaves, [path]: value };
  }, {});
}

function placeholders(text) {
  return [...String(text).matchAll(/{{\s*(\w+)\s*}}/g)]
    .map((m) => m[1])
    .sort()
    .join(",");
}

/** What is wrong with `target`'s translation of one file, measured against `source`. */
export function compare(language, source, target) {
  const problems = [];
  const plural = (key) => key.replace(PLURAL, "");
  const needed = new Intl.PluralRules(language).resolvedOptions().pluralCategories;
  const sourceBases = new Map();
  for (const [key, text] of Object.entries(source)) {
    sourceBases.set(plural(key), { text, plural: PLURAL.test(key) });
  }
  const targetBases = new Set(Object.keys(target).map(plural));
  for (const [base, { text, plural: isPlural }] of sourceBases) {
    if (!targetBases.has(base)) {
      problems.push(`missing "${base}"`);
      continue;
    }
    const forms = isPlural ? needed.map((form) => `${base}_${form}`) : [base];
    for (const form of forms) {
      if (!(form in target)) {
        problems.push(`missing "${form}"`);
      } else if (placeholders(target[form]) !== placeholders(text)) {
        problems.push(`"${form}" has other placeholders than English`);
      }
    }
  }
  for (const base of targetBases) {
    if (!sourceBases.has(base)) problems.push(`"${base}" is not in English`);
  }
  return problems;
}

function run(root) {
  const languages = readdirSync(root).filter((name) => name !== SOURCE);
  const problems = [];
  for (const file of readdirSync(join(root, SOURCE))) {
    const source = flatten(JSON.parse(readFileSync(join(root, SOURCE, file), "utf8")));
    for (const language of languages) {
      let target = {};
      try {
        target = flatten(JSON.parse(readFileSync(join(root, language, file), "utf8")));
      } catch {
        problems.push(`${language}/${file}: file missing`);
        continue;
      }
      for (const problem of compare(language, source, target)) {
        problems.push(`${language}/${file}: ${problem}`);
      }
    }
  }
  return problems;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const problems = run(join(process.cwd(), "src/locales"));
  if (problems.length > 0) {
    console.error(problems.join("\n"));
    console.error(`\n${String(problems.length)} translation problem(s).`);
    process.exit(1);
  }
  console.log("Every translation has every key English has.");
}
