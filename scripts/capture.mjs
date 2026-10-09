// Captures fresh screenshots of every live project into public/work/<slug>/.
// Usage: npm run shots            (all projects)
//        npm run shots -- infini  (only the given slugs)
import puppeteer from "puppeteer-core";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const CHROME =
  process.env.CHROME_PATH ??
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const OUT = path.resolve("public/work");

// tap: click the middle of the screen first (sites that open with a cover).
const sites = [
  { slug: "aurex-india", url: "https://www.aurexindia.com/" },
  { slug: "zurich-estate", url: "https://optimal-immobilien.ch/" },
  { slug: "vento-tea", url: "https://vento-tea.vercel.app" },
  { slug: "ai-fb-scraper", url: "https://fb-scraper-bot.streamlit.app/", wait: 25000 },
  { slug: "infini", url: "https://infini-three.vercel.app" },
  // Left on its cover: the pages inside carry a private family's names.
  { slug: "invitation-cards", url: "https://invitation-card-groom.vercel.app" },
  { slug: "dolancer", url: "https://dolancer.vercel.app" },
  { slug: "almuna", url: "https://almuna-books.vercel.app" },
  { slug: "aurex-truck-parts", url: "https://aurex-trucks-parts.vercel.app" },
  { slug: "optimal-cleaning", url: "https://optimal-cleaning-eta.vercel.app" },
  { slug: "eve-pizzeria", url: "https://eve-pizzeria.vercel.app" },
  { slug: "humble-solutions", url: "http://portfolio.humblesolutions.in/" },
  { slug: "fieldofsoma", url: "https://fieldofsoma.vercel.app" },
];

const DESKTOP = { width: 1440, height: 900, deviceScaleFactor: 1.5 };
const MOBILE = {
  width: 390,
  height: 844,
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
};
const MOBILE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const STOPS = [0.3, 0.58, 0.86];
const SHOT = { type: "webp", quality: 82 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const hash = (buf) => createHash("sha1").update(buf).digest("hex");

// Closes promo popups and declines cookie banners so they stay out of the shot.
// Everything runs through evaluate so pages captured in parallel never wait on focus.
async function dismissOverlays(page) {
  await page
    .evaluate(() => {
      document.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
      );
      const visible = (el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return (
          r.width > 0 &&
          r.height > 0 &&
          s.visibility !== "hidden" &&
          s.display !== "none"
        );
      };
      const inOverlay = (el) => {
        for (let n = el; n && n !== document.body; n = n.parentElement) {
          if (getComputedStyle(n).position === "fixed") return true;
        }
        return false;
      };
      const closers = [...document.querySelectorAll("button,[role='button'],a")]
        .filter(visible)
        .filter(inOverlay)
        .filter((el) => {
          const label = `${el.getAttribute("aria-label") ?? ""} ${el.title ?? ""}`;
          const text = (el.innerText ?? "").trim();
          if (/close|dismiss|schliessen|schließen/i.test(label)) return true;
          if (
            /^(×|✕|x|close|no thanks.*|decline.*|reject.*|ablehnen|nur notwendige.*)$/i.test(
              text,
            )
          )
            return true;
          return !text && !!el.querySelector("svg[class*='lucide-x']");
        });
      closers.slice(0, 3).forEach((el) => el.click());
    })
    .catch(() => {});
  await sleep(900);
}

async function prepare(page, site, viewport) {
  try {
    await page.goto(site.url, { waitUntil: "networkidle2", timeout: 60000 });
  } catch (e) {
    console.log(`  load warning for ${site.url}: ${e.message}`);
  }
  await sleep(site.wait ?? 4500);
  if (site.tap) {
    await page.evaluate(
      (x, y) => document.elementFromPoint(x, y)?.click(),
      viewport.width / 2,
      viewport.height / 2,
    );
    await sleep(4500);
  }
  await dismissOverlays(page);
  await sleep(1200);
  await dismissOverlays(page);
}

// Scrolls in small steps so scroll animations fire the way they do for a visitor.
async function scrollBy(page, distance) {
  await page.evaluate(async (total) => {
    let target = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
    while (target && target !== document.documentElement) {
      const overflow = getComputedStyle(target).overflowY;
      if (
        /(auto|scroll)/.test(overflow) &&
        target.scrollHeight > target.clientHeight + 40
      )
        break;
      target = target.parentElement;
    }
    if (!target || target === document.documentElement)
      target = document.scrollingElement;
    let travelled = 0;
    while (travelled < total) {
      const step = Math.min(120, total - travelled);
      target.scrollBy(0, step);
      travelled += step;
      await new Promise((r) => setTimeout(r, 24));
    }
  }, distance);
  await sleep(1700);
}

async function shoot(browser, site) {
  const dir = path.join(OUT, site.slug);
  await mkdir(dir, { recursive: true });

  const page = await browser.newPage();
  await page.setViewport(DESKTOP);
  await prepare(page, site, DESKTOP);

  const meta = await page.evaluate(() => ({
    title: document.title,
    description:
      document.querySelector('meta[name="description"]')?.content ?? "",
    text: document.body.innerText.replace(/\n{2,}/g, "\n").slice(0, 2500),
    height: document.documentElement.scrollHeight,
  }));

  const seen = new Set();
  let frames = 0;
  const save = async () => {
    const buf = await page.screenshot(SHOT);
    const id = hash(buf);
    if (seen.has(id)) return;
    seen.add(id);
    frames += 1;
    await writeFile(path.join(dir, `desktop-${frames}.webp`), buf);
  };
  await save();

  // Pages that scroll inside a wrapper report a viewport-tall document,
  // so fall back to fixed wheel steps and let the hash drop duplicates.
  const scrollable = Math.max(0, meta.height - DESKTOP.height);
  const targets =
    scrollable > 500
      ? STOPS.map((stop) => Math.round(scrollable * stop))
      : [900, 1800, 2700];
  let at = 0;
  for (const target of targets) {
    await scrollBy(page, target - at);
    at = target;
    await dismissOverlays(page);
    await save();
  }
  await page.close();

  const mobile = await browser.newPage();
  await mobile.setUserAgent(MOBILE_UA);
  await mobile.setViewport(MOBILE);
  await prepare(mobile, site, MOBILE);
  await mobile.screenshot({ path: path.join(dir, "mobile.webp"), ...SHOT });
  await mobile.close();

  await writeFile(
    path.join(dir, "meta.json"),
    JSON.stringify({ ...meta, url: site.url, frames }, null, 2),
  );
  console.log(`done ${site.slug} (${frames} desktop frames, page ${meta.height}px)`);
}

const only = process.argv.slice(2);
const queue = sites.filter((s) => only.length === 0 || only.includes(s.slug));

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  defaultViewport: DESKTOP,
  protocolTimeout: 180000,
  args: ["--hide-scrollbars", "--force-prefers-reduced-motion=0"],
});

const workers = Array.from({ length: 3 }, async () => {
  while (queue.length > 0) {
    const site = queue.shift();
    try {
      await shoot(browser, site);
    } catch (e) {
      console.log(`FAILED ${site.slug}: ${e.message}`);
    }
  }
});
await Promise.all(workers);
await browser.close();

// The site reads this to know how many frames each project has.
const manifest = {};
for (const site of sites) {
  try {
    const meta = JSON.parse(
      await readFile(path.join(OUT, site.slug, "meta.json"), "utf8"),
    );
    manifest[site.slug] = meta.frames;
  } catch {
    manifest[site.slug] = 0;
  }
}
await writeFile(
  path.resolve("src/data/shots.json"),
  JSON.stringify(manifest, null, 2) + "\n",
);
