# FreeCoinAlert

FreeCoinAlert is a web application for configurable cryptocurrency market alerts.

Users connect Telegram, subscribe to platform-provided signals, or create validated custom conditions. The platform consumes live Binance market data, evaluates alerts, and sends Telegram notifications. It also stores its own closed one-minute candles so future historical strategy analysis can use internal data instead of querying Binance for every customer request.

> Project status: frontend and API foundations are initialized, including the minimal browser registration, sign-in, session-restoration, sign-out, Telegram connection, and one-time price-alert flows. Live market processing and a dedicated verification pass remain pending.

## Product Goal

The first release should allow a user to:

1. Create an account and sign in.
2. Connect a private Telegram chat through the FreeCoinAlert bot.
3. Browse available signal templates.
4. Create a custom alert using supported conditions.
5. Select a market, symbol, timeframe, evaluation mode, cooldown, and destination.
6. Receive a reliable Telegram notification when the condition triggers.
7. Review active alerts, triggered events, and delivery state.

FreeCoinAlert provides informational alerts only. The MVP does not execute trades, hold funds, request customer exchange API keys, or provide financial advice.

## Initial Alert Types

Planned MVP conditions include:

- Price above or below a threshold
- Price crossing a threshold
- Percentage price movement
- RSI above or below a threshold
- MACD bullish or bearish crossover
- EMA crossover
- Volume spike

Immediate price alerts may evaluate from live ticker or trade events.

Indicator alerts should initially evaluate only after the selected candle closes. This prevents temporary intrabar indicator movement from sending misleading alerts.

## Architecture Direction

```text
                    Web application
                           |
                    Backend API
                           |
          +----------------+----------------+
          |                                 |
    Alert definitions                 Telegram linking
          |                                 |
          +---------------+-----------------+
                          |
                  Market-data process
                          |
                 Binance WebSocket
                          |
            +-------------+-------------+
            |                           |
     Real-time prices              Closed 1m candles
            |                           |
      Price alerts                Persist to database
                                        |
                              Aggregate larger timeframes
                               5m / 15m / 1h / 4h / 1d
                                        |
                                Strategy evaluation
                                        |
                                  Alert events
                                        |
                              Notification outbox
                                        |
                               Telegram worker

Daily reconciliation
        |
Detect missing 1m candles
        |
Fetch and upsert only missing Binance REST ranges
```

The system should begin as a modular monolith. Separate processes may be used for lifecycle and reliability, but independent microservices are deferred until measurements justify them.

## Market-Data Principles

### WebSocket First

Binance WebSocket data is the primary source for current prices and one-minute kline events.

The application should:

- Maintain shared exchange connections rather than one connection per user.
- Persist one-minute candles only after they are confirmed closed.
- Reconnect safely and detect gaps after outages.
- Make ingestion idempotent.
- Avoid blocking real-time processing with historical work.

### Canonical One-Minute Candles

Closed one-minute candles are the canonical stored market-data interval.

Larger timeframes are derived internally using UTC-aligned boundaries. Live and historical aggregation must use the same implementation.

### Daily Reconciliation

The daily job is not the primary candle source. It should find missing timestamps, request only missing ranges through Binance REST, respect rate limits, and upsert recovered candles.

### Historical Backfill

A separate, controlled backfill process will populate older history when a symbol or date range is needed. It must run independently from live alert processing.

## Shared Strategy Engine

Live alerts and future historical analysis must use the same strategy implementation.

```text
Live alert engine --------+
                          +--> strategy-core
Historical analysis ------+
```

The shared core should contain:

- Candle aggregation
- RSI, EMA, MACD, and volume calculations
- Comparison and crossover operators
- Logical `AND` and `OR`
- Rule validation
- Strategy-template versions
- Deterministic evaluation

This prevents live signals and historical results from disagreeing because of duplicated implementations.

## Custom Signals

Users must not submit executable Python or JavaScript.

Custom signals should use a constrained, validated, versioned rule format.

Example:

```json
{
  "schemaVersion": 1,
  "type": "CROSS_ABOVE",
  "left": {
    "type": "MACD_LINE",
    "fastPeriod": 12,
    "slowPeriod": 26,
    "signalPeriod": 9
  },
  "right": {
    "type": "MACD_SIGNAL",
    "fastPeriod": 12,
    "slowPeriod": 26,
    "signalPeriod": 9
  }
}
```

The backend must validate supported markets, symbols, timeframes, indicators, parameter ranges, rule depth, and computational complexity.

## Signal Templates and Versioning

The platform may publish reusable templates such as:

- MACD Bullish Crossover
- MACD Bearish Crossover
- RSI Oversold
- RSI Overbought
- EMA Trend Change
- Unusual Volume

Templates must be versioned. Existing subscriptions remain pinned to their selected version unless the user explicitly upgrades.

## Telegram Linking

The recommended flow is:

1. The authenticated user selects **Connect Telegram**.
2. The backend creates a short-lived, single-use token.
3. The browser opens the Telegram bot using a deep link.
4. The user starts the bot.
5. Telegram returns the token to the backend.
6. The backend links the chat to the authenticated account.
7. The bot sends confirmation.

Users should not manually enter Telegram chat IDs.

## Reliable Notifications

Alert evaluation must not send Telegram messages directly.

```text
Condition triggered
      |
Create alert event
      |
Create notification-outbox record
      |
Commit transaction
      |
Telegram worker sends and records delivery
```

Every logical trigger needs a stable deduplication key so retries, reconnects, repeated candles, and service restarts do not create duplicate messages.

## Future Historical Analysis

Historical analysis will use the internal candle database rather than querying Binance per user.

A signal alone does not have a meaningful win rate. A complete strategy must define entry, execution, exit, stop loss, take profit, maximum holding time, fees, slippage, and position sizing.

Future reports may include:

- Number of trades
- Win rate
- Total return
- Maximum drawdown
- Profit factor
- Average profit and loss
- Holding duration
- Risk-adjusted metrics when assumptions justify them

Historical calculations must prevent look-ahead bias. A signal confirmed at candle close cannot execute using that same candle's earlier opening price.

## Proposed Repository Structure

```text
FreeCoinAlert/
├── apps/
│   ├── web/
│   └── api/
├── services/
│   ├── market-data/
│   └── notifications/
├── packages/
│   ├── shared/
│   └── strategy-core/
├── docs/
│   ├── user-stories/
│   ├── README.md
│   ├── PRODUCT.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATABASE.md
│   ├── SECURITY.md
│   ├── MARKET_DATA.md
│   ├── ALERTS.md
│   ├── TELEGRAM.md
│   ├── STRATEGIES.md
│   ├── BACKTESTING.md
│   ├── OPERATIONS.md
│   ├── OBSERVABILITY.md
│   ├── CONCERNS.md
│   └── CONTINUITY.md
├── AGENTS.md
└── README.md
```

Folders should be introduced only when an approved implementation issue requires them.

## Proposed Technology Direction

The current direction is provider-independent:

- Next.js and TypeScript for the frontend
- Python and FastAPI for the API and processing
- PostgreSQL for durable application and candle data
- Python `asyncio` for initial background processing
- Telegram Bot API for notifications
- Docker and Docker Compose for local development

These are not final until accepted through implementation issues.

Redis, Celery, Kafka, Kubernetes, and independent microservices are intentionally deferred.

## Delivery Plan

### Phase 1: Functional Alert MVP

- Authentication
- Telegram connection
- Supported coin list
- Price-above and price-below alerts
- Telegram delivery
- Alert management and history

### Phase 2: Candle and Indicator Alerts

- One-minute WebSocket candle storage
- UTC timeframe aggregation
- RSI, MACD, EMA crossover, and volume spike
- Closed-candle evaluation
- Daily gap reconciliation

### Phase 3: Custom Strategy Builder

- Versioned rule format
- `AND` and `OR` conditions
- Multiple indicators
- Cooldown settings
- Rule complexity limits

### Phase 4: Historical Analysis

- Controlled historical backfill
- Entry and exit definitions
- Fees and slippage
- Performance metrics and reports

## Documentation

Start with [`docs/README.md`](docs/README.md) for the documentation catalog and reading order.

All contributors and AI agents must follow [`AGENTS.md`](AGENTS.md).

Current work is tracked in GitHub Issues. Do not create local ticket files.

## Development

The default integrated local environment uses Docker Compose v2, Docker, Node.js `24.18.0`, and pnpm `11.4.0`. Before the first startup, copy the safe local configuration:

```bash
cp .env.example .env
pnpm dev
```

In PowerShell:

```powershell
Copy-Item .env.example .env
pnpm dev
```

After a later dedicated verification pass succeeds, the local endpoints are expected to be:

```text
Frontend:   http://localhost:3000
API:        http://localhost:8000
API docs:   http://localhost:8000/docs
PostgreSQL: localhost:5432
```

Manage the stack with `pnpm dev:status`, `pnpm dev:logs`, and `pnpm dev:down`. `pnpm dev:reset` permanently deletes the local PostgreSQL volume and all of its data. Access the local database without a host-installed client with:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

`.env` is ignored by Git. The example PostgreSQL password is only for isolated local development and must never be used in production. Changing PostgreSQL initialization values after its volume exists does not recreate the existing database automatically.

Direct component commands remain available when intentionally running a component outside Compose: `pnpm dev:web` for the frontend and `pnpm dev:api` after `uv sync --project apps/api` for the API.

The stack provides the frontend, API process-health endpoint, and a local PostgreSQL server. Browser-session authentication, Telegram connection, and the one-time price-alert UI are implemented. Run a dedicated verification pass only when requested by the maintainer.

## Disclaimer

FreeCoinAlert is intended to provide informational market alerts and historical analysis. Cryptocurrency trading involves substantial risk. Alerts and historical results do not guarantee future performance, and users remain responsible for their own decisions.
