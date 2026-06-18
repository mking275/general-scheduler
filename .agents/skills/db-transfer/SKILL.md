# db-transfer
# name: db-transfer
# description: >
#   Transfer data between FarmAgent dev (farmagent-dev-sandbox) and prod
#   (fruit-scout-production) Cloud SQL databases via GCS CSV export/import.
#   Use for: seeding prod staging data from dev, backfilling dev from prod,
#   or migrating any table between environments. Requires gcloud CLI with
#   access to both GCP projects.

## Overview

FarmAgent runs two Cloud SQL PostgreSQL instances:

| Environment | GCP Project | Instance | User | DB |
|---|---|---|---|---|
| **Dev** | `farmagent-dev-sandbox` | `postgres-sandbox` | `postgres` | `production` |
| **Prod** | `fruit-scout-production` | `postgres-prod` | `operation_user` | `production` |

**Transfer bucket**: `gs://farmagent-dev-sandbox-db-migration/transfers/`

The transfer method is **GCS CSV export → import** because:
- The prod VM service account has no IAM access to the dev Cloud SQL instance (403)
- Direct piping via cloud-sql-proxy requires both projects to be accessible from the same host
- GCS export/import is fully server-side within GCP — no data hits the desktop

---

## Usage

### Step 1 — Export tables from source instance

Cloud SQL only allows one export operation at a time. Run exports sequentially.

```bash
TRANSFER_ID="transfers/$(date +%Y%m%d-%H%M%S)-<description>"
BUCKET="gs://farmagent-dev-sandbox-db-migration"
EXPORT_PATH="$BUCKET/$TRANSFER_ID"

# Export from DEV
gcloud sql export csv postgres-sandbox \
  "$EXPORT_PATH/<table_name>.csv" \
  --project=farmagent-dev-sandbox \
  --database=production \
  --query="SELECT col1, col2, ... FROM schema.table_name [WHERE ...]"

# Wait for completion before starting next export:
gcloud sql operations wait <operation_id> --project=farmagent-dev-sandbox
```

To export from **PROD** instead:
```bash
gcloud sql export csv postgres-prod \
  "$EXPORT_PATH/<table_name>.csv" \
  --project=fruit-scout-production \
  --database=production \
  --query="SELECT col1, col2, ... FROM schema.table_name"
```

> **IMPORTANT**: Always use an explicit `SELECT` with column names — never `SELECT *`.
> Column order must exactly match the target table's column order for the import step.

---

### Step 2 — Wait for all exports to complete

```bash
# Check status of a running operation
gcloud sql operations describe <operation_id> --project=farmagent-dev-sandbox

# Or wait synchronously
gcloud sql operations wait <operation_id> --project=farmagent-dev-sandbox --timeout=600
```

Verify the files exist:
```bash
gcloud storage ls "$EXPORT_PATH/"
```

---

### Step 3 — Grant prod Cloud SQL service account read access to the bucket

This is required once. The prod Cloud SQL SA needs `storage.objectViewer` on the migration bucket.

```bash
# Get prod Cloud SQL service account
PROD_SA=$(gcloud sql instances describe postgres-prod \
  --project=fruit-scout-production \
  --format="value(serviceAccountEmailAddress)")

# Grant access
gcloud storage buckets add-iam-policy-binding gs://farmagent-dev-sandbox-db-migration \
  --member="serviceAccount:$PROD_SA" \
  --role="roles/storage.objectViewer"
```

> This grant persists — only needs to be done once.

---

### Step 4 — Import CSVs into target instance

```bash
# Import into PROD (columns must match SELECT order from Step 1)
gcloud sql import csv postgres-prod \
  "$EXPORT_PATH/<table_name>.csv" \
  --project=fruit-scout-production \
  --database=production \
  --table=schema.table_name \
  --columns=col1,col2,...

# Wait before next import
gcloud sql operations wait <operation_id> --project=fruit-scout-production --timeout=600
```

To import into **DEV** instead, swap `postgres-prod` / `fruit-scout-production` for `postgres-sandbox` / `farmagent-dev-sandbox` and use `--user=postgres`.

---

### Step 5 — Verify

```bash
# Connect to prod via local proxy and verify
cloud-sql-proxy "fruit-scout-production:us-central1:postgres-prod" --port=25460 --quiet &
PROD_PASS=$(gcloud secrets versions access latest \
  --secret="operation-db-password" \
  --project="fruit-scout-production")
PGPASSWORD="$PROD_PASS" psql "host=127.0.0.1 port=25460 user=operation_user dbname=production sslmode=disable" \
  -c "SELECT COUNT(*) FROM schema.table_name;"
kill %1
```

---

## Common Transfer Recipes

### Seed prod staging data from dev (e.g. after a new backfill)

Tables required (in order — respect FK constraints):
1. `digital_twin_staging.stg_fraction` (no FK deps)
2. `digital_twin_staging.stg_field_metrics` (FK → stg_fraction)
3. `digital_twin_staging.stg_plant` (FK → stg_fraction, largest table)

Always truncate target tables before importing if you want a clean load:
```bash
PGPASSWORD="$PROD_PASS" psql "$PROD_CONN" -c \
  "TRUNCATE digital_twin_staging.stg_plant;
   TRUNCATE digital_twin_staging.stg_field_metrics;
   TRUNCATE digital_twin_staging.stg_fraction CASCADE;"
```

### Copy prod dt_plant back to dev for local testing

```bash
gcloud sql export csv postgres-prod \
  "$EXPORT_PATH/dt_plant_sample.csv" \
  --project=fruit-scout-production \
  --database=production \
  --query="SELECT plant_id,field_id,fraction_id,customer_id,lng,lat,plant_class,plant_class_raw,source_ortho_uuid,label_version,registered_at FROM digital_twin.dt_plant WHERE customer_id='Herradura' LIMIT 50000"
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `HTTPError 409: another operation in progress` | Cloud SQL only allows 1 export/import at a time | Wait and retry |
| `403: NOT_AUTHORIZED on instances/postgres-sandbox` | Prod VM SA can't reach dev Cloud SQL | Use GCS method (this skill) |
| `ERROR: column X does not exist` | SELECT columns don't match table schema | Check migration was applied first |
| `duplicate key value violates unique constraint` | Data already exists in target | TRUNCATE target table first |
| Import completes but 0 rows | Wrong `--columns` order or empty file | Verify GCS file size and column order |

---

## Notes

- **Never transfer `stg_registration_log`** — it's an immutable audit trail; each environment keeps its own.
- **Export files persist in GCS** under `gs://farmagent-dev-sandbox-db-migration/transfers/`. Clean them up after successful transfer to avoid storage costs.
- Cloud SQL export/import jobs run entirely server-side — safe to close your terminal while they run.
