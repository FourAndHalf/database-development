#!/bin/bash
# scripts/sync_eval_data_from_rds.sh
#
# Pull a full data dump from the production AWS RDS Postgres (read-only)
# and, optionally, load it into the local dev Postgres (nexus-pg) so the
# golden dataset / eval harness under eval/ can sample real production
# traffic (requests, request_retrievals, conversations, messages) instead
# of the thin local dataset.
#
# Two explicit steps, never chained automatically:
#   ./scripts/sync_eval_data_from_rds.sh --dump
#   ./scripts/sync_eval_data_from_rds.sh --load data/rds_dumps/rds_full_<timestamp>.sql
#
# --dump only ever runs `pg_dump` (read-only) against RDS_DATABASE_URL.
# --load only ever writes to the LOCAL nexus-pg container, and requires
# you to name the exact dump file — nothing is auto-selected.
#
# NOTE: a full dump includes users.email and users.password_hash (hashed,
# but still real user data). Review the dump before loading it locally.

set -euo pipefail

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DUMP_DIR="data/rds_dumps"
LOCAL_CONTAINER="nexus-pg"
LOCAL_DB="nexus_db"
LOCAL_USER="nexus"

usage() {
    echo "Usage:"
    echo "  $0 --dump                 Dump the full RDS database to ${DUMP_DIR}/"
    echo "  $0 --load <dump-file.sql> Load a dump file into the local ${LOCAL_CONTAINER} container"
    exit 1
}

do_dump() {
    if [ -z "${RDS_DATABASE_URL:-}" ]; then
        echo "Error: RDS_DATABASE_URL is not set (expected in .env)." >&2
        exit 1
    fi

    mkdir -p "${DUMP_DIR}"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DUMP_FILE="${DUMP_DIR}/rds_full_${TIMESTAMP}.sql"

    echo "Dumping production RDS database (read-only) to ${DUMP_FILE}..."
    pg_dump --no-owner --no-privileges "${RDS_DATABASE_URL}" > "${DUMP_FILE}"

    echo "Dump complete: ${DUMP_FILE}"
    echo ""
    echo "Tables included in the dump:"
    grep -E '^COPY public\.' "${DUMP_FILE}" | sed -E 's/^COPY public\.([a-zA-Z_]+).*/  \1/'
    echo ""
    echo "Review the dump before loading it locally — it includes users.email and users.password_hash."
    echo "To load: $0 --load ${DUMP_FILE}"
}

do_load() {
    DUMP_FILE="${1:-}"
    if [ -z "${DUMP_FILE}" ] || [ ! -f "${DUMP_FILE}" ]; then
        echo "Error: pass an existing dump file, e.g. --load ${DUMP_DIR}/rds_full_20260725_120000.sql" >&2
        exit 1
    fi

    if ! docker ps --format '{{.Names}}' | grep -qx "${LOCAL_CONTAINER}"; then
        echo "Error: local container '${LOCAL_CONTAINER}' is not running." >&2
        exit 1
    fi

    echo "Loading ${DUMP_FILE} into local container '${LOCAL_CONTAINER}' (db: ${LOCAL_DB})..."
    docker exec -i "${LOCAL_CONTAINER}" psql -U "${LOCAL_USER}" -d "${LOCAL_DB}" -f - < "${DUMP_FILE}"
    echo "Load complete."
}

case "${1:-}" in
    --dump)
        do_dump
        ;;
    --load)
        do_load "${2:-}"
        ;;
    *)
        usage
        ;;
esac
