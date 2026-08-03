import { copyFileSync, existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
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
  parseInteger(values, "LOCAL_CANDLE_BOOTSTRAP_DAYS", 35, 180, errors);
  parseInteger(values, "LOCAL_STARTUP_TIMEOUT_SECONDS", 60, 7200, errors);

  if (telegramEnabled !== null) {
    validateTelegram(values, telegramEnabled, errors);
  }

  return { errors, ports, telegramEnabled };
}

function runCommand(command) {
  try {
    const result = spawnSync(command[0], command.slice(1), {
      cwd: REPOSITORY_ROOT,
      encoding: "utf8",
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    return {
      ok: result.error === undefined && result.status === 0,
      stdout: result.stdout ?? "",
      stderr: result.stderr ?? "",
    };
  } catch {
    return { ok: false, stdout: "", stderr: "" };
  }
}

function composeVersionMajor(output) {
  const match = output.match(/version\s+v?(\d+)\.\d+/i);
  return match === null ? null : Number(match[1]);
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

function runDockerChecks() {
  const errors = [];
  const dockerVersion = runCommand(["docker", "version"]);

  if (!dockerVersion.ok) {
    errors.push(
      "Docker is unavailable; start Docker Desktop or Docker Engine and rerun pnpm dev:preflight.",
    );
  }

  const composeVersion = runCommand(["docker", "compose", "version"]);

  if (!composeVersion.ok) {
    errors.push(
      "Docker Compose is unavailable; install Compose v2 and rerun pnpm dev:preflight.",
    );
  } else {
    const major = composeVersionMajor(`${composeVersion.stdout}\n${composeVersion.stderr}`);

    if (major === null || major < 2) {
      errors.push(
        "Docker Compose v2 is required for completed-service dependencies, --wait, and JSON service inspection.",
      );
    }
  }

  if (errors.length > 0) {
    return { errors, services: [] };
  }

  const composeConfig = runCommand(["docker", "compose", "config", "--quiet"]);

  if (!composeConfig.ok) {
    errors.push(
      "Docker Compose configuration is invalid; inspect the named environment settings and rerun pnpm dev:preflight.",
    );
    return { errors, services: [] };
  }

  const composePs = runCommand(["docker", "compose", "ps", "--format", "json"]);

  if (!composePs.ok) {
    errors.push(
      "Docker Compose service state could not be inspected; start Docker and rerun pnpm dev:preflight.",
    );
    return { errors, services: [] };
  }

  const services = parseComposeServices(composePs.stdout);

  if (services === null) {
    errors.push(
      "Docker Compose returned an unreadable service-state response; use Compose v2 and rerun pnpm dev:preflight.",
    );
    return { errors, services: [] };
  }

  return { errors, services };
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
          `Cannot bind ${key} on 127.0.0.1; change ${key} and rerun pnpm dev:preflight.`,
        );
      }
    }
  }

  return errors;
}

function printErrors(errors) {
  console.error("Local preflight failed.");

  for (const error of errors) {
    console.error(`- ${error}`);
  }

  console.error("Fix the listed items and rerun pnpm dev:preflight.");
}

function printSuccess(mode, telegramEnabled) {
  console.log(
    mode === "setup" ? "Local core configuration is ready." : "Local preflight passed.",
  );
  console.log(`Telegram is ${telegramEnabled ? "enabled" : "disabled"}.`);

  if (!telegramEnabled) {
    console.log("");
    console.log("To test Telegram:");
    console.log("1. Set LOCAL_ENABLE_TELEGRAM=true");
    console.log("2. Set TELEGRAM_BOT_USERNAME");
    console.log("3. Set TELEGRAM_BOT_TOKEN");
  }

  console.log("");
  console.log("Selected local profiles:");
  console.log("- market (always)");
  console.log(`- telegram (${telegramEnabled ? "enabled" : "disabled"})`);
  console.log("- historical-analysis (future conditional)");
}

async function runPreflight(mode) {
  const configuration = loadConfiguration();

  if (configuration.values === null) {
    printErrors(configuration.errors);
    return 1;
  }

  const validation = validateConfiguration(configuration.values);

  if (validation.errors.length > 0) {
    printErrors(validation.errors);
    return 1;
  }

  const docker = runDockerChecks();

  if (docker.errors.length > 0) {
    printErrors(docker.errors);
    return 1;
  }

  const portErrors = await validatePorts(validation.ports, docker.services);

  if (portErrors.length > 0) {
    printErrors(portErrors);
    return 1;
  }

  printSuccess(mode, validation.telegramEnabled);
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

async function main() {
  const command = process.argv[2];

  if (command === "setup") {
    return runSetup();
  }

  if (command === "preflight") {
    return runPreflight("preflight");
  }

  console.error("Usage: node scripts/local-dev.mjs <setup|preflight>");
  return 1;
}

main()
  .then((exitCode) => {
    process.exitCode = exitCode;
  })
  .catch(() => {
    printErrors([
      "The local setup/preflight script could not complete; inspect the named configuration and rerun it.",
    ]);
    process.exitCode = 1;
  });
