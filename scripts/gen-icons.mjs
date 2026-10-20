// Renders src/app/icon.svg into PNG icons for platforms that ignore SVG
// icons (iOS home screen, some Android launchers, crawlers that want PNG).
// Chrome is driven headlessly via puppeteer-core, same as capture.mjs.
// Usage: node scripts/gen-icons.mjs
import puppeteer from "puppeteer-core";
import { readFile } from "node:fs/promises";

const CHROME =
  process.env.CHROME_PATH ??
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

const svg = await readFile("src/app/icon.svg", "utf8");
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--hide-scrollbars"],
});

const targets = [
  { file: "public/apple-icon.png", size: 180 },
  { file: "public/icon-512.png", size: 512 },
];

for (const { file, size } of targets) {
  const page = await browser.newPage();
  await page.setViewport({ width: size, height: size, deviceScaleFactor: 1 });
  await page.setContent(
    `<style>html,body{margin:0;background:#11110f}svg{display:block}</style>` +
      svg.replace("<svg ", `<svg width="${size}" height="${size}" `),
  );
  await page.screenshot({ path: file });
  await page.close();
  console.log(`wrote ${file} (${size}x${size})`);
}

await browser.close();
