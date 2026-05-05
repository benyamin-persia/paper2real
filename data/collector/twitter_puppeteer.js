/**
 * Fast X/Twitter crawler using Puppeteer.
 *
 * Install:
 *   npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth
 *
 * Examples:
 *   node data/collector/twitter_puppeteer.js
 *   node data/collector/twitter_puppeteer.js --workers 4 --max-tweets 4
 *   node data/collector/twitter_puppeteer.js --account saylor --max-tweets 4
 *   node data/collector/twitter_puppeteer.js --tier tier1 --workers 3
 *
 * Outputs:
 *   data/raw/twitter_tweets_puppeteer.csv
 *   data/raw/twitter_timing_puppeteer.csv
 *   data/raw/twitter_puppeteer.json
 */

const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const path = require("path");

puppeteer.use(StealthPlugin());

const TIERS_FILE = path.join(__dirname, "../raw/account_tiers.json");
const JSON_OUTPUT = path.join(__dirname, "../raw/twitter_puppeteer.json");
const TWEETS_CSV = path.join(__dirname, "../raw/twitter_tweets_puppeteer.csv");
const TIMING_CSV = path.join(__dirname, "../raw/twitter_timing_puppeteer.csv");

const DEFAULT_WORKERS = 4;
const DEFAULT_MAX_TWEETS = 4;
const DEFAULT_MAX_SCROLLS = 5;

function utcNow() {
  return new Date().toISOString();
}

function parseArgs() {
  const args = {
    account: null,
    tier: null,
    workers: DEFAULT_WORKERS,
    maxTweets: DEFAULT_MAX_TWEETS,
    maxScrolls: DEFAULT_MAX_SCROLLS,
    timeoutMs: 30000,
    noRetryMissing: false,
    skipPinned: false,
    headed: false,
  };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (key === "--account") args.account = argv[++i].replace(/^@/, "");
    else if (key === "--tier") args.tier = argv[++i];
    else if (key === "--workers" || key === "--concurrency") args.workers = parseInt(argv[++i], 10);
    else if (key === "--max-tweets") args.maxTweets = parseInt(argv[++i], 10);
    else if (key === "--max-scrolls") args.maxScrolls = parseInt(argv[++i], 10);
    else if (key === "--timeout-ms") args.timeoutMs = parseInt(argv[++i], 10);
    else if (key === "--no-retry-missing") args.noRetryMissing = true;
    else if (key === "--skip-pinned") args.skipPinned = true;
    else if (key === "--headed") args.headed = true;
  }
  return args;
}

function loadAccounts(args) {
  const data = JSON.parse(fs.readFileSync(TIERS_FILE, "utf8"));
  if (args.account) return [args.account];
  if (args.tier === "tier1") return data.tier1_permanent || [];
  if (args.tier === "tier2") return data.tier2_roles || [];
  if (args.tier === "tier3") return data.tier3_dynamic || [];
  return [...new Set([
    ...(data.tier1_permanent || []),
    ...(data.tier2_roles || []),
    ...(data.tier3_dynamic || []),
  ])];
}

function csvEscape(value) {
  const s = value === null || value === undefined ? "" : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

function writeCsv(file, rows, fields) {
  const lines = [fields.join(",")];
  for (const row of rows) {
    lines.push(fields.map((field) => csvEscape(row[field])).join(","));
  }
  fs.writeFileSync(file, "\uFEFF" + lines.join("\n"), "utf8");
}

const EXTRACT_JS = ({ maxTweets, includePinned }) => {
  const parseCompact = (value) => {
    if (!value) return 0;
    const raw = String(value).replace(/,/g, "").trim();
    const match = raw.match(/([0-9]+(?:\.[0-9]+)?)([KMB])?/i);
    if (!match) return 0;
    const n = parseFloat(match[1]);
    const suffix = (match[2] || "").toUpperCase();
    const mult = suffix === "K" ? 1e3 : suffix === "M" ? 1e6 : suffix === "B" ? 1e9 : 1;
    return Math.round(n * mult);
  };

  const firstNumber = (text) => parseCompact(text || "");

  const metricsFromLabel = (article) => {
    const metrics = { replies: 0, reposts: 0, likes: 0, views: 0, bookmarks: 0, quotes: 0 };
    const labels = [
      ...Array.from(article.querySelectorAll('[role="group"][aria-label]')).map((x) => x.getAttribute("aria-label") || ""),
      ...Array.from(article.querySelectorAll("[aria-label]")).map((x) => x.getAttribute("aria-label") || ""),
    ].join(" | ");
    const patterns = [
      ["replies", /([0-9.,]+\s*[KMB]?)\s+(?:Reply|Replies)/i],
      ["reposts", /([0-9.,]+\s*[KMB]?)\s+(?:repost|reposts|retweet|retweets)/i],
      ["likes", /([0-9.,]+\s*[KMB]?)\s+(?:Like|Likes)/i],
      ["views", /([0-9.,]+\s*[KMB]?)\s+(?:view|views)/i],
      ["bookmarks", /([0-9.,]+\s*[KMB]?)\s+(?:bookmark|bookmarks)/i],
      ["quotes", /([0-9.,]+\s*[KMB]?)\s+(?:quote|quotes)/i],
    ];
    for (const [key, re] of patterns) {
      const m = labels.match(re);
      if (m) metrics[key] = parseCompact(m[1]);
    }
    return metrics;
  };

  const metricsFromButtons = (article, metrics) => {
    const reply = article.querySelector('[data-testid="reply"]')?.getAttribute("aria-label");
    const repost = article.querySelector('[data-testid="retweet"]')?.getAttribute("aria-label");
    const like = article.querySelector('[data-testid="like"], [data-testid="unlike"]')?.getAttribute("aria-label");
    const bookmark = article.querySelector('[data-testid="bookmark"]')?.getAttribute("aria-label");
    const views = article.querySelector('a[href$="/analytics"]')?.getAttribute("aria-label")
      || article.querySelector('a[href*="/analytics"]')?.innerText;
    if (reply && !metrics.replies) metrics.replies = firstNumber(reply);
    if (repost && !metrics.reposts) metrics.reposts = firstNumber(repost);
    if (like && !metrics.likes) metrics.likes = firstNumber(like);
    if (bookmark && !metrics.bookmarks) metrics.bookmarks = firstNumber(bookmark);
    if (views && !metrics.views) metrics.views = firstNumber(views);
    return metrics;
  };

  const out = [];
  const seen = new Set();
  for (const article of document.querySelectorAll('article[data-testid="tweet"]')) {
    const full = article.innerText || "";
    const isPinned = /\bPinned\b/i.test(full.split("\n").slice(0, 3).join(" "));
    if (isPinned && !includePinned) continue;

    const text = article.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || "";
    const timestamp = article.querySelector("time")?.getAttribute("datetime") || "";
    const url = article.querySelector('a[href*="/status/"]')?.href || "";
    const tweetId = (url.match(/status\/(\d+)/) || [])[1] || "";
    if (!tweetId || seen.has(tweetId)) continue;
    seen.add(tweetId);

    let metrics = metricsFromLabel(article);
    metrics = metricsFromButtons(article, metrics);
    out.push({
      tweet_id: tweetId,
      timestamp,
      text,
      url,
      is_pinned: isPinned ? 1 : 0,
      comments: metrics.replies || 0,
      replies: metrics.replies || 0,
      retweets: metrics.reposts || 0,
      reposts: metrics.reposts || 0,
      quotes: metrics.quotes || 0,
      likes: metrics.likes || 0,
      views: metrics.views || 0,
      bookmarks: metrics.bookmarks || 0,
    });
  }
  return out
    .sort((a, b) => Date.parse(b.timestamp || 0) - Date.parse(a.timestamp || 0))
    .slice(0, maxTweets);
};

async function extractUntilReady(page, args) {
  try {
    await page.waitForSelector('article[data-testid="tweet"]', { timeout: 12000 });
  } catch {
    return [];
  }
  let tweets = [];
  for (let i = 0; i <= args.maxScrolls; i++) {
    tweets = await page.evaluate(EXTRACT_JS, {
      maxTweets: args.maxTweets,
      includePinned: !args.skipPinned,
    });
    if (tweets.length >= args.maxTweets) return tweets;
    await page.mouse.wheel({ deltaY: 900 });
    await new Promise((resolve) => setTimeout(resolve, 900));
  }
  return tweets;
}

async function scrapeAccount(browser, handle, args) {
  const t0 = Date.now();
  const page = await browser.newPage();
  try {
    await page.setRequestInterception(true);
    page.on("request", (req) => {
      const type = req.resourceType();
      if (["image", "font", "media"].includes(type)) req.abort();
      else req.continue();
    });

    await page.setViewport({ width: 1280, height: 900 });
    await page.goto(`https://x.com/${handle}`, {
      waitUntil: "domcontentloaded",
      timeout: args.timeoutMs,
    });
    const tweets = await extractUntilReady(page, args);
    const elapsed = Number(((Date.now() - t0) / 1000).toFixed(2));
    console.log(`  @${handle.padEnd(20)} ${String(elapsed).padStart(6)}s  (${tweets.length} tweets)`);
    return { handle, tweets, elapsed_s: elapsed, error: "" };
  } catch (err) {
    const elapsed = Number(((Date.now() - t0) / 1000).toFixed(2));
    console.log(`  @${handle.padEnd(20)} ${String(elapsed).padStart(6)}s  ERROR: ${err.message}`);
    return { handle, tweets: [], elapsed_s: elapsed, error: err.message };
  } finally {
    await page.close();
  }
}

function flattenRows(results, scrapedAt) {
  const rows = [];
  for (const account of results) {
    account.tweets.forEach((tweet, idx) => {
      rows.push({
        scraped_at: scrapedAt,
        handle: account.handle,
        rank: idx + 1,
        tweet_id: tweet.tweet_id || "",
        timestamp: tweet.timestamp || "",
        text: tweet.text || "",
        url: tweet.url || "",
        is_pinned: tweet.is_pinned || 0,
        comments: tweet.comments || 0,
        replies: tweet.replies || 0,
        retweets: tweet.retweets || 0,
        reposts: tweet.reposts || 0,
        quotes: tweet.quotes || 0,
        likes: tweet.likes || 0,
        views: tweet.views || 0,
        bookmarks: tweet.bookmarks || 0,
        account_elapsed_s: account.elapsed_s || 0,
        account_error: account.error || "",
      });
    });
  }
  return rows;
}

async function main() {
  const args = parseArgs();
  const accounts = loadAccounts(args);
  const startedAt = utcNow();
  const totalStart = Date.now();

  console.log(`\n[Fast Puppeteer] Scraping ${accounts.length} X account(s)`);
  console.log(`  Tweets/account: ${args.maxTweets}`);
  console.log(`  Workers:        ${args.workers}`);
  console.log(`  Include pinned: ${!args.skipPinned}\n`);

  const browser = await puppeteer.launch({
    headless: !args.headed,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-blink-features=AutomationControlled",
    ],
  });

  const results = [];
  for (let i = 0; i < accounts.length; i += args.workers) {
    const batch = accounts.slice(i, i + args.workers);
    const batchStart = Date.now();
    const batchResults = await Promise.all(batch.map((handle) => scrapeAccount(browser, handle, args)));
    results.push(...batchResults);
    console.log(`  Batch ${Math.floor(i / args.workers) + 1} done in ${((Date.now() - batchStart) / 1000).toFixed(2)}s\n`);
  }

  if (!args.noRetryMissing) {
    const missing = results.filter((r) => !r.error && r.tweets.length === 0).map((r) => r.handle);
    if (missing.length) {
      console.log(`  Retrying ${missing.length} zero-tweet account(s) one by one...\n`);
      const retryByHandle = {};
      for (const handle of missing) {
        retryByHandle[handle] = await scrapeAccount(browser, handle, args);
      }
      for (let i = 0; i < results.length; i++) {
        if (retryByHandle[results[i].handle]) results[i] = retryByHandle[results[i].handle];
      }
    }
  }
  await browser.close();

  const finishedAt = utcNow();
  const totalS = Number(((Date.now() - totalStart) / 1000).toFixed(2));
  const perAccount = results.map((r) => r.elapsed_s);
  const tweetsTotal = results.reduce((sum, r) => sum + r.tweets.length, 0);
  const errors = results.filter((r) => r.error).length;
  const accountsWithTweets = results.filter((r) => r.tweets.length).length;
  const avg = perAccount.length ? Number((perAccount.reduce((a, b) => a + b, 0) / perAccount.length).toFixed(2)) : 0;
  const slowest = perAccount.length ? Math.max(...perAccount) : 0;

  const tweetRows = flattenRows(results, finishedAt);
  const timingRows = results.map((r) => ({
    scraped_at: finishedAt,
    handle: r.handle,
    elapsed_s: r.elapsed_s,
    tweets_found: r.tweets.length,
    error: r.error,
  }));

  const tweetFields = [
    "scraped_at", "handle", "rank", "tweet_id", "timestamp", "text", "url", "is_pinned",
    "comments", "replies", "retweets", "reposts", "quotes", "likes", "views", "bookmarks",
    "account_elapsed_s", "account_error",
  ];
  const timingFields = ["scraped_at", "handle", "elapsed_s", "tweets_found", "error"];
  writeCsv(TWEETS_CSV, tweetRows, tweetFields);
  writeCsv(TIMING_CSV, timingRows, timingFields);

  const output = {
    scraper: "fast_puppeteer_csv",
    started_at: startedAt,
    finished_at: finishedAt,
    accounts_total: accounts.length,
    accounts_with_tweets: accountsWithTweets,
    tweets_per_account_requested: args.maxTweets,
    tweets_total: tweetsTotal,
    errors,
    workers: args.workers,
    total_s: totalS,
    avg_per_account_s: avg,
    slowest_account_s: slowest,
    tweets_csv: TWEETS_CSV,
    timing_csv: TIMING_CSV,
    results,
  };
  fs.writeFileSync(JSON_OUTPUT, JSON.stringify(output, null, 2));

  console.log("-- Timing ------------------------------------------------");
  console.log(`  Accounts:             ${accounts.length}`);
  console.log(`  Accounts with tweets: ${accountsWithTweets}`);
  console.log(`  Tweets scraped:       ${tweetsTotal}`);
  console.log(`  Workers:              ${args.workers}`);
  console.log(`  Total time:           ${totalS}s`);
  console.log(`  Avg/account:          ${avg}s`);
  console.log(`  Slowest account:      ${slowest}s`);
  console.log(`  Errors:               ${errors}/${accounts.length}`);
  console.log(`  Tweets CSV:           ${TWEETS_CSV}`);
  console.log(`  Timing CSV:           ${TIMING_CSV}`);
  console.log("---------------------------------------------------------\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
