#!/usr/bin/env bash
# Validate production deployment config for issues that caused prior incidents.
#
# Bind mount policy:
# - Named Docker volumes are allowed for persistent container-managed data:
#   cv_data, minio_data, postgres_data.
# - Host bind mounts are intentionally narrow and data/config-only:
#   ./user_cv -> /winning-cv/user_cv
#   ./cookies -> /winning-cv/cookies
#   ./init-db -> /docker-entrypoint-initdb.d (read-only)
#   ./nginx/frontend.conf -> /etc/nginx/conf.d/default.conf (read-only)
# - Source-code bind mounts into packaged app paths are forbidden in production
#   because they can mask image contents (e.g. ./api -> /winning-cv/api).
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

fail() { echo "❌ $*" >&2; exit 1; }
pass() { echo "✅ $*"; }

command -v docker >/dev/null || fail "docker not found"
[ -f "$COMPOSE_FILE" ] || fail "compose file not found: $COMPOSE_FILE"

docker compose -f "$COMPOSE_FILE" config --format json > "$TMP_JSON"

python3 - "$TMP_JSON" <<'PY'
import json
import sys
from pathlib import Path

compose_path = Path(sys.argv[1])
config = json.loads(compose_path.read_text())
repo = Path.cwd().resolve()
errors = []

allowed_bind_sources = {
    "user_cv": "/winning-cv/user_cv",
    "cookies": "/winning-cv/cookies",
    "init-db": "/docker-entrypoint-initdb.d",
    "nginx/frontend.conf": "/etc/nginx/conf.d/default.conf",
}
allowed_named_volumes = {"cv_data", "minio_data", "postgres_data"}
for required in sorted(allowed_named_volumes):
    if required not in config.get("volumes", {}):
        errors.append(f"missing named volume: {required}")

for service, svc in sorted(config.get("services", {}).items()):
    for volume in svc.get("volumes") or []:
        vtype = volume.get("type")
        source = str(volume.get("source", ""))
        target = str(volume.get("target", ""))
        if vtype == "volume":
            if source not in allowed_named_volumes:
                errors.append(f"{service}: unexpected named volume {source!r} -> {target}")
            continue
        if vtype != "bind":
            errors.append(f"{service}: unsupported volume type {vtype!r} for {source!r} -> {target}")
            continue

        source_path = Path(source).resolve()
        try:
            rel = source_path.relative_to(repo)
        except ValueError:
            errors.append(f"{service}: bind source outside repo is not allowed: {source} -> {target}")
            continue

        rel_str = rel.as_posix()
        rel_key = rel.parts[0] if rel.parts else "."
        expected_target = allowed_bind_sources.get(rel_str) or allowed_bind_sources.get(rel_key)
        if expected_target is None:
            errors.append(f"{service}: forbidden production bind mount ./{rel} -> {target}")
            continue
        if target != expected_target:
            errors.append(f"{service}: ./{rel_str} may only mount to {expected_target}, not {target}")
        if rel_str in {"init-db", "nginx/frontend.conf"} and not volume.get("read_only", False):
            errors.append(f"{service}: ./{rel_str} bind mount must be read-only")

frontend = config.get("services", {}).get("frontend", {})
ports = frontend.get("ports") or []
if not any(str(p.get("published")) == "13001" and str(p.get("target")) == "80" for p in ports):
    errors.append("frontend must publish host port 13001 to container port 80")

# Guard against reintroducing the old wrong health/deploy port in live deployment files.
forbidden_port = "13" + "000"
scan_roots = [Path("docker-compose.yml"), Path("scripts"), Path(".github/workflows")]
for root in scan_roots:
    if not root.exists():
        continue
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for path in files:
        if path.name == "validate_prod_config.sh":
            continue
        if path.suffix not in {".sh", ".yml", ".yaml"} and path.name != "docker-compose.yml":
            continue
        text = path.read_text(errors="ignore")
        if forbidden_port in text:
            errors.append(f"{path}: forbidden production health/deploy port {forbidden_port} found")

if errors:
    print("Production config validation failed:", file=sys.stderr)
    for error in errors:
        print(f" - {error}", file=sys.stderr)
    sys.exit(1)

print("Production config validation passed")
PY

pass "production compose bind mounts and health ports are safe"
