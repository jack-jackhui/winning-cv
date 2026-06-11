# WinningCV Production Hardening

## Production monitor cron

Production uses `scripts/prod_monitor.sh` for health checks and `scripts/prod_monitor_cron.sh` as the cron-safe wrapper.

Recommended production install:

```bash
cd /home/azureuser/winning-cv
./scripts/install_prod_monitor_cron.sh
```

Default schedule: every 5 minutes.

The wrapper:
- writes logs to `logs/prod_monitor_cron.log`
- prevents overlapping monitor runs with `flock`
- sends Telegram alerts only on failure when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are already configured in `.env` or the environment
- rate-limits failure alerts with `ALERT_COOLDOWN_SECONDS` (default: 3600 seconds)

If Telegram env vars are not present, the monitor still runs and logs a clear `alert delivery skipped` line; credentials should not be invented or committed.

## Production bind mount policy

Production images must contain application source code. Host bind mounts must not mask packaged image code.

Allowed production volumes:
- Named volumes:
  - `cv_data` → `/winning-cv/customised_cv`
  - `minio_data` → `/data`
  - `postgres_data` → `/var/lib/postgresql/data`
- Narrow host bind mounts:
  - `./user_cv` → `/winning-cv/user_cv`
  - `./cookies` → `/winning-cv/cookies`
  - `./init-db` → `/docker-entrypoint-initdb.d` (read-only)

Forbidden examples:
- `./api:/winning-cv/api`
- `./frontend:/winning-cv/frontend`
- `.:/winning-cv`
- any bind mount from source-code directories into packaged app paths

Run the guard locally or in CI:

```bash
./scripts/validate_prod_config.sh
```

The guard also fails if the old wrong production health/deploy port `13000` appears in compose, scripts, or workflows. Production frontend health checks should use host port `13001`.
