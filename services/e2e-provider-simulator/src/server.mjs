import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import { dirname } from "node:path";
import { URL } from "node:url";

import { WebSocket, WebSocketServer } from "ws";

const PORT = Number(process.env.PORT || 9000);
const CONTROL_TOKEN = process.env.E2E_CONTROL_TOKEN || "";
const WORKER_GATE_PATH = process.env.E2E_WORKER_GATE_PATH || "/e2e/worker-gates.json";
const configuredClock = Date.parse(process.env.E2E_CLOCK_NOW || "");
const E2E_CLOCK_NOW_MS = Number.isFinite(configuredClock)
  ? configuredClock
  : Date.UTC(2026, 7, 4);
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
const BASE_PRICES = {
  BTCUSDT: 100,
  ETHUSDT: 110,
  BNBUSDT: 120,
  SOLUSDT: 130,
  XRPUSDT: 140,
};
const OUTCOMES = new Set([
  "sent",
  "temporary_failure",
  "permanent_failure",
  "rate_limited",
  "uncertain",
]);
const REST_OUTCOMES = new Set(["success", "rate_limited", "ip_banned", "server_error"]);
const ARCHIVE_OUTCOMES = new Set(["available", "not_found", "checksum_mismatch", "server_error"]);

const state = {
  sequence: 0,
  disconnected: false,
  unavailableSymbols: new Set(),
  currentPrices: new Map(),
  klineOverrides: new Map(),
  clients: new Set(),
  telegramUpdates: [],
  pendingPolls: [],
  nextUpdateId: 1,
  nextMessageId: 1,
  telegramOutcomes: [],
  telegramMessages: [],
  browserVisits: [],
  restOutcomes: [],
  restRequestCounts: new Map(),
  archiveOutcomes: new Map(),
  archiveRequestCounts: new Map(),
  archivePayloads: new Map(),
  workerGates: new Map(),
  eventTimeMs: E2E_CLOCK_NOW_MS - 1_000,
};

const server = http.createServer(async (request, response) => {
  try {
    await routeHttpRequest(request, response);
  } catch (error) {
    console.error("provider-simulator.request_failed", error);
    if (!response.headersSent) {
      sendJson(response, 500, { ok: false, description: "simulator_error" });
    } else {
      response.destroy();
    }
  }
});

const websocketServer = new WebSocketServer({ noServer: true });
server.on("upgrade", (request, socket, head) => {
  const requestUrl = new URL(request.url || "/", "http://provider-simulator");
  if (requestUrl.pathname !== "/stream" || state.disconnected) {
    socket.destroy();
    return;
  }
  websocketServer.handleUpgrade(request, socket, head, (client) => {
    client.streams = new Set((requestUrl.searchParams.get("streams") || "").split("/"));
    state.clients.add(client);
    client.on("close", () => state.clients.delete(client));
    client.on("error", () => state.clients.delete(client));
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`provider-simulator.listening port=${PORT}`);
});

async function routeHttpRequest(request, response) {
  const requestUrl = new URL(request.url || "/", "http://provider-simulator");
  if (request.method === "GET" && requestUrl.pathname === "/health") {
    sendJson(response, 200, { status: "ok", service: "provider-simulator" });
    return;
  }
  if (requestUrl.pathname.startsWith("/__e2e/")) {
    await routeControl(request, response, requestUrl);
    return;
  }
  if (request.method === "GET" && requestUrl.pathname.startsWith("/telegram/")) {
    await routeTelegramStart(request, response, requestUrl);
    return;
  }
  if (requestUrl.pathname.startsWith("/api/v3/")) {
    await routeBinance(request, response, requestUrl);
    return;
  }
  if (requestUrl.pathname.startsWith("/data/spot/")) {
    await routePublicArchive(request, response, requestUrl);
    return;
  }
  if (requestUrl.pathname.startsWith("/bot") || requestUrl.pathname.startsWith("/file/bot")) {
    await routeTelegramApi(request, response, requestUrl);
    return;
  }
  sendJson(response, 404, { ok: false, description: "not_found" });
}

async function routeControl(request, response, requestUrl) {
  if (!authorized(request)) {
    sendJson(response, 404, { ok: false, description: "not_found" });
    return;
  }
  const body = request.method === "GET" ? {} : await readJson(request);
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/reset") {
    state.disconnected = false;
    state.currentPrices.clear();
    state.klineOverrides.clear();
    state.telegramUpdates = [];
    state.telegramOutcomes = normalizeOutcomes(body.outcomes || []);
    state.telegramMessages = [];
    state.browserVisits = [];
    state.restOutcomes = [];
    state.restRequestCounts.clear();
    state.archiveOutcomes.clear();
    state.archiveRequestCounts.clear();
    state.archivePayloads.clear();
    // Telegram update IDs are monotonic for the lifetime of a bot. Keep the
    // counter across fixture resets so the real poller's offset remains valid.
    state.nextMessageId = 1;
    state.unavailableSymbols = new Set(normalizeSymbols(body.unavailableSymbols));
    state.workerGates.clear();
    await clearWorkerGates();
    sendJson(response, 200, acknowledge());
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/price") {
    sendJson(response, 200, publishPrice(body));
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/kline") {
    sendJson(response, 200, publishKline(body));
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/disconnect") {
    state.disconnected = true;
    for (const client of state.clients) {
      client.close(1012, "e2e_disconnect");
    }
    sendJson(response, 200, acknowledge());
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/reconnect") {
    state.disconnected = false;
    sendJson(response, 200, acknowledge());
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/telegram/update") {
    const update = body.update || createStartUpdate(body);
    const updateId = queueTelegramUpdate(update);
    sendJson(response, 200, { ...acknowledge(), updateId });
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/telegram/outcomes") {
    const outcomes = normalizeOutcomes(body.outcomes || (body.outcome ? [body.outcome] : []));
    state.telegramOutcomes.push(...outcomes);
    sendJson(response, 200, { ...acknowledge(), outcomes });
    return;
  }
  if (request.method === "GET" && requestUrl.pathname === "/__e2e/telegram/messages") {
    sendJson(response, 200, {
      messages: state.telegramMessages,
      browserVisits: state.browserVisits,
    });
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/rest-outcomes") {
    state.restOutcomes = normalizeRestOutcomes(body.outcomes);
    sendJson(response, 200, { ...acknowledge(), outcomes: state.restOutcomes });
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/binance/archive-outcomes") {
    state.archiveOutcomes.clear();
    for (const [archiveKey, outcome] of Object.entries(body.outcomes || {})) {
      if (ARCHIVE_OUTCOMES.has(outcome)) {
        state.archiveOutcomes.set(archiveKey, outcome);
      }
    }
    sendJson(response, 200, { ...acknowledge(), outcomes: Object.fromEntries(state.archiveOutcomes) });
    return;
  }
  if (request.method === "GET" && requestUrl.pathname === "/__e2e/binance/counters") {
    sendJson(response, 200, {
      rest: Object.fromEntries(state.restRequestCounts),
      archives: Object.fromEntries(state.archiveRequestCounts),
    });
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/historical-worker/gates") {
    const names = normalizeGateNames(body.names);
    for (const name of names) {
      state.workerGates.set(name, false);
    }
    await updateWorkerGates(names, false);
    sendJson(response, 200, { ...acknowledge(), gates: [...state.workerGates.keys()] });
    return;
  }
  if (request.method === "POST" && requestUrl.pathname === "/__e2e/historical-worker/release") {
    const names = normalizeGateNames(body.names);
    for (const name of names) {
      state.workerGates.set(name, true);
    }
    await updateWorkerGates(names, true);
    sendJson(response, 200, { ...acknowledge(), released: names });
    return;
  }
  sendJson(response, 404, { ok: false, description: "not_found" });
}

async function routeBinance(request, response, requestUrl) {
  if (request.method !== "GET") {
    sendJson(response, 405, { code: -1, msg: "method_not_allowed" });
    return;
  }
  const route = requestUrl.pathname.slice("/api/v3/".length);
  incrementCount(state.restRequestCounts, route);
  const outcome = state.restOutcomes.shift() || "success";
  if (outcome === "rate_limited" || outcome === "ip_banned") {
    response.setHeader("Retry-After", "3600");
    response.setHeader("X-MBX-USED-WEIGHT-1M", "1200");
    sendJson(response, outcome === "rate_limited" ? 429 : 418, {
      code: outcome === "rate_limited" ? -1003 : -1003,
      msg: outcome,
    });
    return;
  }
  if (outcome === "server_error") {
    sendJson(response, 503, { code: -1, msg: "server_error" });
    return;
  }
  if (requestUrl.pathname === "/api/v3/exchangeInfo") {
    const requested = parseSymbolsParameter(requestUrl.searchParams.get("symbols"));
    response.setHeader("X-MBX-USED-WEIGHT-1M", "20");
    sendJson(response, 200, {
      timezone: "UTC",
      serverTime: simulatorTimeMs(),
      rateLimits: [
        {
          rateLimitType: "REQUEST_WEIGHT",
          interval: "MINUTE",
          intervalNum: 1,
          limit: 1200,
        },
      ],
      symbols: requested.map(exchangeInfoSymbol),
    });
    return;
  }
  if (requestUrl.pathname === "/api/v3/klines") {
    const symbol = requestUrl.searchParams.get("symbol");
    if (!SYMBOLS.includes(symbol) || state.unavailableSymbols.has(symbol)) {
      sendJson(response, 400, { code: -1121, msg: "Invalid symbol." });
      return;
    }
    const startTime = Number(requestUrl.searchParams.get("startTime"));
    const endTime = Number(requestUrl.searchParams.get("endTime"));
    const limit = Math.min(Number(requestUrl.searchParams.get("limit") || 1000), 1000);
    if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || startTime >= endTime) {
      sendJson(response, 400, { code: -1100, msg: "Invalid time range." });
      return;
    }
    const rows = [];
    for (let openTime = startTime - (startTime % 60_000); openTime < endTime && rows.length < limit; openTime += 60_000) {
      rows.push(binanceKlineRow(binanceKline(symbol, openTime)));
    }
    response.setHeader("X-MBX-USED-WEIGHT-1M", "2");
    sendJson(response, 200, rows);
    return;
  }
  sendJson(response, 404, { code: -1, msg: "not_found" });
}

async function routePublicArchive(request, response, requestUrl) {
  if (request.method !== "GET") {
    sendJson(response, 405, { code: -1, msg: "method_not_allowed" });
    return;
  }

  const archiveKey = requestUrl.pathname.slice(1);
  incrementCount(state.archiveRequestCounts, archiveKey);
  const baseArchiveKey = archiveKey.endsWith(".CHECKSUM")
    ? archiveKey.slice(0, -".CHECKSUM".length)
    : archiveKey;
  const outcome = state.archiveOutcomes.get(archiveKey)
    || state.archiveOutcomes.get(baseArchiveKey)
    || "available";
  if (outcome === "server_error") {
    sendJson(response, 503, { code: -1, msg: "server_error" });
    return;
  }

  const fixture = getArchiveFixture(archiveKey);
  if (fixture === null || outcome === "not_found") {
    sendJson(response, 404, { code: -1, msg: "not_found" });
    return;
  }
  if (archiveKey.endsWith(".CHECKSUM")) {
    const checksum = outcome === "checksum_mismatch"
      ? "0".repeat(64)
      : fixture.checksum;
    response.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    response.end(`${checksum}  ${fixture.filename}\n`);
    return;
  }
  response.writeHead(200, { "content-type": "application/zip" });
  response.end(fixture.bytes);
}

function getArchiveFixture(archiveKey) {
  const checksumKey = archiveKey.endsWith(".CHECKSUM")
    ? archiveKey.slice(0, -".CHECKSUM".length)
    : archiveKey;
  const cached = state.archivePayloads.get(checksumKey);
  if (cached) return cached;

  const match = checksumKey.match(
    /^data\/spot\/(monthly|daily)\/klines\/([A-Z0-9]+)\/1m\/([^/]+\.zip)$/,
  );
  if (!match) return null;
  const [, granularity, symbol, filename] = match;
  const supportedFixture = (
    granularity === "monthly" && symbol === "ETHUSDT" && filename === "ETHUSDT-1m-2025-01.zip"
  ) || (
    granularity === "daily" && symbol === "BTCUSDT" && filename === "BTCUSDT-1m-2024-12-31.zip"
  ) || (
    granularity === "daily" && symbol === "ETHUSDT" && filename === "ETHUSDT-1m-2025-01-02.zip"
  );
  if (!supportedFixture) return null;

  const periodLabel = filename.slice(`${symbol}-1m-`.length, -".zip".length);
  const periodStart = granularity === "monthly"
    ? Date.parse(`${periodLabel}-01T00:00:00.000Z`)
    : Date.parse(`${periodLabel}T00:00:00.000Z`);
  const periodEnd = granularity === "monthly"
    ? Date.UTC(new Date(periodStart).getUTCFullYear(), new Date(periodStart).getUTCMonth() + 1, 1)
    : periodStart + 24 * 60 * 60 * 1000;
  const timestampMultiplier = periodStart < Date.UTC(2025, 0, 1) ? 1 : 1000;
  const rowCount = Math.round((periodEnd - periodStart) / 60_000);
  const rows = [];
  for (let index = 0; index < rowCount; index += 1) {
    const openTime = periodStart + index * 60_000;
    const open = 100 + (index % 600) / 100;
    const close = open + 0.01;
    const high = close + 0.02;
    const low = open - 0.02;
    const rawOpenTime = Math.round(openTime * timestampMultiplier);
    const rawCloseTime = Math.round((openTime + 59_999) * timestampMultiplier);
    rows.push([
      rawOpenTime,
      open.toFixed(6),
      high.toFixed(6),
      low.toFixed(6),
      close.toFixed(6),
      "1.000000",
      rawCloseTime,
      close.toFixed(6),
      1,
      0,
      1,
      0,
    ].join(","));
  }
  const csv = Buffer.from(`${rows.join("\n")}\n`, "utf8");
  const bytes = createStoredZip(filename.replace(".zip", ".csv"), csv);
  const fixture = {
    filename,
    bytes,
    checksum: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
  state.archivePayloads.set(checksumKey, fixture);
  return fixture;
}

function createStoredZip(filename, content) {
  const name = Buffer.from(filename, "utf8");
  const checksum = crc32(content);
  const local = Buffer.alloc(30 + name.length);
  local.writeUInt32LE(0x04034b50, 0);
  local.writeUInt16LE(20, 4);
  local.writeUInt32LE(0, 6);
  local.writeUInt16LE(0, 8);
  local.writeUInt16LE(0, 10);
  local.writeUInt16LE(0, 12);
  local.writeUInt32LE(checksum, 14);
  local.writeUInt32LE(content.length, 18);
  local.writeUInt32LE(content.length, 22);
  local.writeUInt16LE(name.length, 26);
  local.writeUInt16LE(0, 28);
  name.copy(local, 30);

  const central = Buffer.alloc(46 + name.length);
  central.writeUInt32LE(0x02014b50, 0);
  central.writeUInt16LE(20, 4);
  central.writeUInt16LE(20, 6);
  central.writeUInt32LE(0, 8);
  central.writeUInt16LE(0, 10);
  central.writeUInt16LE(0, 12);
  central.writeUInt16LE(0, 14);
  central.writeUInt32LE(checksum, 16);
  central.writeUInt32LE(content.length, 20);
  central.writeUInt32LE(content.length, 24);
  central.writeUInt16LE(name.length, 28);
  central.writeUInt16LE(0, 30);
  central.writeUInt16LE(0, 32);
  central.writeUInt16LE(0, 34);
  central.writeUInt16LE(0, 36);
  central.writeUInt32LE(0, 38);
  central.writeUInt32LE(0, 42);
  name.copy(central, 46);

  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(1, 8);
  end.writeUInt16LE(1, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(local.length + content.length, 16);
  end.writeUInt16LE(0, 20);
  return Buffer.concat([local, content, central, end]);
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value >>> 1) ^ (value & 1 ? 0xedb88320 : 0);
    }
  }
  return (value ^ 0xffffffff) >>> 0;
}

async function routeTelegramApi(request, response, requestUrl) {
  if (request.method !== "POST" && request.method !== "GET") {
    sendJson(response, 405, { ok: false, description: "method_not_allowed" });
    return;
  }
  const method = requestUrl.pathname.split("/").filter(Boolean).at(-1);
  if (method === "getMe") {
    sendJson(response, 200, {
      ok: true,
      result: { id: 900000001, is_bot: true, first_name: "E2E", username: "e2e_bot" },
    });
    return;
  }
  if (method === "deleteWebhook") {
    sendJson(response, 200, { ok: true, result: true });
    return;
  }
  const body = request.method === "GET"
    ? Object.fromEntries(requestUrl.searchParams)
    : await readJson(request);
  if (method === "getUpdates") {
    await handleGetUpdates(request, response, body);
    return;
  }
  if (method === "sendMessage") {
    handleSendMessage(request, response, body);
    return;
  }
  sendJson(response, 404, { ok: false, description: "method_not_found" });
}

async function routeTelegramStart(request, response, requestUrl) {
  const username = requestUrl.pathname.split("/").filter(Boolean).at(-1);
  const token = requestUrl.searchParams.get("start") || "";
  state.browserVisits.push({
    sequence: nextSequence(),
    username,
    token,
  });
  const html = "<!doctype html><html><body><p>E2E Telegram simulator</p></body></html>";
  response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  response.end(html);
}

async function handleGetUpdates(request, response, body) {
  const offset = Number.isFinite(Number(body.offset)) ? Number(body.offset) : 0;
  const ready = availableUpdates(offset);
  if (ready.length) {
    sendJson(response, 200, { ok: true, result: ready });
    return;
  }
  const timeoutSeconds = Math.min(Math.max(Number(body.timeout || 1), 1), 30);
  const pending = { request, response, offset };
  state.pendingPolls.push(pending);
  pending.timer = setTimeout(() => {
    const index = state.pendingPolls.indexOf(pending);
    if (index === -1) return;
    state.pendingPolls.splice(index, 1);
    sendJson(response, 200, { ok: true, result: [] });
  }, timeoutSeconds * 1000);
}

function handleSendMessage(request, response, body) {
  const chatId = Number(body.chat_id);
  const text = typeof body.text === "string" ? body.text : "";
  const outcome = state.telegramOutcomes.shift() || "sent";
  const message = {
    sequence: nextSequence(),
    chatId,
    text,
    outcome,
  };
  state.telegramMessages.push(message);
  if (outcome === "uncertain") {
    request.socket.destroy();
    return;
  }
  if (outcome === "temporary_failure") {
    sendJson(response, 500, {
      ok: false,
      error_code: 500,
      description: "Internal Server Error (500)",
    });
    return;
  }
  if (outcome === "permanent_failure") {
    sendJson(response, 400, { ok: false, error_code: 400, description: "permanent_failure" });
    return;
  }
  if (outcome === "rate_limited") {
    response.setHeader("Retry-After", "1");
    sendJson(response, 429, {
      ok: false,
      error_code: 429,
      description: "rate_limited",
      parameters: { retry_after: 1 },
    });
    return;
  }
  sendJson(response, 200, {
    ok: true,
    result: {
      message_id: state.nextMessageId++,
      date: Math.floor(simulatorTimeMs() / 1000),
      chat: { id: chatId, type: "private" },
      text,
    },
  });
}

function publishPrice(body) {
  const symbol = String(body.symbol || "").toUpperCase();
  if (!SYMBOLS.includes(symbol) || state.unavailableSymbols.has(symbol)) {
    return { accepted: false, ...acknowledge(), reason: "symbol_unavailable" };
  }
  const price = String(body.price || "");
  if (!/^\d+(\.\d+)?$/.test(price) || Number(price) <= 0) {
    return { accepted: false, ...acknowledge(), reason: "invalid_price" };
  }
  state.currentPrices.set(symbol, price);
  const eventTime = nextEventTime();
  const aggregateId = Number.isInteger(body.aggregateId) ? body.aggregateId : nextSequence();
  const data = {
    e: "aggTrade",
    E: eventTime,
    s: symbol,
    a: aggregateId,
    p: price,
    f: Number.isInteger(body.firstTradeId) ? body.firstTradeId : aggregateId * 2,
    l: Number.isInteger(body.lastTradeId) ? body.lastTradeId : aggregateId * 2 + 1,
    T: eventTime,
  };
  const ticker = {
    e: "24hrTicker",
    E: eventTime,
    s: symbol,
    c: price,
    b: price,
    a: price,
  };
  const published = [
    publishStream(`${symbol.toLowerCase()}@aggTrade`, data),
    publishStream(`${symbol.toLowerCase()}@ticker`, ticker),
  ].some(Boolean);
  return { accepted: true, ...acknowledge(), published };
}

function publishKline(body) {
  const symbol = String(body.symbol || "").toUpperCase();
  if (!SYMBOLS.includes(symbol) || state.unavailableSymbols.has(symbol)) {
    return { accepted: false, ...acknowledge(), reason: "symbol_unavailable" };
  }
  const openTime = Number.isFinite(Number(body.openTimeMs))
    ? Number(body.openTimeMs)
    : Math.floor(simulatorTimeMs() / 60_000) * 60_000 - 60_000;
  const kline = binanceKline(symbol, openTime, body);
  state.klineOverrides.set(`${symbol}:${openTime}`, kline);
  const published = publishStream(`${symbol.toLowerCase()}@kline_1m`, {
    e: "kline",
    E: nextEventTime(),
    s: symbol,
    k: klineToEvent(symbol, kline),
  });
  return { accepted: true, ...acknowledge(), published };
}

function binanceKline(symbol, openTime, override = {}) {
  const existing = state.klineOverrides.get(`${symbol}:${openTime}`);
  if (existing && Object.keys(override).length === 0) return existing;
  const base = BASE_PRICES[symbol] + (Math.floor(openTime / 60_000) % 1_440) / 100;
  const openPrice = String(override.openPrice || base.toFixed(6));
  const closePrice = String(override.closePrice || (Number(openPrice) + 0.01).toFixed(6));
  const highPrice = String(override.highPrice || Math.max(Number(openPrice), Number(closePrice) + 0.02).toFixed(6));
  const lowPrice = String(override.lowPrice || Math.min(Number(openPrice), Number(closePrice) - 0.02).toFixed(6));
  return {
    openTime,
    closeTime: openTime + 59_999,
    openPrice,
    highPrice,
    lowPrice,
    closePrice,
    baseVolume: String(override.baseVolume || "1.000000"),
    quoteVolume: String(override.quoteVolume || closePrice),
    tradeCount: Number.isInteger(override.tradeCount) ? override.tradeCount : 1,
    firstTradeId: Number.isInteger(override.firstTradeId) ? override.firstTradeId : 0,
    lastTradeId: Number.isInteger(override.lastTradeId) ? override.lastTradeId : 1,
    closed: override.closed !== false,
  };
}

function binanceKlineRow(kline) {
  return [
    kline.openTime,
    kline.openPrice,
    kline.highPrice,
    kline.lowPrice,
    kline.closePrice,
    kline.baseVolume,
    kline.closeTime,
    kline.quoteVolume,
    kline.tradeCount,
    kline.firstTradeId,
    kline.lastTradeId,
    "0",
  ];
}

function klineToEvent(symbol, kline) {
  return {
    t: kline.openTime,
    T: kline.closeTime,
    s: symbol,
    i: "1m",
    o: kline.openPrice,
    c: kline.closePrice,
    h: kline.highPrice,
    l: kline.lowPrice,
    v: kline.baseVolume,
    q: kline.quoteVolume,
    n: kline.tradeCount,
    f: kline.firstTradeId,
    L: kline.lastTradeId,
    x: kline.closed,
  };
}

function publishStream(stream, data) {
  let published = false;
  for (const client of state.clients) {
    if (client.readyState !== WebSocket.OPEN || !client.streams.has(stream)) continue;
    client.send(JSON.stringify({ stream, data }));
    published = true;
  }
  return published;
}

function exchangeInfoSymbol(symbol) {
  const unavailable = state.unavailableSymbols.has(symbol);
  return {
    symbol,
    status: unavailable ? "HALT" : "TRADING",
    baseAsset: symbol.replace("USDT", ""),
    quoteAsset: "USDT",
    isSpotTradingAllowed: !unavailable,
    permissions: unavailable ? [] : ["SPOT"],
    filters: [
      {
        filterType: "PRICE_FILTER",
        minPrice: "0.000001",
        maxPrice: "1000000000",
        tickSize: "0.000001",
      },
    ],
  };
}

function availableUpdates(offset) {
  return state.telegramUpdates.filter((update) => update.update_id >= offset);
}

function queueTelegramUpdate(update) {
  const normalized = {
    ...update,
    update_id: Number.isInteger(update.update_id) ? update.update_id : state.nextUpdateId++,
  };
  state.telegramUpdates.push(normalized);
  for (const pending of [...state.pendingPolls]) {
    const ready = availableUpdates(pending.offset);
    if (!ready.length) continue;
    state.pendingPolls.splice(state.pendingPolls.indexOf(pending), 1);
    clearTimeout(pending.timer);
    sendJson(pending.response, 200, { ok: true, result: ready });
  }
  return normalized.update_id;
}

function createStartUpdate(body) {
  const chatId = Number.isInteger(body.chatId) ? body.chatId : 700000001;
  const token = String(body.token || "");
  const text = String(body.text || `/start ${token}`).trim();
  return {
    message: {
      message_id: state.nextMessageId++,
      date: Math.floor(simulatorTimeMs() / 1000),
      chat: { id: chatId, type: "private", username: "e2e_user" },
      from: { id: chatId, is_bot: false, first_name: "E2E", username: "e2e_user" },
      text,
      entities: text.startsWith("/start") ? [{ type: "bot_command", offset: 0, length: 6 }] : [],
    },
  };
}

function parseSymbolsParameter(value) {
  if (!value) return SYMBOLS;
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) return parsed.map((symbol) => String(symbol).toUpperCase()).filter((symbol) => SYMBOLS.includes(symbol));
  } catch {
    return SYMBOLS;
  }
  return SYMBOLS;
}

function normalizeSymbols(value) {
  return Array.isArray(value)
    ? value.map((symbol) => String(symbol).toUpperCase()).filter((symbol) => SYMBOLS.includes(symbol))
    : [];
}

function normalizeOutcomes(value) {
  return Array.isArray(value) ? value.filter((outcome) => OUTCOMES.has(outcome)) : [];
}

function normalizeRestOutcomes(value) {
  return Array.isArray(value)
    ? value.filter((outcome) => REST_OUTCOMES.has(outcome))
    : [];
}

function incrementCount(counts, key) {
  counts.set(key, (counts.get(key) || 0) + 1);
}

function normalizeGateNames(value) {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : ["historical_analysis_before_run"];
}

function acknowledge() {
  return { accepted: true, sequence: nextSequence() };
}

function simulatorTimeMs() {
  return state.eventTimeMs;
}

function nextEventTime() {
  // The API validates live provider events against wall-clock freshness. Keep
  // the event sequence monotonic while ensuring simulated live events are not
  // rejected as stale when the E2E scenario clock is intentionally fixed.
  state.eventTimeMs = Math.max(state.eventTimeMs + 1, Date.now() - 1_000);
  return state.eventTimeMs;
}

function nextSequence() {
  state.sequence += 1;
  return state.sequence;
}

function authorized(request) {
  return Boolean(CONTROL_TOKEN) && request.headers["x-e2e-control-token"] === CONTROL_TOKEN;
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  if (!chunks.length) return {};
  const rawBody = Buffer.concat(chunks).toString("utf8");
  try {
    const parsed = JSON.parse(rawBody);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return Object.fromEntries(new URLSearchParams(rawBody));
  }
}

function sendJson(response, status, payload) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function clearWorkerGates() {
  await writeWorkerGates({});
}

async function updateWorkerGates(names, released) {
  let gateState = { gates: {} };
  try {
    const parsed = JSON.parse(await fs.readFile(WORKER_GATE_PATH, "utf8"));
    if (parsed && typeof parsed === "object" && parsed.gates && typeof parsed.gates === "object") {
      gateState = { gates: { ...parsed.gates } };
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  for (const name of names) gateState.gates[name] = released;
  await writeWorkerGates(gateState.gates);
}

async function writeWorkerGates(gates) {
  const temporaryPath = `${WORKER_GATE_PATH}.tmp`;
  await fs.mkdir(dirname(WORKER_GATE_PATH), { recursive: true });
  await fs.writeFile(temporaryPath, JSON.stringify({ gates }), "utf8");
  await fs.rename(temporaryPath, WORKER_GATE_PATH);
}
