# Services

The normal market stream, Telegram poller, notification worker, and historical-analysis worker run from `apps/api`. The approved E2E boundary also contains the standalone [`e2e-provider-simulator`](e2e-provider-simulator), which is built only by the isolated E2E Compose overlay and has no production role.

Use [Operations](../docs/OPERATIONS.md) for entry points and profiles, [Testing](../docs/TESTING.md) for the isolated environment contract, and [Architecture](../docs/ARCHITECTURE.md) for process ownership.
