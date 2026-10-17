// Writes the public pages as prerendered HTML after the build (F17.2.2).
//
// The landing renders in English at "/", and in each language at "/en", "/uk" and "/pl";
// the Help page (F17.10), the privacy policy and the terms (F17.7.1) in English at "/help",
// "/privacy" and "/terms", the browser then showing the reader's language;
// with that language's title, description, Open Graph tags, canonical address and hreflang
// links, so search engines and link previews read it without running the app. The untouched
// build output is kept as app.html: every other route falls back to it (firebase.json), so a
// signed-in page never flashes the landing before the app starts.
//
// The stores the app's tree is rendered with read the browser's storage and window; here
// they get empty stand-ins, which is what a visitor without a session has.
import { copyFile, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";

const SITE = (process.env.SITE_URL ?? "https://budget-agent.web.app").replace(/\/$/, "");
const LANGUAGES = ["en", "uk", "pl"];
const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const ssr = new URL("../dist-ssr/entry-prerender.js", import.meta.url);

const memory = new Map();
globalThis.localStorage = {
  getItem: (key) => (memory.has(key) ? memory.get(key) : null),
  setItem: (key, value) => memory.set(key, String(value)),
  removeItem: (key) => memory.delete(key),
  clear: () => memory.clear(),
};
globalThis.window = globalThis;
globalThis.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
globalThis.addEventListener = () => {};
globalThis.removeEventListener = () => {};
globalThis.document = {
  documentElement: { lang: "en", classList: { toggle() {}, add() {}, remove() {} } },
};

const { render } = await import(pathToFileURL(fileURLToPath(ssr)).href);
const template = await readFile(`${dist}index.html`, "utf8");
await copyFile(`${dist}index.html`, `${dist}app.html`);

const escape = (text) =>
  text.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;");

async function meta(language) {
  const file = new URL(`../src/locales/${language}/landing.json`, import.meta.url);
  return JSON.parse(await readFile(file, "utf8")).meta;
}

async function helpMeta() {
  const file = new URL("../src/locales/en/help.json", import.meta.url);
  const help = JSON.parse(await readFile(file, "utf8"));
  return { title: `${help.title} — Budget Agent`, description: help.intro };
}

async function legalMeta(document) {
  const file = new URL("../src/locales/en/legal.json", import.meta.url);
  const page = JSON.parse(await readFile(file, "utf8"))[document];
  return { title: `${page.title} — Budget Agent`, description: page.intro };
}

function head(language, address, { title, description }, languageVersions = true) {
  const alternates = languageVersions
    ? LANGUAGES.map(
        (code) => `<link rel="alternate" hreflang="${code}" href="${SITE}/${code}" />`,
      ).join("\n    ") + `\n    <link rel="alternate" hreflang="x-default" href="${SITE}/" />`
    : "";
  return `<title>${escape(title)}</title>
    <meta name="description" content="${escape(description)}" />
    <link rel="canonical" href="${SITE}${address}" />
    ${alternates}
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Budget Agent" />
    <meta property="og:url" content="${SITE}${address}" />
    <meta property="og:title" content="${escape(title)}" />
    <meta property="og:description" content="${escape(description)}" />
    <meta property="og:locale" content="${{ en: "en_GB", uk: "uk_UA", pl: "pl_PL" }[language]}" />
    <meta property="og:image" content="${SITE}/icon-512.png" />
    <meta name="twitter:card" content="summary" />`;
}

async function page(path, language, out, pageMeta = null) {
  const body = await render(path, language);
  const html = template
    .replace(/<html lang="[^"]*">/, `<html lang="${language}">`)
    .replace(
      /<title>[\s\S]*?<\/title>\s*<meta\s+name="description"[\s\S]*?\/>/,
      pageMeta ? head(language, path, pageMeta, false) : head(language, path, await meta(language)),
    )
    .replace('<div id="root"></div>', `<div id="root">${body}</div>`);
  if (!html.includes(body)) throw new Error(`Could not place the rendered ${path} into the page`);
  await writeFile(`${dist}${out}`, html);
  console.log(`prerendered ${path} (${language}) -> dist/${out}`);
}

await page("/", "en", "index.html");
for (const language of LANGUAGES) await page(`/${language}`, language, `${language}.html`);
await page("/help", "en", "help.html", await helpMeta());
for (const document of ["privacy", "terms"]) {
  await page(`/${document}`, "en", `${document}.html`, await legalMeta(document));
}
