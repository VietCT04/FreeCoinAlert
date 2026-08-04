import { randomUUID } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPOSITORY_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const E2E_ENV_PATH = join(REPOSITORY_ROOT, ".env.e2e");
const ARTIFACT_DIRECTORY = join(REPOSITORY_ROOT, "artifacts", "e2e");
const RUN_SUMMARY_PATH = join(ARTIFACT_DIRECTORY, "run-summary.json");
const COMPOSE_PREFIX = [
  "compose",
  "-p",
  "freecoinalert-e2e",
  "--env-file",
  ".env.e2e",
  "-f",
  "compose.yaml",
  "-f",
  "compose.e2e.yaml",
];

const REQUIRED_SERVICES = [
  "db",
  "api-prepare",
  "db-migrate",
  "provider-simulator",
  "market-catalog-init",
  "e2e-seed",
  "api",
  "web",
  "market-stream",
  "telegram-updates",
  "notification-worker",
  "signal-telegram-dispatcher",
  "historical-analysis-worker",
  "e2e-control",
];

const SERVICE_KINDS = new Map([
  ["db", "healthy"],
  ["api-prepare", "completed"],
  ["db-migrate", "completed"],
  ["provider-simulator", "healthy"],
  ["market-catalog-init", "completed"],
  ["e2e-seed", "completed"],
  ["api", "healthy"],
  ["web", "healthy"],
  ["market-stream", "running"],
  ["telegram-updates", "running"],
  ["notification-worker", "running"],
  ["signal-telegram-dispatcher", "running"],
  ["historical-analysis-worker", "running"],
  ["e2e-control", "healthy"],
]);

const BUILD_SERVICES = [
  "provider-simulator",
  "api-prepare",
  "db-migrate",
  "market-catalog-init",
  "e2e-seed",
  "api",
  "web",
  "market-stream",
  "telegram-updates",
  "notification-worker",
  "signal-telegram-dispatcher",
  "historical-analysis-worker",
  "e2e-control",
  "e2e-tests",
];

const SECRET_KEYS = [
  "POSTGRES_PASSWORD",
  "TELEGRAM_BOT_TOKEN",
  "E2E_CONTROL_TOKEN",
];

let activeChild = null;
let signalCount = 0;
let cleanupStarted = false;
let stackTouched = false;
let composeEnvironment = process.env;

class RunnerError extends Error {
  constructor(message, exitCode = 1) {
    super(message);
    this.exitCode = exitCode;
  }
}

function parseEnvFile(contents) {
  const values = Object.create(null);
  const errors = [];

  for (const [index, line] of contents.split(/\r?\n/).entries()) {
    const trimmedLine = line.trim();

    if (trimmedLine === "" || trimmedLine.startsWith("#")) {
      continue;
    }

    const match = trimmedLine.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) {
      errors.push(`Invalid .env.e2e line ${index + 1}.`);
      continue;
    }

    const [, key, rawValue] = match;
    if (Object.prototype.hasOwnProperty.call(values, key)) {
      errors.push(`Duplicate .env.e2e key ${key}.`);
      continue;
    }

    let value = rawValue.trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }

  if (errors.length) {
    throw new RunnerError(errors.join(" "));
  }

  return values;
}

function requireValue(values, key) {
  if (!values[key]) {
    throw new RunnerError(`Set ${key} in .env.e2e.`);
  }
  return values[key];
}

function parsePort(values, key) {
  const value = Number(requireValue(values, key));
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    throw new RunnerError(`Set ${key} to a valid port in .env.e2e.`);
  }
  return value;
}

function validateE2EConfiguration(values) {
  const requiredKeys = [
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "WEB_PORT",
    "API_PORT",
    "POSTGRES_PORT",
    "WEB_ORIGIN",
    "NEXT_PUBLIC_API_BASE_URL",
    "SESSION_COOKIE_SECURE",
    "E2E_TEST_MODE",
    "E2E_CLOCK_NOW",
    "E2E_CONTROL_TOKEN",
    "TELEGRAM_BOT_API_BASE_URL",
    "TELEGRAM_BOT_FILE_BASE_URL",
    "TELEGRAM_PUBLIC_BOT_BASE_URL",
    "BINANCE_SPOT_BASE_URL",
    "BINANCE_SPOT_WS_BASE_URL",
  ];

  for (const key of requiredKeys) {
    requireValue(values, key);
  }

  if (values.E2E_TEST_MODE !== "true") {
    throw new RunnerError(".env.e2e must set E2E_TEST_MODE=true.");
  }

  if (values.SESSION_COOKIE_SECURE !== "false") {
    throw new RunnerError(".env.e2e must set SESSION_COOKIE_SECURE=false.");
  }

  if (!values.POSTGRES_DB.endsWith("_e2e")) {
    throw new RunnerError("The E2E database name must end in _e2e.");
  }

  const ports = [
    parsePort(values, "WEB_PORT"),
    parsePort(values, "API_PORT"),
    parsePort(values, "POSTGRES_PORT"),
  ];
  if (new Set(ports).size !== ports.length) {
    throw new RunnerError("E2E web, API, and database ports must be distinct.");
  }
  if (ports.some((port) => [3000, 8000, 5432].includes(port))) {
    throw new RunnerError("E2E ports must differ from normal local defaults.");
  }

  const providerUrls = [
    "TELEGRAM_BOT_API_BASE_URL",
    "TELEGRAM_BOT_FILE_BASE_URL",
    "TELEGRAM_PUBLIC_BOT_BASE_URL",
    "BINANCE_SPOT_BASE_URL",
    "BINANCE_SPOT_WS_BASE_URL",
  ];
  for (const key of providerUrls) {
    let parsed;
    try {
      parsed = new URL(values[key]);
    } catch {
      throw new RunnerError(`Set ${key} to a valid provider-simulator URL.`);
    }
    if (parsed.hostname !== "provider-simulator") {
      throw new RunnerError(`${key} must resolve to provider-simulator in E2E mode.`);
    }
  }

  const profiles = new Set((values.COMPOSE_PROFILES || "").split(","));
  for (const profile of ["market", "telegram", "historical-analysis", "e2e"]) {
    if (!profiles.has(profile)) {
      throw new RunnerError(`.env.e2e must enable the ${profile} Compose profile.`);
    }
  }
}

function setComposeEnvironment(values) {
  const environment = { ...process.env };
  for (const key of Object.keys(values)) {
    delete environment[key];
  }
  delete environment.COMPOSE_FILE;
  delete environment.COMPOSE_PROJECT_NAME;
  environment.COMPOSE_PROFILES = values.COMPOSE_PROFILES;
  composeEnvironment = environment;
}

function parseNodeVersion(version) {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)/);
  return match ? match.slice(1).map(Number) : null;
}

function verifyNodeEngine() {
  const version = parseNodeVersion(process.versions.node);
  if (!version) {
    throw new RunnerError("Could not determine the Node.js version.");
  }

  const [major, minor, patch] = version;
  if (major !== 24 || minor < 18 || (minor === 18 && patch < 0)) {
    throw new RunnerError("Node.js 24.18.0 through 24.x is required for pnpm e2e.");
  }
}

function runCapture(args) {
  try {
    const result = spawnSync("docker", args, {
      cwd: REPOSITORY_ROOT,
      env: composeEnvironment,
      encoding: "utf8",
      shell: false,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    return {
      ok: result.error === undefined && result.status === 0,
      status: result.status,
      stdout: typeof result.stdout === "string" ? result.stdout : "",
      stderr: typeof result.stderr === "string" ? result.stderr : "",
    };
  } catch {
    return { ok: false, status: null, stdout: "", stderr: "" };
  }
}

function verifyDocker() {
  if (!runCapture(["version"]).ok) {
    throw new RunnerError("Docker Engine is unavailable; start Docker and rerun pnpm e2e.");
  }

  const composeVersion = runCapture(["compose", "version"]);
  if (!composeVersion.ok || !/version\s+v?2\./i.test(`${composeVersion.stdout}\n${composeVersion.stderr}`)) {
    throw new RunnerError("Docker Compose v2 is required for pnpm e2e.");
  }

  if (!runCapture([...COMPOSE_PREFIX, "config", "--quiet"]).ok) {
    throw new RunnerError("The isolated E2E Compose configuration is invalid.");
  }
}

function composeArgs(...args) {
  return [...COMPOSE_PREFIX, ...args];
}

function runProcess(args, { environment = composeEnvironment } = {}) {
  return new Promise((resolveProcess) => {
    let child;
    try {
      child = spawn("docker", args, {
        cwd: REPOSITORY_ROOT,
        env: environment,
        shell: false,
        stdio: "inherit",
        windowsHide: true,
      });
    } catch {
      resolveProcess({ code: 127, signal: null });
      return;
    }

    activeChild = child;
    child.once("error", () => {
      if (activeChild === child) {
        activeChild = null;
      }
      resolveProcess({ code: 127, signal: null });
    });
    child.once("exit", (code, signal) => {
      if (activeChild === child) {
        activeChild = null;
      }
      resolveProcess({ code: signal ? 130 : code ?? 1, signal });
    });
  });
}

function handleSignal() {
  signalCount += 1;
  if (activeChild && activeChild.exitCode === null) {
    if (signalCount === 1) {
      try {
        activeChild.kill("SIGINT");
      } catch {
        activeChild.kill();
      }
      return;
    }

    try {
      activeChild.kill("SIGKILL");
    } catch {
      activeChild.kill();
    }
  }
}

function registerSignalHandlers() {
  process.on("SIGINT", handleSignal);
  process.on("SIGTERM", handleSignal);
}

function throwIfInterrupted() {
  if (signalCount > 0) {
    throw new RunnerError("The E2E run was interrupted.", 130);
  }
}

function safeArtifactDirectory() {
  const resolved = resolve(ARTIFACT_DIRECTORY);
  const expected = resolve(REPOSITORY_ROOT, "artifacts", "e2e");
  if (resolved !== expected) {
    throw new RunnerError("The E2E artifact directory is not the fixed repository artifact path.");
  }
  return resolved;
}

function prepareArtifacts() {
  const directory = safeArtifactDirectory();
  rmSync(directory, { recursive: true, force: true });
  mkdirSync(directory, { recursive: true });
}

function parseComposeServices(output) {
  const trimmed = output.trim();
  if (!trimmed) {
    return [];
  }

  try {
    const parsed = JSON.parse(trimmed);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return trimmed
      .split(/\r?\n/)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  }
}

function serviceExitCode(service) {
  const value = service.ExitCode ?? service.exitCode ?? service.exit_code;
  return value === undefined || value === null || value === "" ? null : Number(value);
}

function normalizeServiceStatus(service, kind) {
  if (!service) {
    return "missing";
  }

  const state = String(service.State ?? service.state ?? "").toLowerCase();
  const health = String(service.Health ?? service.health ?? "").toLowerCase();
  const status = String(service.Status ?? service.status ?? "").toLowerCase();
  const restarting = state === "restarting" || status.includes("restarting");
  const unhealthy = health === "unhealthy" || status.includes("unhealthy");
  const starting =
    health === "starting" || state === "created" || status.includes("starting");

  if (kind === "completed") {
    if (state === "exited" && serviceExitCode(service) === 0) {
      return "completed";
    }
    if (state === "exited" || state === "dead" || restarting || unhealthy) {
      return "failed";
    }
    return starting || state === "running" ? "starting" : "stopped";
  }

  if (kind === "running") {
    if (state === "dead" || state === "exited" || restarting || unhealthy) {
      return "failed";
    }
    if (starting) {
      return "starting";
    }
    return state === "running" ? "running" : "stopped";
  }

  if (state === "dead" || state === "exited" || restarting || unhealthy) {
    return "failed";
  }
  if (health === "healthy") {
    return "healthy";
  }
  if (starting) {
    return "starting";
  }
  return state === "running" ? "running" : "stopped";
}

function inspectServices() {
  const result = runCapture(composeArgs("ps", "--all", "--format", "json"));
  const records = new Map();
  for (const service of parseComposeServices(result.stdout)) {
    const name = service.Service ?? service.service;
    if (name) {
      records.set(name, service);
    }
  }

  const statuses = REQUIRED_SERVICES.map((name) => ({
    name,
    status: normalizeServiceStatus(records.get(name), SERVICE_KINDS.get(name)),
  }));
  return { ok: result.ok, statuses, records };
}

function readinessFailures(statuses) {
  return statuses.filter(({ name, status }) => {
    const kind = SERVICE_KINDS.get(name);
    if (kind === "completed") return status !== "completed";
    if (kind === "healthy") return status !== "healthy";
    return status !== "running";
  });
}

function redactText(text, values) {
  let result = text.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, "");
  for (const key of SECRET_KEYS) {
    const value = values[key];
    if (!value) continue;
    result = result.split(value).join("[REDACTED]");
  }
  return result;
}

function captureComposeLogs(values) {
  const logDirectory = join(ARTIFACT_DIRECTORY, "compose-logs");
  mkdirSync(logDirectory, { recursive: true });
  for (const service of [...REQUIRED_SERVICES, "e2e-tests"]) {
    const result = runCapture(
      composeArgs("logs", "--no-color", "--timestamps", "--tail", "1000", service),
    );
    const body = redactText(`${result.stdout}${result.stderr}`, values);
    writeFileSync(join(logDirectory, `${service}.log`), body, "utf8");
  }
}

function emptyTestCounts() {
  return { total: 0, passed: 0, failed: 0, skipped: 0, timedOut: 0 };
}

function readTestCounts() {
  const resultPath = join(ARTIFACT_DIRECTORY, "results.json");
  if (!existsSync(resultPath)) {
    return emptyTestCounts();
  }

  try {
    const report = JSON.parse(readFileSync(resultPath, "utf8"));
    const counts = emptyTestCounts();
    const visitSuite = (suite) => {
      for (const spec of suite.specs || []) {
        for (const test of spec.tests || []) {
          counts.total += 1;
          const lastResult = test.results?.at(-1);
          const status = lastResult?.status;
          if (status === "passed") counts.passed += 1;
          else if (status === "skipped") counts.skipped += 1;
          else if (status === "timedOut") counts.timedOut += 1;
          else counts.failed += 1;
        }
      }
      for (const child of suite.suites || []) visitSuite(child);
    };
    for (const suite of report.suites || []) visitSuite(suite);
    return counts;
  } catch {
    return emptyTestCounts();
  }
}

function writeRunSummary(statuses, startTime, exitCode) {
  writeFileSync(
    RUN_SUMMARY_PATH,
    JSON.stringify(
      {
        services: statuses,
        testCounts: readTestCounts(),
        startedAt: startTime,
        endedAt: new Date().toISOString(),
        exitCode,
      },
      null,
      2,
    ),
    "utf8",
  );
}

async function cleanupStack() {
  if (cleanupStarted) {
    return { code: 0 };
  }
  cleanupStarted = true;
  return runProcess(composeArgs("down", "--volumes", "--remove-orphans"));
}

function nextRunId() {
  return `${Date.now().toString(36)}-${randomUUID().slice(0, 8)}`;
}

async function startStack() {
  const build = await runProcess(composeArgs("build", ...BUILD_SERVICES));
  if (build.code !== 0) {
    throw new RunnerError("The isolated E2E images could not be built.", build.code);
  }
  throwIfInterrupted();

  stackTouched = true;
  const up = await runProcess(
    composeArgs(
      "up",
      "--detach",
      "--wait",
      "--wait-timeout",
      "300",
      ...REQUIRED_SERVICES,
    ),
  );
  if (up.code !== 0) {
    throw new RunnerError("The isolated E2E services did not start successfully.", up.code);
  }
  throwIfInterrupted();

  const inspection = inspectServices();
  const failures = readinessFailures(inspection.statuses);
  if (!inspection.ok || failures.length) {
    throw new RunnerError("The isolated E2E services did not reach their required states.");
  }
}

async function runBrowserCommand(mode, runId) {
  const command = ["run", "--rm"];
  if (mode === "ui") {
    command.push("--service-ports");
  }
  command.push("-e", `E2E_RUN_ID=${runId}`, "e2e-tests", "pnpm", "exec", "playwright", "test");
  if (mode === "ui") {
    command.push("--ui", "--ui-host=0.0.0.0", "--ui-port=9323");
    console.log("Playwright UI: http://localhost:9323");
  }
  return runProcess(composeArgs(...command));
}

async function runSuite(mode) {
  const startTime = new Date().toISOString();
  let values;
  let primaryExitCode = 0;
  let statuses = REQUIRED_SERVICES.map((name) => ({ name, status: "not_started" }));

  try {
    verifyNodeEngine();
    if (!existsSync(E2E_ENV_PATH)) {
      throw new RunnerError(".env.e2e is missing from the repository root.");
    }
    values = parseEnvFile(readFileSync(E2E_ENV_PATH, "utf8"));
    validateE2EConfiguration(values);
    setComposeEnvironment(values);
    verifyDocker();

    stackTouched = true;
    const staleResources = await runProcess(
      composeArgs("down", "--volumes", "--remove-orphans"),
    );
    if (staleResources.code !== 0) {
      throw new RunnerError("Stale E2E resources could not be removed.", staleResources.code);
    }
    throwIfInterrupted();
    prepareArtifacts();

    await startStack();
    const run = await runBrowserCommand(mode, nextRunId());
    primaryExitCode = run.code;
    throwIfInterrupted();
    const inspection = inspectServices();
    statuses = inspection.statuses;
    if (primaryExitCode !== 0) {
      captureComposeLogs(values);
    }
    writeRunSummary(statuses, startTime, primaryExitCode);
  } catch (error) {
    primaryExitCode = error instanceof RunnerError ? error.exitCode : 1;
    if (values) {
      const inspection = inspectServices();
      statuses = inspection.statuses;
      captureComposeLogs(values);
      writeRunSummary(statuses, startTime, primaryExitCode);
    }
    console.error(error instanceof Error ? error.message : "The E2E runner failed.");
  } finally {
    if (stackTouched) {
      const cleanup = await cleanupStack();
      if (primaryExitCode === 0 && cleanup.code !== 0) {
        primaryExitCode = cleanup.code;
        if (values) {
          writeRunSummary(statuses, startTime, primaryExitCode);
        }
      }
    }
  }

  return primaryExitCode;
}

async function runReport() {
  verifyNodeEngine();
  if (!existsSync(join(ARTIFACT_DIRECTORY, "playwright-report"))) {
    console.error("No Playwright HTML report exists under artifacts/e2e.");
    return 1;
  }
  if (!existsSync(E2E_ENV_PATH)) {
    throw new RunnerError(".env.e2e is missing from the repository root.");
  }
  const values = parseEnvFile(readFileSync(E2E_ENV_PATH, "utf8"));
  validateE2EConfiguration(values);
  setComposeEnvironment(values);
  verifyDocker();
  const result = await runProcess(
    composeArgs(
      "run",
      "--rm",
      "--no-deps",
      "--build",
      "e2e-tests",
      "pnpm",
      "exec",
      "playwright",
      "show-report",
      "/artifacts/e2e/playwright-report",
    ),
  );
  return result.code;
}

async function main() {
  registerSignalHandlers();
  const mode = process.argv[2] || "run";
  if (process.argv.length > 3 || !["run", "ui", "report"].includes(mode)) {
    console.error("Use pnpm e2e, pnpm e2e:ui, or pnpm e2e:report.");
    return 2;
  }
  if (mode === "report") {
    return runReport();
  }
  return runSuite(mode);
}

main()
  .then((exitCode) => {
    process.exitCode = exitCode;
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : "The E2E runner failed.");
    process.exitCode = error instanceof RunnerError ? error.exitCode : 1;
  });
