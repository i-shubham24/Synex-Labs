// Checks that every project link on the site still answers: live sites,
// App Store and Google Play pages. Run weekly by .github/workflows/links.yml.
// Usage: node scripts/check-links.mjs
// Exits 1 when a link is gone (404, 410, 5xx, DNS or a dead Vercel
// deployment). Blocks such as 403 or 429 are reported but do not fail,
// since stores and some hosts refuse CI machines.
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../src/data/projects.ts", import.meta.url), "utf8");
const links = [
  ...new Set(
    [...source.matchAll(/^\s*(?:url|appStore|playStore):\s*"([^"]+)"/gm)].map((m) => m[1]),
  ),
];

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";

// Follows redirects by hand and keeps cookies between hops, like a browser.
// Some hosts (Streamlit) bounce through a sign-in redirect that sets a cookie
// and loops forever without it.
async function get(url) {
  // host -> (cookie name -> value)
  const jar = new Map();
  for (let hop = 0; hop < 10; hop++) {
    const host = new URL(url).host;
    const cookies = jar.get(host) ?? new Map();
    jar.set(host, cookies);
    const res = await fetch(url, {
      redirect: "manual",
      headers: {
        "User-Agent": UA,
        Accept: "text/html,*/*",
        ...(cookies.size && {
          Cookie: [...cookies].map(([k, v]) => `${k}=${v}`).join("; "),
        }),
      },
      signal: AbortSignal.timeout(30000),
    });
    for (const line of res.headers.getSetCookie()) {
      const [pair] = line.split(";");
      const at = pair.indexOf("=");
      const name = pair.slice(0, at).trim();
      if (/max-age=0\b/i.test(line)) cookies.delete(name);
      else cookies.set(name, pair.slice(at + 1).trim());
    }
    const next = res.headers.get("location");
    if (res.status < 300 || res.status >= 400 || !next) return res;
    await res.body?.cancel();
    url = new URL(next, url).href;
  }
  throw new Error("too many redirects");
}

async function check(url) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const res = await get(url);
      const vercel = res.headers.get("x-vercel-error");
      await res.body?.cancel();
      if (res.ok) return { url, state: "ok", detail: String(res.status) };
      if ([401, 403, 429].includes(res.status))
        return { url, state: "blocked", detail: String(res.status) };
      if (attempt === 2 || res.status < 500)
        return { url, state: "dead", detail: `${res.status}${vercel ? ` ${vercel}` : ""}` };
    } catch (e) {
      if (attempt === 2)
        return { url, state: "dead", detail: e.cause?.code ?? e.name ?? String(e) };
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
}

const results = [];
// A few at a time, so no host sees a burst.
for (let i = 0; i < links.length; i += 4) {
  results.push(...(await Promise.all(links.slice(i, i + 4).map(check))));
}

for (const r of results) console.log(`${r.state.padEnd(7)} ${r.detail.padEnd(28)} ${r.url}`);
const dead = results.filter((r) => r.state === "dead");
console.log(`\n${links.length} links, ${dead.length} dead.`);
if (dead.length) process.exit(1);
