# Databricks Incremental Materialized View — Complete Setup Guide

> **Use case:** Large source table (trillions of rows). Load only rows from a fixed `cob_date` cutoff on day zero. All subsequent refreshes must be **incremental only** — picking up both new dates and changes to existing rows.
>
> **No DLT pipeline required.** Everything runs via plain SQL on a serverless SQL Warehouse.

---

## Prerequisites

| Requirement | Detail |
|---|---|
| SQL Warehouse | Unity Catalog-enabled **Pro** or **Serverless** |
| Source table format | Must be a **Delta table** |
| Permissions | `SELECT` on source table, `CREATE MATERIALIZED VIEW` on target schema |
| Serverless compute | Required for incremental refresh to work |

---

## Architecture Overview

```
Source Table (trillions of rows)
  x_prod.reference_data.party
        |
        |  WHERE __cob_date >= '2024-01-01'   ← limits day-zero scan
        |  Row tracking + CDF detects changes ← enables incremental refresh
        ▼
Materialized View
  x_prod.reference_data.party_identifiers_mv
        |
        |  Day zero    → full scan of filtered rows only
        |  Subsequent  → incremental: new dates + changes to existing rows
        ▼
  Always query the MV, never the source
```

---

## Step 1 — Enable Source Table Properties

Run this **once** on the source table. All three properties are required/recommended by Databricks for optimal incremental refresh.

```sql
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
  delta.enableRowTracking    = true,   -- REQUIRED for incremental refresh
  delta.enableChangeDataFeed = true,   -- REQUIRED for change detection
  delta.enableDeletionVectors = true   -- RECOMMENDED: efficient delete tracking
);
```

> **Important:** If the source table is ever recreated from scratch, you must re-run this command — row tracking is reset on table recreation.

---

## Step 2 — Verify Your Query Is Incrementalizable

Run this **before** creating the MV. It validates that your query structure supports incremental refresh without actually creating anything.

```sql
EXPLAIN CREATE MATERIALIZED VIEW
AS
SELECT
    __cob_date,
    eci,
    country_of_domicile,
    country_of_asset,
    organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM x_prod.reference_data.party cp
LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids
WHERE __cob_date >= '2024-01-01';
```

**What to look for in the output:**

- If it returns a physical query plan → your query is incrementalizable ✅
- If it returns an error mentioning `NOT_INCREMENTALIZABLE` → the query has an unsupported operator and needs fixing before proceeding ❌

---

## Step 3 — Create the Materialized View (Day Zero Load)

This single statement creates the MV **and** performs the initial data load automatically. The `WHERE` clause limits the day-zero scan to rows from `2024-01-01` onwards — the rest of the trillion-row table is never touched.

```sql
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  REFRESH POLICY INCREMENTAL STRICT
AS
SELECT
    __cob_date,
    eci,
    country_of_domicile,
    country_of_asset,
    organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM x_prod.reference_data.party cp
LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids
WHERE __cob_date >= '2024-01-01';
```

**What `REFRESH POLICY INCREMENTAL STRICT` means:**

| Policy | Behaviour |
|---|---|
| `AUTO` (default) | Databricks decides — may choose full recompute if it thinks it's cheaper |
| `INCREMENTAL` | Prefer incremental, silently fall back to full if needed |
| `INCREMENTAL STRICT` | **Always incremental. Fails with an error rather than doing a full recompute.** This is what you want. |

> **Note on the static date filter:** Using a static string like `'2024-01-01'` is correct and safe for incremental refresh. Do **not** replace it with `current_date()` or any other dynamic function — non-deterministic functions in `SELECT` or computed columns break incremental refresh. However, `current_date()` is permitted inside `WHERE` clauses as a special exception if you ever need a rolling window.

---

## Step 4 — Subsequent Incremental Refreshes

Every time you want to refresh, run:

```sql
REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;
```

Databricks will automatically:
- Detect new rows added to the source (new `cob_date` values)
- Detect changes/updates to existing rows within the `>= 2024-01-01` window
- Apply only those deltas to the MV — **no full recompute**

Because `INCREMENTAL STRICT` is set, if for any reason an incremental refresh cannot be performed (e.g. source table row tracking was disabled), the refresh will **fail with a clear error** rather than silently running an expensive full scan.

### Optional: Force a full refresh manually

If you ever need to rebuild from scratch (e.g. the source data was corrected retroactively):

```sql
REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv FULL;
```

---

## Step 5 — Verify Each Refresh Is Incremental

### Method 1 — Catalog Explorer UI (easiest)

1. In the Databricks sidebar click **Catalog**
2. Navigate to `x_prod → reference_data → party_identifiers_mv`
3. In the right panel, look at **Current refresh status**
4. Click **"See refresh details"** — this shows whether the refresh was full or incremental, the duration, and the reason

### Method 2 — Event Log Query (programmatic)

Run this after every refresh to confirm the technique used:

```sql
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC;
```

**Interpreting the message column:**

| Message contains | Meaning |
|---|---|
| `ROW_BASED` | ✅ Incremental |
| `PARTITION_OVERWRITE` | ✅ Incremental |
| `GROUP_AGGREGATE` | ✅ Incremental |
| `APPEND_ONLY` | ✅ Incremental |
| `WINDOW_FUNCTION` | ✅ Incremental |
| `GENERIC_AGGREGATE` | ✅ Incremental |
| `FULL_RECOMPUTE` | ❌ Full refresh — investigate why |
| `NO_OP` | ℹ️ No changes detected in source — nothing to do |

**Sample output when incremental:**
```
2025-03-21T22:23:16.497+00:00 | Flow 'party_identifiers_mv' has been planned in LDP to be executed as ROW_BASED.
```

### Method 3 — DESCRIBE EXTENDED

```sql
DESCRIBE EXTENDED x_prod.reference_data.party_identifiers_mv;
```

Scroll to the bottom of the output and look for **Last Refresh Type** — it will say either `INCREMENTAL` or `FULL`.

---

## Troubleshooting

### Refresh fails with `MATERIALIZED_VIEW_NOT_INCREMENTALIZABLE`

This is expected behaviour with `INCREMENTAL STRICT` — the refresh refused to do a full recompute. Common causes:

| Error code | Cause | Fix |
|---|---|---|
| `ROW_TRACKING_NOT_ENABLED` | Row tracking not enabled on source | Re-run Step 1 |
| `INPUT_NOT_IN_DELTA` | Source is not a Delta table | Source must be Delta |
| `EXPRESSION_NOT_DETERMINISTIC` | Non-deterministic function in SELECT | Remove `RAND()`, `UUID()` etc. |
| `OPERATOR_NOT_INCREMENTALIZABLE` | Unsupported join or operator | Simplify the query |

### Refresh shows `FULL_RECOMPUTE` in event log

If using `AUTO` policy, Databricks chose full recompute as cheaper. Switch to `INCREMENTAL STRICT` to enforce incremental. Also verify row tracking is still enabled on the source:

```sql
DESCRIBE EXTENDED x_prod.reference_data.party;
-- Look for: delta.enableRowTracking = true
```

### Moving the cutoff date forward

If you want to change `>= '2024-01-01'` to a later date, re-run the `CREATE OR REPLACE` statement with the new date. This triggers a one-time full reload from the new cutoff, then resumes incremental from there.

---

## When Does the MV Update? Refresh Triggers Explained

**The MV does NOT update automatically by default.** Databricks SQL materialized views always run in **triggered mode** — they never continuously watch the source and self-update. Data added to your master table will not appear in the MV until a refresh is explicitly triggered.

You have four options:

---

### Option 1 — Manual (default behaviour)

Nothing happens automatically. You call the refresh yourself:

```sql
REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;
```

Use this for development, testing, or ad-hoc scenarios.

---

### Option 2 — `TRIGGER ON UPDATE` ⭐ Recommended for production

The MV automatically refreshes when Databricks detects changes in the upstream source table. This is the closest to "automatic" and is what Databricks recommends for production workloads, especially when the source does not update on a predictable schedule.

**Add to an existing MV:**
```sql
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ADD TRIGGER ON UPDATE;
```

**Or set at creation time:**
```sql
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  REFRESH POLICY INCREMENTAL STRICT
  TRIGGER ON UPDATE
AS
SELECT ...
```

**Throttle refresh frequency** — if the source updates very frequently and you don't need the MV to respond every single time, cap it:
```sql
-- Refresh at most once every 5 minutes even if source changes more often
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ALTER TRIGGER ON UPDATE AT MOST EVERY INTERVAL 5 MINUTES;
```

**Verified limitations (from official docs):**

| Limitation | Detail |
|---|---|
| Minimum interval | 1 minute — cannot trigger faster than once per minute |
| Max upstream tables | 10 tables per MV |
| Max upstream views | 30 views per MV |
| Workspace limit | Max 1,000 MVs with `TRIGGER ON UPDATE` per workspace |
| Feature status | **Beta** as of the latest docs |
| Delta Sharing | Shared tables are NOT supported as upstream sources |

> **Note:** Enabling file events on the source table can make triggers more performant and increases some of the above limits. Contact your Databricks admin about workspace-level file events configuration.

---

### Option 3 — Scheduled Refresh

Refresh on a fixed time interval regardless of whether source data changed:

```sql
-- Refresh every hour
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  REFRESH POLICY INCREMENTAL STRICT
  SCHEDULE EVERY 1 HOUR
AS SELECT ...

-- Or every day at midnight UTC
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  REFRESH POLICY INCREMENTAL STRICT
  SCHEDULE CRON '0 0 0 * * ?' AT TIME ZONE 'UTC'
AS SELECT ...
```

Add or change a schedule on an existing MV without recreating it:
```sql
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ALTER SCHEDULE EVERY 4 HOURS;
```

Drop a schedule entirely (reverts to manual):
```sql
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  DROP SCHEDULE;
```

Use this when your source updates on a known, predictable cadence (e.g. a nightly batch load).

---

### Option 4 — Orchestrated via Databricks Jobs

Trigger the refresh as part of a larger pipeline, after upstream jobs complete:

```sql
-- SQL task inside a Databricks Job
REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;
```

Use this when the MV refresh needs to happen after other dependent jobs finish — for example, after a nightly ETL job writes new data to the source table.

---

### Refresh Options Comparison

| Method | When does MV update? | Latency | Best for |
|---|---|---|---|
| Manual | Only when you run `REFRESH` | You control it | Dev / testing |
| `TRIGGER ON UPDATE` | Within ~1 min of source changes | ~1 min minimum | Production — unpredictable source updates |
| `SCHEDULE` | Fixed interval (e.g. every hour) | Up to 1 interval | Production — predictable daily/hourly loads |
| Job orchestration | After upstream job completes | Depends on job | Complex pipelines with dependencies |

---

### Important: MV Latency Is Not Real-Time

Regardless of which trigger method you choose, materialized views are **not designed for millisecond latency**. The latency of updating a materialized view is in the **seconds to minutes** range, not milliseconds. If you need real-time data, a materialized view is not the right tool — consider a streaming table instead.

---

## Summary Cheatsheet

```sql
-- 1. Enable source table properties (once)
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
  delta.enableRowTracking    = true,
  delta.enableChangeDataFeed = true,
  delta.enableDeletionVectors = true
);

-- 2. Verify query is incrementalizable
EXPLAIN CREATE MATERIALIZED VIEW
AS SELECT ... FROM ... WHERE __cob_date >= '2024-01-01';

-- 3. Create MV (day zero load)
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  REFRESH POLICY INCREMENTAL STRICT
AS SELECT ... FROM ... WHERE __cob_date >= '2024-01-01';

-- 4. Subsequent incremental refreshes
REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;

-- 5. Verify incremental
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC;
```

---

## References

- [Incremental refresh for materialized views](https://docs.databricks.com/aws/en/optimizations/incremental-refresh)
- [Use materialized views in Databricks SQL](https://docs.databricks.com/aws/en/ldp/dbsql/materialized)
- [Monitor materialized views in Databricks SQL](https://docs.databricks.com/aws/en/ldp/dbsql/materialized-monitor)
- [REFRESH POLICY clause](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-materialized-view-refresh-policy)
- [ALTER MATERIALIZED VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-materialized-view)
- [CREATE MATERIALIZED VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-materialized-view)
- [Row tracking in Databricks](https://docs.databricks.com/aws/en/delta/row-tracking)
