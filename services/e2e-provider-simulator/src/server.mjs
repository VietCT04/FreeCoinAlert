import http from "node:http";
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
    state.nextUpdateId = 1;
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
  if (requestUrl.pathname === "/api/v3/exchangeInfo") {
    const requested = parseSymbolsParameter(requestUrl.searchParams.get("symbols"));
    sendJson(response, 200, {
      timezone: "UTC",
      serverTime: simulatorTimeMs(),
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
      rows.push(binanceKline(symbol, openTime));
    }
    sendJson(response, 200, rows);
    return;
  }
  sendJson(response, 404, { code: -1, msg: "not_found" });
}

async function routeTelegramApi(request, response, requestUrl) {
  if (request.method !== "POST") {
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
  const body = await readJson(request);
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
  if (token) {
    queueTelegramUpdate(createStartUpdate({ token }));
  }
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
    sendJson(response, 500, { ok: false, error_code: 500, description: "temporary_failure" });
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
  state.eventTimeMs += 1;
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
  const parsed = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  return parsed && typeof parsed === "object" ? parsed : {};
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
