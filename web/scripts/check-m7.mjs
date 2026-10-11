// M7 demo run in a real browser: paused report -> confirm -> ask -> learning check -> governance log.
import puppeteer from "puppeteer-core";

const URL = process.env.WEB_URL ?? "http://localhost:3100";
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = process.env.SHOTS ?? ".";
const QUESTION = "Should we reduce her vitamin D dose?";

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, defaultViewport: { width: 1360, height: 1000 } });
const result = { pass: false, ms: {} };
const clickText = async (page, xpath) => {
  const [el] = await page.$$(`xpath/${xpath}`);
  if (!el) throw new Error(`not found: ${xpath}`);
  await el.click();
};
try {
  const page = await browser.newPage();
  const start = Date.now();
  await page.goto(URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#newrep", { timeout: 30000 });
  await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0), { timeout: 20000 });
  await page.screenshot({ path: `${OUT}/m7-family-paused.png`, fullPage: true });

  await clickText(page, ".//button[normalize-space()='Under the hood']");
  await page.waitForSelector("[data-step='Verifier'][data-state='wait']", { timeout: 15000 });
  result.before = await page.$eval("[data-gate-status]", (e) => e.textContent);
  await page.screenshot({ path: `${OUT}/m7-hood-before.png`, fullPage: true });

  await clickText(page, ".//button[normalize-space()='Family view']");
  await page.waitForSelector("#newrep");
  const confirmLabel = await page.$$eval("button", (bs) => bs.map((b) => b.textContent.trim()).find((t) => t.startsWith("It says")));
  const t0 = Date.now();
  await clickText(page, `.//button[normalize-space()='${confirmLabel}']`);
  await page.waitForFunction(() => !document.querySelector("#newrep"), { timeout: 15000 });
  result.ms.confirmToSaved = Date.now() - t0;
  result.confirmed = confirmLabel;

  await page.type("input[aria-label='Your question about Amma']", QUESTION);
  const t1 = Date.now();
  await clickText(page, ".//button[normalize-space()='Ask']");
  await page.waitForSelector("[data-ask-status='answered']", { timeout: 60000 });
  result.ms.askAnswered = Date.now() - t1;
  result.ask = await page.$eval("[data-ask-status='answered']", (e) => ({ blocked: e.getAttribute("data-ask-blocked"), text: e.textContent }));
  await page.screenshot({ path: `${OUT}/m7-family-after.png`, fullPage: true });

  await clickText(page, ".//button[normalize-space()='Under the hood']");
  await page.waitForFunction(() => /promoted/i.test(document.querySelector("[data-gate-status]")?.textContent ?? ""), { timeout: 150000 });
  result.ms.confirmToPromoted = Date.now() - t0;
  result.ms.total = Date.now() - start;
  result.gate = await page.$eval("[data-gate-status]", (e) => e.textContent);
  result.rules = await page.$$eval("[data-rule]", (rows) =>
    rows.map((r) => ({ rule: r.getAttribute("data-rule"), correct: r.querySelector("[data-correct]")?.textContent, regressions: r.querySelector("[data-regressions]")?.getAttribute("data-regressions") })),
  );
  result.log = await page.$$eval("[data-event]", (rows) => rows.map((r) => r.textContent.replace(/\s+/g, " ").trim().slice(0, 130)));
  await page.screenshot({ path: `${OUT}/m7-hood-after.png`, fullPage: true });
  const events = result.log.join("\n");
  result.pass = ["HELD", "RELEASED", "BLOCKED", "REJECTED", "PROMOTED"].every((e) => events.includes(e)) && result.ask.blocked === "true";
} catch (e) {
  result.error = String(e);
} finally {
  await browser.close();
}
console.log(JSON.stringify(result, null, 2));
process.exit(result.pass ? 0 : 1);
