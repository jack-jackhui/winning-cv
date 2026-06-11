# WinningCV Production Operations

## Production smoke test

Run from the deployment directory on `azure-vm` after pulling a new release:

```bash
./scripts/prod_smoke_check.sh
```

The smoke check validates frontend/API health, container health, queue failures, and a lightweight worker queue task.

## Monitoring

Run manually:

```bash
./scripts/prod_monitor.sh
```

Recommended cron on `azure-vm`:

```cron
*/5 * * * * cd /path/to/winning-cv && ./scripts/prod_monitor.sh >> logs/prod_monitor.log 2>&1
```

Optional knobs: `FRONTEND_URL`, `MAX_PENDING`, `MAX_FAILED_24H`, `MIN_FREE_PCT`, `ALERT_WEBHOOK`.

## Queue model

Job searches are queued into Postgres `task_queue` by default and processed by `winning-cv-worker`.
The API still keeps `search_tasks` updated so the frontend can resume progress after refresh.
If the queue is unavailable in local development, the API falls back to its in-process thread pool.
