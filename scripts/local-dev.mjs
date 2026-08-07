import { copyFileSync, existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath, URL } from "node:url";

const REPOSITORY_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ENV_PATH = join(REPOSITORY_ROOT, ".env");
const ENV_EXAMPLE_PATH = join(REPOSITORY_ROOT, ".env.example");

const REQUIRED_CONFIGURATION_KEYS = [
  "POSTGRES_DB",
  "POSTGRES_USER",
  "POSTGRES_PASSWORD",
  "WEB_PORT",
  "API_PORT",
  "POSTGRES_PORT",
  "NEXT_PUBLIC_API_BASE_URL",
  "WEB_ORIGIN",
  "SESSION_COOKIE_SECURE",
  "BINANCE_SPOT_BASE_URL",
  "BINANCE_SPOT_WS_BASE_URL",
  "LOCAL_ENABLE_TELEGRAM",
  "LOCAL_CANDLE_BOOTSTRAP_DAYS",
  "LOCAL_STARTUP_TIMEOUT_SECONDS",
];

const PORT_CONFIGURATION = [
  { key: "WEB_PORT", service: "web" },
  { key: "API_PORT", service: "api" },
  { key: "POSTGRES_PORT", service: "db" },
];

const HTTP_CONFIGURATION_KEYS = [
  "NEXT_PUBLIC_API_BASE_URL",
  "WEB_ORIGIN",
  "BINANCE_SPOT_BASE_URL",
];

const TELEGRAM_CONFIGURATION_KEYS = [
  "TELEGRAM_BOT_USERNAME",
  "TELEGRAM_BOT_TOKEN",
];

const AVAILABLE_PROFILE_NAMES = ["market", "telegram", "historical-analysis"];

const SERVICE_DEFINITIONS = [
  { name: "db", label: "Database", kind: "healthy", required: true },
  { name: "api", label: "API", kind: "healthy", required: true },
  { name: "web", label: "Web", kind: "healthy", required: true },
  {
    name: "api-prepare",
    label: "API preparation",
    kind: "completed",
    required: true,
  },
  {
    name: "db-migrate",
    label: "Migrations",
    kind: "completed",
    required: true,
  },
  {
    name: "market-catalog-init",
    label: "Market catalogue",
    kind: "completed",
    required: true,
  },
  {
    name: "candle-bootstrap-init",
    label: "Candle bootstrap",
    kind: "completed",
    required: true,
  },
  {
    name: "market-stream",
    label: "Market stream",
    kind: "running",
    required: true,
  },
  {
    name: "telegram-updates",
    label: "Telegram updates",
    kind: "running",
    profile: "telegram",
  },
  {
    name: "notification-worker",
    label: "Notification worker",
    kind: "running",
    profile: "telegram",
  },
  {
    name: "signal-telegram-dispatcher",
    label: "Signal dispatcher",
    kind: "running",
    profile: "telegram",
  },
  {
    name: "historical-analysis-worker",
    label: "Historical analysis worker",
    kind: "running",
    profile: "historical-analysis",
    missingStatus: "failed",
  },
];

function hasValue(value) {
  return typeof value === "string" && value.trim() !== "";
}

function parseEnvFile(contents) {
  const values = Object.create(null);
  const errors = [];
  const lines = contents.split(/\r?\n/);

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();

    if (trimmedLine === "" || trimmedLine.startsWith("#")) {
      return;
    }

    const match = trimmedLine.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);

    if (match === null) {
      errors.push(`.env line ${index + 1} is malformed; use KEY=VALUE.`);
      return;
    }

    let value = match[2].trim();

    if (value.startsWith("'") || value.startsWith('"')) {
      const quote = value[0];

      if (value.length < 2 || !value.endsWith(quote)) {
        errors.push(`.env line ${index + 1} has an unmatched quote.`);
        return;
      }

      value = value.slice(1, -1);
    }

    values[match[1]] = value;
  });

  return { values, errors };
}

function resolveConfiguration(fileValues) {
  const values = { ...fileValues };
  const overrideKeys = new Set([
    ...REQUIRED_CONFIGURATION_KEYS,
    ...TELEGRAM_CONFIGURATION_KEYS,
  ]);

  for (const key of overrideKeys) {
    if (process.env[key] !== undefined) {
      values[key] = process.env[key];
    }
  }

  return values;
}

function loadConfiguration() {
  if (!existsSync(ENV_PATH)) {
    return {
      values: null,
      errors: [
        ".env is missing; run pnpm dev:setup to create it from .env.example.",
      ],
    };
  }

  let contents;

  try {
    contents = readFileSync(ENV_PATH, "utf8");
  } catch {
    return {
      values: null,
      errors: [".env could not be read; check its local file permissions."],
    };
  }

  const parsed = parseEnvFile(contents);

  if (parsed.errors.length > 0) {
    return { values: null, errors: parsed.errors };
  }

  return { values: resolveConfiguration(parsed.values), errors: [] };
}

function requireConfigurationValues(values, errors) {
  for (const key of REQUIRED_CONFIGURATION_KEYS) {
    if (!hasValue(values[key])) {
      errors.push(`Set ${key} in .env.`);
    }
  }
}

function parseInteger(values, key, minimum, maximum, errors) {
  const value = values[key];

  if (!hasValue(value)) {
    return null;
  }

  if (!/^\d+$/.test(value)) {
    errors.push(`Set ${key} to an integer from ${minimum} through ${maximum}.`);
    return null;
  }

  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum) {
    errors.push(`Set ${key} to an integer from ${minimum} through ${maximum}.`);
    return null;
  }

  return parsed;
}

function validateBoolean(values, key, errors) {
  const value = values[key];

  if (!hasValue(value)) {
    return null;
  }

  if (value !== "true" && value !== "false") {
    errors.push(`Set ${key} to lowercase true or false.`);
    return null;
  }

  return value === "true";
}

function validateUrl(values, key, protocols, errors) {
  const value = values[key];

  if (!hasValue(value)) {
    return;
  }

  let parsed;

  try {
    parsed = new URL(value);
  } catch {
    errors.push(`Set ${key} to a valid ${protocols.join(" or ")} URL.`);
    return;
  }

  if (!protocols.includes(parsed.protocol) || parsed.hostname === "") {
    errors.push(`Set ${key} to a valid ${protocols.join(" or ")} URL.`);
  }

  if (
    key === "NEXT_PUBLIC_API_BASE_URL" &&
    (parsed.username !== "" || parsed.password !== "")
  ) {
    errors.push(`${key} must not contain URL credentials.`);
  }
}

function validateTelegram(values, telegramEnabled, errors) {
  const username = values.TELEGRAM_BOT_USERNAME;
  const token = values.TELEGRAM_BOT_TOKEN;

  if (hasValue(username) && !/^[A-Za-z0-9_]+$/.test(username)) {
    errors.push("Set TELEGRAM_BOT_USERNAME to letters, numbers, or underscores only.");
  }

  if (telegramEnabled && !hasValue(username)) {
    errors.push("Set TELEGRAM_BOT_USERNAME before enabling Telegram.");
  }

  if (telegramEnabled && !hasValue(token)) {
    errors.push("Set TELEGRAM_BOT_TOKEN before enabling Telegram.");
  }

  if (!telegramEnabled && hasValue(token)) {
    errors.push("Clear TELEGRAM_BOT_TOKEN or set LOCAL_ENABLE_TELEGRAM=true.");
  }
}

function validateConfiguration(values) {
  const errors = [];
  const ports = [];

  requireConfigurationValues(values, errors);

  for (const configuration of PORT_CONFIGURATION) {
    const port = parseInteger(values, configuration.key, 1, 65535, errors);

    if (port !== null) {
      ports.push({ ...configuration, port });
    }
  }

  if (ports.length === PORT_CONFIGURATION.length) {
    const uniquePorts = new Set(ports.map(({ port }) => port));

    if (uniquePorts.size !== ports.length) {
      errors.push("Set WEB_PORT, API_PORT, and POSTGRES_PORT to three distinct ports.");
    }
  }

  for (const key of HTTP_CONFIGURATION_KEYS) {
    validateUrl(values, key, ["http:", "https:"], errors);
  }

  validateUrl(values, "BINANCE_SPOT_WS_BASE_URL", ["ws:", "wss:"], errors);

  const sessionCookieSecure = values.SESSION_COOKIE_SECURE;
  if (
    hasValue(sessionCookieSecure) &&
    sessionCookieSecure !== "true" &&
    sessionCookieSecure !== "false"
  ) {
    errors.push("Set SESSION_COOKIE_SECURE to lowercase true or false.");
  }

  const telegramEnabled = validateBoolean(values, "LOCAL_ENABLE_TELEGRAM", errors);
  const candleBootstrapDays = parseInteger(
    values,
    "LOCAL_CANDLE_BOOTSTRAP_DAYS",
    35,
    180,
    errors,
  );
  const startupTimeoutSeconds = parseInteger(
    values,
    "LOCAL_STARTUP_TIMEOUT_SECONDS",
    60,
    7200,
    errors,
  );

  if (telegramEnabled !== null) {
    validateTelegram(values, telegramEnabled, errors);
  }

  return {
    errors,
    ports,
    telegramEnabled,
    candleBootstrapDays,
    startupTimeoutSeconds,
  };
}

function runCommand(command, options = {}) {
  try {
    const result = spawnSync(command[0], command.slice(1), {
      cwd: REPOSITORY_ROOT,
      encoding: "utf8",
      shell: false,
      stdio: options.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    return {
      ok: result.error === undefined && result.status === 0,
      stdout: typeof result.stdout === "string" ? result.stdout : "",
      stderr: typeof result.stderr === "string" ? result.stderr : "",
    };
  } catch {
    return { ok: false, stdout: "", stderr: "" };
  }
}

function composeCommand(profiles, args) {
  return [
    "docker",
    "compose",
    ...profiles.flatMap((profile) => ["--profile", profile]),
    ...args,
  ];
}

function parseComposeVersion(output) {
  const match = output.match(/version\s+v?(\d+)\.(\d+)(?:\.(\d+))?/i);

  if (match === null) {
    return null;
  }

  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: match[3] === undefined ? 0 : Number(match[3]),
  };
}

function parseComposeProfiles(output) {
  const lines = new Set(
    output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line !== ""),
  );

  return new Set(
    AVAILABLE_PROFILE_NAMES.filter((profile) => lines.has(profile)),
  );
}

function parseComposeServices(output) {
  const trimmedOutput = output.trim();

  if (trimmedOutput === "") {
    return [];
  }

  try {
    const parsed = JSON.parse(trimmedOutput);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    const services = [];

    for (const line of trimmedOutput.split(/\r?\n/)) {
      try {
        const parsed = JSON.parse(line);
        services.push(...(Array.isArray(parsed) ? parsed : [parsed]));
      } catch {
        return null;
      }
    }

    return services;
  }
}

function runDockerChecks() {
  const errors = [];
  const dockerVersion = runCommand(["docker", "version"]);

  if (!dockerVersion.ok) {
    errors.push(
      "Docker is unavailable; start Docker Desktop or Docker Engine and rerun the local command.",
    );
  }

  const composeVersion = runCommand(["docker", "compose", "version"]);

  if (!composeVersion.ok) {
    errors.push(
      "Docker Compose is unavailable; install Compose v2 and rerun the local command.",
    );
  } else {
    const version = parseComposeVersion(`${composeVersion.stdout}\n${composeVersion.stderr}`);

    if (
      version === null ||
      version.major < 2 ||
      (version.major === 2 && version.minor < 22)
    ) {
      errors.push(
        "Docker Compose 2.22 or newer is required for completed-service dependencies, --wait, JSON service inspection, and Compose Watch.",
      );
    }
  }

  if (errors.length > 0) {
    return { errors };
  }

  const composeConfig = runCommand(["docker", "compose", "config", "--quiet"]);

  if (!composeConfig.ok) {
    errors.push(
      "Docker Compose configuration is invalid; inspect the named environment settings and rerun the local command.",
    );
  }

  return { errors };
}

function resolveProfiles(telegramEnabled) {
  const result = runCommand(["docker", "compose", "config", "--profiles"]);

  if (!result.ok) {
    return {
      profiles: [],
      historicalAvailable: false,
      errors: [
        "Docker Compose profiles could not be resolved; inspect the local Compose configuration and rerun the command.",
      ],
    };
  }

  const availableProfiles = parseComposeProfiles(result.stdout);
  const errors = [];
  const profiles = [];

  if (!availableProfiles.has("market")) {
    errors.push("The local Compose model does not provide the required market profile.");
  } else {
    profiles.push("market");
  }

  if (telegramEnabled) {
    if (!availableProfiles.has("telegram")) {
      errors.push("Telegram is enabled but the local Compose model has no telegram profile.");
    } else {
      profiles.push("telegram");
    }
  }

  const historicalAvailable = availableProfiles.has("historical-analysis");

  if (historicalAvailable) {
    profiles.push("historical-analysis");
  }

  return { profiles, historicalAvailable, errors };
}

function inspectComposeServices(profiles) {
  const result = runCommand(
    composeCommand(profiles, ["ps", "--all", "--format", "json"]),
  );

  if (!result.ok) {
    return {
      services: null,
      errors: [
        "Docker Compose service state could not be inspected; start Docker and rerun the local command.",
      ],
    };
  }

  const services = parseComposeServices(result.stdout);

  if (services === null) {
    return {
      services: null,
      errors: [
        "Docker Compose returned an unreadable service-state response; use Compose v2 and rerun the local command.",
      ],
    };
  }

  return { services, errors: [] };
}

function isRunningComposeService(services, serviceName) {
  return services.some((service) => {
    const serviceNameFromCompose = service.Service ?? service.service;
    const state = String(service.State ?? service.state ?? "").toLowerCase();

    return (
      serviceNameFromCompose === serviceName &&
      ["running", "healthy", "up"].includes(state)
    );
  });
}

function checkPortAvailability(port) {
  return new Promise((resolveResult) => {
    const server = createServer();

    server.once("error", (error) => {
      resolveResult({ available: false, errorCode: error.code });
    });

    server.listen(port, "127.0.0.1", () => {
      server.close(() => {
        resolveResult({ available: true, errorCode: null });
      });
    });
  });
}

async function validatePorts(ports, composeServices) {
  const errors = [];

  for (const { key, service, port } of ports) {
    if (isRunningComposeService(composeServices, service)) {
      continue;
    }

    const result = await checkPortAvailability(port);

    if (!result.available) {
      if (result.errorCode === "EADDRINUSE") {
        errors.push(
          `${key} port ${port} is occupied; stop that process or change ${key}.`,
        );
      } else {
        errors.push(
          `Cannot bind ${key} on 127.0.0.1; change ${key} and rerun the local command.`,
        );
      }
    }
  }

  return errors;
}

async function loadCommandContext({ checkPorts }) {
  const configuration = loadConfiguration();

  if (configuration.values === null) {
    printErrors(configuration.errors);
    return null;
  }

  const validation = validateConfiguration(configuration.values);

  if (validation.errors.length > 0) {
    printErrors(validation.errors);
    return null;
  }

  const docker = runDockerChecks();

  if (docker.errors.length > 0) {
    printErrors(docker.errors);
    return null;
  }

  const profileSelection = resolveProfiles(validation.telegramEnabled);

  if (profileSelection.errors.length > 0) {
    printErrors(profileSelection.errors);
    return null;
  }

  let services = [];

  if (checkPorts) {
    const inspection = inspectComposeServices(profileSelection.profiles);

    if (inspection.errors.length > 0) {
      printErrors(inspection.errors);
      return null;
    }

    services = inspection.services;
    const portErrors = await validatePorts(validation.ports, services);

    if (portErrors.length > 0) {
      printErrors(portErrors);
      return null;
    }
  }

  return {
    values: configuration.values,
    ...validation,
    ...profileSelection,
    services,
  };
}

function printErrors(errors) {
  console.error("Local command failed.");

  for (const error of errors) {
    console.error(`- ${error}`);
  }
}

function printSuccess(mode, context) {
  console.log(
    mode === "setup" ? "Local core configuration is ready." : "Local preflight passed.",
  );
  console.log(`Telegram is ${context.telegramEnabled ? "enabled" : "disabled"}.`);

  if (!context.telegramEnabled) {
    console.log("");
    console.log("To test Telegram:");
    console.log("1. Set LOCAL_ENABLE_TELEGRAM=true");
    console.log("2. Set TELEGRAM_BOT_USERNAME");
    console.log("3. Set TELEGRAM_BOT_TOKEN");
  }

  console.log("");
  console.log("Selected local profiles:");
  console.log("- market (always)");
  console.log(`- telegram (${context.telegramEnabled ? "enabled" : "disabled"})`);
  console.log(
    `- historical-analysis (${context.historicalAvailable ? "enabled" : "unavailable"})`,
  );
}

function serviceName(service) {
  return service.Service ?? service.service ?? null;
}

function serviceRecordMap(services) {
  const records = new Map();

  for (const service of services) {
    const name = serviceName(service);

    if (name !== null) {
      records.set(name, service);
    }
  }

  return records;
}

function serviceExitCode(service) {
  const directExitCode = service.ExitCode ?? service.exitCode;

  if (directExitCode !== undefined && directExitCode !== null) {
    const parsed = Number(directExitCode);

    if (Number.isInteger(parsed)) {
      return parsed;
    }
  }

  const status = String(service.Status ?? service.status ?? "");
  const match = status.match(/exited\s*\((\d+)\)/i);

  return match === null ? null : Number(match[1]);
}

function normalizedServiceStatus(service, definition) {
  if (service === undefined) {
    return definition.missingStatus ?? "stopped";
  }

  const state = String(service.State ?? service.state ?? "").toLowerCase();
  const rawHealth = String(service.Health ?? service.health ?? "").toLowerCase();
  const rawStatus = String(service.Status ?? service.status ?? "").toLowerCase();
  const health = rawHealth ||
    (rawStatus.includes("unhealthy")
      ? "unhealthy"
      : rawStatus.includes("healthy")
        ? "healthy"
        : "");
  const restarting = state === "restarting" || rawStatus.includes("restarting");
  const unhealthy = health === "unhealthy" || rawStatus.includes("unhealthy");
  const starting =
    health === "starting" || state === "created" || rawStatus.includes("starting");

  if (definition.kind === "completed") {
    if (state === "exited" && serviceExitCode(service) === 0) {
      return "completed";
    }

    if (state === "exited" || state === "dead" || restarting || unhealthy) {
      return "failed";
    }

    return starting || state === "running" ? "starting" : "stopped";
  }

  if (definition.kind === "running") {
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

function buildServiceStatuses(context, services) {
  const records = serviceRecordMap(services);
  const statuses = new Map();

  for (const definition of SERVICE_DEFINITIONS) {
    if (definition.profile === "telegram" && !context.telegramEnabled) {
      statuses.set(definition.name, "disabled");
      continue;
    }

    if (
      definition.profile === "historical-analysis" &&
      !context.historicalAvailable
    ) {
      statuses.set(definition.name, "unavailable");
      continue;
    }

    statuses.set(
      definition.name,
      normalizedServiceStatus(records.get(definition.name), definition),
    );
  }

  return statuses;
}

function serviceIsEnabled(context, definition) {
  if (definition.required) {
    return true;
  }

  if (definition.profile === "telegram") {
    return context.telegramEnabled;
  }

  return definition.profile === "historical-analysis" && context.historicalAvailable;
}

function readinessFailures(context, statuses) {
  const failures = [];

  for (const definition of SERVICE_DEFINITIONS) {
    if (!serviceIsEnabled(context, definition)) {
      continue;
    }

    const status = statuses.get(definition.name);
    let ready = false;

    if (definition.kind === "completed") {
      ready = status === "completed";
    } else if (definition.kind === "healthy") {
      ready = status === "healthy";
    } else {
      ready = status === "running";
    }

    if (!ready) {
      failures.push({ label: definition.label, status });
    }
  }

  return failures;
}

function failedEnabledStatuses(context, statuses) {
  return SERVICE_DEFINITIONS.filter(
    (definition) =>
      serviceIsEnabled(context, definition) &&
      statuses.get(definition.name) === "failed",
  ).map((definition) => ({
    label: definition.label,
    status: statuses.get(definition.name),
  }));
}

function printStatus(context, statuses) {
  console.log("FreeCoinAlert local status.");
  console.log("");

  for (const definition of SERVICE_DEFINITIONS) {
    console.log(
      `${definition.label.padEnd(30, " ")} ${statuses.get(definition.name)}`,
    );
  }
}

function displayOrigin(value) {
  return new URL(value).origin;
}

function displayHealthUrl(value) {
  const healthUrl = new URL("/health", displayOrigin(value));
  return healthUrl.toString().replace(/\/$/, "");
}

function printReadiness(context, statuses) {
  console.log("FreeCoinAlert local MVP is ready.");
  console.log("");
  console.log(`Web:                         ${displayOrigin(context.values.WEB_ORIGIN)}`);
  console.log(
    `API:                         ${displayOrigin(context.values.NEXT_PUBLIC_API_BASE_URL)}`,
  );
  console.log(
    `API health:                  ${displayHealthUrl(context.values.NEXT_PUBLIC_API_BASE_URL)}`,
  );
  console.log("");

  const readinessOrder = [
    ["Database", "db"],
    ["Migrations", "db-migrate"],
    ["Market catalogue", "market-catalog-init"],
    ["Candle bootstrap", "candle-bootstrap-init"],
    ["Market stream", "market-stream"],
    ["Telegram updates", "telegram-updates"],
    ["Notification worker", "notification-worker"],
    ["Signal dispatcher", "signal-telegram-dispatcher"],
    ["Historical analysis worker", "historical-analysis-worker"],
  ];

  for (const [label, serviceNameValue] of readinessOrder) {
    console.log(
      `${`${label}:`.padEnd(30, " ")}${statuses.get(serviceNameValue)}`,
    );
  }
}

function printStartupFailure(failures = []) {
  console.error("Startup failed.");

  for (const failure of failures) {
    console.error(`- ${failure.label}: ${failure.status}`);
  }

  console.error("Run pnpm dev:status");
  console.error("Run pnpm dev:all:logs");
}

function stopChild(child) {
  try {
    if (!child.kill("SIGINT")) {
      child.kill();
    }
  } catch {
    try {
      child.kill();
    } catch {
      return;
    }
  }
}

function runChildProcess(command, options = {}) {
  return new Promise((resolveResult) => {
    let child;
    let settled = false;
    let interrupted = false;

    try {
      child = spawn(command[0], command.slice(1), {
        cwd: REPOSITORY_ROOT,
        shell: false,
        stdio: options.inherit ? "inherit" : "ignore",
        windowsHide: true,
      });
    } catch {
      resolveResult({ ok: false, interrupted: false });
      return;
    }

    const onSignal = () => {
      interrupted = true;
      stopChild(child);
    };

    const cleanup = () => {
      if (options.handleSignals) {
        process.removeListener("SIGINT", onSignal);
        process.removeListener("SIGTERM", onSignal);
      }
    };

    const finish = (ok) => {
      if (settled) {
        return;
      }

      settled = true;
      cleanup();
      resolveResult({ ok, interrupted });
    };

    if (options.handleSignals) {
      process.once("SIGINT", onSignal);
      process.once("SIGTERM", onSignal);
    }

    child.once("error", () => finish(false));
    child.once("close", (code) => finish(code === 0));
  });
}

function runComposeDown(profiles) {
  return runCommand(
    composeCommand(profiles, ["down", "--remove-orphans"]),
    { inherit: true },
  ).ok;
}

async function runPreflight(mode) {
  const context = await loadCommandContext({ checkPorts: true });

  if (context === null) {
    return 1;
  }

  printSuccess(mode, context);
  return 0;
}

async function runSetup() {
  if (existsSync(ENV_PATH)) {
    console.log("Using existing .env; it was not modified.");
  } else {
    if (!existsSync(ENV_EXAMPLE_PATH)) {
      printErrors([
        ".env.example is missing; restore the tracked local configuration template.",
      ]);
      return 1;
    }

    try {
      copyFileSync(ENV_EXAMPLE_PATH, ENV_PATH);
    } catch {
      printErrors([
        ".env could not be created from .env.example; check local file permissions.",
      ]);
      return 1;
    }

    console.log("Created .env from .env.example.");
  }

  console.log("");
  return runPreflight("setup");
}

async function runUp(args) {
  if (args.length > 1 || (args.length === 1 && args[0] !== "--detach")) {
    printErrors(["Usage: pnpm dev:all or pnpm dev:all:detached."]);
    return 1;
  }

  const detached = args.length === 1;
  const context = await loadCommandContext({ checkPorts: true });

  if (context === null) {
    return 1;
  }

  const startup = await runChildProcess(
    composeCommand(context.profiles, [
      "up",
      "--build",
      "--detach",
      "--wait",
      "--wait-timeout",
      String(context.startupTimeoutSeconds),
    ]),
    { handleSignals: true },
  );

  if (startup.interrupted) {
    const stopped = runComposeDown(context.profiles);

    if (!stopped) {
      printErrors(["The local stack could not be stopped cleanly after interruption."]);
      return 1;
    }

    return 130;
  }

  const inspection = inspectComposeServices(context.profiles);

  if (inspection.errors.length > 0) {
    printStartupFailure();
    return 1;
  }

  const statuses = buildServiceStatuses(context, inspection.services);
  const failures = readinessFailures(context, statuses);

  if (!startup.ok || failures.length > 0) {
    printStartupFailure(failures);
    return 1;
  }

  printReadiness(context, statuses);

  if (detached) {
    return 0;
  }

  const watch = await runChildProcess(
    composeCommand(context.profiles, ["up", "--watch"]),
    { handleSignals: true, inherit: true },
  );

  if (watch.interrupted) {
    const stopped = runComposeDown(context.profiles);

    if (!stopped) {
      printErrors(["The local stack could not be stopped cleanly after interruption."]);
      return 1;
    }

    return 0;
  }

  return watch.ok ? 0 : 1;
}

async function runStatus() {
  const context = await loadCommandContext({ checkPorts: false });

  if (context === null) {
    return 1;
  }

  const inspection = inspectComposeServices(context.profiles);

  if (inspection.errors.length > 0) {
    printErrors(inspection.errors);
    return 1;
  }

  const statuses = buildServiceStatuses(context, inspection.services);
  printStatus(context, statuses);

  return failedEnabledStatuses(context, statuses).length > 0 ? 1 : 0;
}

async function runLogs() {
  const context = await loadCommandContext({ checkPorts: false });

  if (context === null) {
    return 1;
  }

  const logs = await runChildProcess(
    composeCommand(context.profiles, ["logs", "--follow"]),
    { handleSignals: true, inherit: true },
  );

  if (logs.interrupted) {
    return 0;
  }

  if (!logs.ok) {
    printErrors(["Logs could not be followed; run pnpm dev:status."]);
    return 1;
  }

  return 0;
}

async function runDown() {
  const context = await loadCommandContext({ checkPorts: false });

  if (context === null) {
    return 1;
  }

  return runComposeDown(context.profiles) ? 0 : 1;
}

function readResetConfirmation() {
  return new Promise((resolveResult) => {
    let input = "";
    let settled = false;

    const cleanup = () => {
      process.stdin.removeListener("data", onData);
      process.stdin.removeListener("end", onEnd);
      process.stdin.pause();
    };

    const finish = (value) => {
      if (settled) {
        return;
      }

      settled = true;
      cleanup();
      resolveResult(value);
    };

    const onData = (chunk) => {
      input += chunk.toString();
      const lineBreak = input.search(/[\r\n]/);

      if (lineBreak !== -1) {
        finish(input.slice(0, lineBreak));
      }
    };

    const onEnd = () => finish(input);

    process.stdin.setEncoding("utf8");
    process.stdin.on("data", onData);
    process.stdin.once("end", onEnd);
    process.stdin.resume();
  });
}

async function runReset(args) {
  if (args.length > 1 || (args.length === 1 && args[0] !== "--force")) {
    printErrors(["Usage: pnpm dev:reset or pnpm dev:reset:force."]);
    return 1;
  }

  const force = args.length === 1;
  const context = await loadCommandContext({ checkPorts: false });

  if (context === null) {
    return 1;
  }

  if (!force) {
    if (!process.stdin.isTTY || !process.stdout.isTTY) {
      printErrors([
        "Reset requires an interactive terminal or the explicit --force flag.",
      ]);
      return 1;
    }

    console.log(
      "This permanently deletes the local PostgreSQL database and dependency volumes.",
    );
    console.log("Type RESET to continue:");

    const confirmation = await readResetConfirmation();

    if (confirmation !== "RESET") {
      console.log("Reset cancelled.");
      return 0;
    }
  }

  const result = runCommand(
    composeCommand(context.profiles, ["down", "--volumes", "--remove-orphans"]),
    { inherit: true },
  );

  return result.ok ? 0 : 1;
}

async function main() {
  const [command, ...args] = process.argv.slice(2);

  if (command === "setup" && args.length === 0) {
    return runSetup();
  }

  if (command === "preflight" && args.length === 0) {
    return runPreflight("preflight");
  }

  if (command === "up") {
    return runUp(args);
  }

  if (command === "status" && args.length === 0) {
    return runStatus();
  }

  if (command === "logs" && args.length === 0) {
    return runLogs();
  }

  if (command === "down" && args.length === 0) {
    return runDown();
  }

  if (command === "reset") {
    return runReset(args);
  }

  console.error(
    "Usage: node scripts/local-dev.mjs <setup|preflight|up [--detach]|logs|status|down|reset [--force]>",
  );
  return 1;
}

main()
  .then((exitCode) => {
    process.exitCode = exitCode;
  })
  .catch(() => {
    printErrors([
      "The local command could not complete; inspect the named configuration and rerun it.",
    ]);
    process.exitCode = 1;
  });
