// M4 "Done when": confirming LDL in the Family view updates the chart, the grid and the banner within 3 s.
import puppeteer from "puppeteer-core";

const URL = process.env.WEB_URL ?? "http://localhost:3100";
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = process.env.SHOTS ?? ".";
const LIMIT_MS = 3000;

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, defaultViewport: { width: 1360, height: 1000 } });
const result = { pass: false };
try {
  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#newrep", { timeout: 20000 });

  const sep = await page.$$eval("[data-test=ldl] [data-day]", (cells) => cells.at(-1)?.getAttribute("data-day"));
  const cellSel = `[data-test=ldl] [data-day="${sep}"]`;
  const [cholesterol] = await page.$$("xpath/.//button[normalize-space()='Cholesterol']");
  await cholesterol.click();
  await page.waitForFunction(() => document.querySelector("article svg")?.textContent?.includes("waiting for your check"));

  result.before = {
    banner: await page.$eval("#newrep", (h) => h.textContent),
    grid: await page.$eval(cellSel, (c) => c.textContent),
    chart: await page.$eval("article svg text[font-weight='600']", (t) => t.textContent),
    pill: await page.$eval("[data-run-status]", (p) => p.textContent),
  };
  await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0), { timeout: 15000 });
  await page.screenshot({ path: `${OUT}/m4-before.png`, fullPage: true });

  const [confirm] = await page.$$("xpath/.//button[starts-with(normalize-space(), 'It says 104')]");
  const t0 = Date.now();
  await confirm.click();

  const at = {};
  const watch = (name, fn, arg) => page.waitForFunction(fn, { timeout: 15000, polling: 50 }, arg).then(() => (at[name] = Date.now() - t0));
  await Promise.all([
    watch("grid", (sel) => document.querySelector(sel)?.textContent?.startsWith("104"), cellSel),
    watch("chart", () => document.querySelector("article svg text[font-weight='600']")?.textContent === "104 mg/dL"),
    watch("banner", () => !document.querySelector("#newrep")),
  ]);
  result.ms = at;
  result.after = {
    grid: await page.$eval(cellSel, (c) => c.textContent),
    chart: await page.$eval("article svg text[font-weight='600']", (t) => t.textContent),
    saved: await page.evaluate(() => [...document.querySelectorAll("section strong")].map((s) => s.textContent).find((t) => t.includes("saved"))),
  };
  await page.waitForFunction(() => document.querySelector("[data-run-status]")?.getAttribute("data-run-status") === "complete", { timeout: 60000 }).catch(() => {});
  result.after.pill = await page.$eval("[data-run-status]", (p) => p.textContent);
  result.after.saved = await page.evaluate(() => [...document.querySelectorAll("section strong")].map((s) => s.textContent).find((t) => t.includes("saved")));
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/m4-after.png`, fullPage: true });
  result.pass = Object.values(at).every((ms) => ms <= LIMIT_MS);
} catch (e) {
  result.error = String(e);
} finally {
  await browser.close();
}
console.log(JSON.stringify(result, null, 2));
process.exit(result.pass ? 0 : 1);
