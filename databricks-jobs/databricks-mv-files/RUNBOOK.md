# Databricks Materialized View — Project Runbook

> **Goal:** Compare query performance between standard views and materialized views on the `party` and `instrument` tables, with true incremental updates (INSERT / UPDATE / DELETE) on the materialized view.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Objects Created](#2-objects-created)
3. [How to Run](#3-how-to-run)
4. [Execution Order](#4-execution-order)
5. [Validation Checklist](#5-validation-checklist)
6. [Understanding Incremental Refresh](#6-understanding-incremental-refresh)
7. [Performance Comparison Guide](#7-performance-comparison-guide)
8. [TRIGGER ON UPDATE Behaviour](#8-trigger-on-update-behaviour)
9. [Troubleshooting](#9-troubleshooting)
10. [Cleanup](#10-cleanup)

---

## 1. Architecture Overview

### Why two layers?

`EXPLODE` (used to flatten the `alternate_identifiers` / `alternateIdentifiers` arrays) is **not on Databricks' supported list for direct incremental refresh**. To get true incremental processing end-to-end, we use a two-layer architecture:

```
Source Delta Table
    └─► Streaming Table       ← handles CDC: INSERT / UPDATE / DELETE incrementally
            └─► Materialized View  ← EXPLODE flattening on top of streaming table
```

The **Streaming Table** absorbs the changes from the source incrementally via Change Data Feed (CDF). The **Materialized View** on top of it does the array flattening — and because its upstream is already incremental, the whole pipeline is incremental.

### What is a Streaming Table?
A Streaming Table continuously reads only **new changes** from a Delta source (using the CDF). It never reprocesses data it has already seen, making it the correct CDC layer for this use case.

### What is a Materialized View?
A Materialized View physically stores pre-computed query results as a Delta table. Unlike a standard view (which re-executes its query on every access), a materialized view serves pre-computed data — dramatically reducing query latency.

---

## 2. Objects Created

| Object | Full Name | Type | Purpose |
|---|---|---|---|
| Party streaming table | `x_prod.reference_data.party_stream` | Streaming Table | CDC layer — incremental changes from party source |
| Instrument streaming table | `` `19519_ctg_dev`.refdata.instrument_stream `` | Streaming Table | CDC layer — incremental changes from instrument source |
| Party materialized view | `x_prod.reference_data.party_identifiers_mv` | Materialized View | Flattened party identifiers — auto-refreshes on source change |
| Instrument materialized view | `` `19519_ctg_dev`.refdata.instrument_identifiers_mv `` | Materialized View | Flattened instrument identifiers — auto-refreshes on source change |
| Party standard view | `x_prod.reference_data.party_identifiers_vw` | Standard View | Baseline for performance comparison |
| Instrument standard view | `` `19519_ctg_dev`.refdata.instrument_identifiers_vw `` | Standard View | Baseline for performance comparison |

---

## 3. How to Run

You have **three files** to work with:

| File | What it does | Run order |
|---|---|---|
| `01_standard_view.py` | Creates standard views, measures query time | 1st |
| `02_materialized_view.py` | Full MV setup, incremental refresh, benchmark | 2nd |
| `databricks_mv_setup.sql` | Complete SQL reference (all sections in one file) | Reference only |

### Importing notebooks into Databricks

1. In your Databricks workspace, go to **Workspace** in the left sidebar
2. Navigate to the folder where you want to save the notebooks
3. Click **⋮ (kebab menu) → Import**
4. Select the `.py` file (`01_standard_view.py` or `02_materialized_view.py`)
5. Attach to a **SQL warehouse** (required for `%sql` cells and Materialized View creation)
6. Run cells top to bottom — each cell is independent and labelled

> ⚠️ **Compute requirement:** Materialized Views and Streaming Tables require a **Unity Catalog-enabled Pro or Serverless SQL warehouse**. Classic compute will not support incremental refresh.

---

## 4. Execution Order

Run in this exact order to avoid dependency errors:

```
Step 1  →  Run 01_standard_view.py         (creates standard views + records baseline times)
Step 2  →  Run 02_materialized_view.py     (enables CDF, creates streaming tables + MVs)
Step 3  →  Fill in summary tables in both notebooks with the recorded times
```

### Within `02_materialized_view.py`, cell order matters:

| Cell group | What it does | Pre-requisite |
|---|---|---|
| PRE-REQUISITE | `ALTER TABLE` to enable row tracking + CDF | Source tables must exist |
| Step 1 | `EXPLAIN CREATE` — checks incrementalizability | Pre-requisite must pass |
| Step 2 | Create Streaming Tables | Step 1 completed |
| Step 3 | Create Materialized Views | Streaming Tables must have data |
| Step 4 | Data consistency check vs standard view | Both MV and standard view must exist |
| Step 5–6 | Benchmark timing | MV must be fully loaded |
| Step 7 | INSERT / UPDATE / DELETE incremental test | MV must be running with TRIGGER ON UPDATE |

---

## 5. Validation Checklist

### ✅ Pre-requisite validation

After running the `ALTER TABLE` cells, run `SHOW TBLPROPERTIES` and confirm:

```
delta.enableDeletionVectors  =  true
delta.enableRowTracking      =  true
delta.enableChangeDataFeed   =  true
```

If any are missing, re-run the `ALTER TABLE` cell for that table.

---

### ✅ Incrementalizability check

After running `EXPLAIN CREATE MATERIALIZED VIEW`:

| Output | Meaning | Action |
|---|---|---|
| `INCREMENTALIZABLE` | Query supports direct incremental refresh | Streaming Table layer optional — but keep it for robustness |
| `NOT_INCREMENTALIZABLE` with `OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE blocks direct incremental | Proceed with Streaming Table architecture as designed |
| `NOT_INCREMENTALIZABLE` with `ROW_TRACKING_NOT_ENABLED` | Row tracking not enabled on source | Re-run the `ALTER TABLE` pre-requisite cell |
| `NOT_INCREMENTALIZABLE` with `INPUT_NOT_IN_DELTA` | Source is not a Delta table | Contact your data platform team |

---

### ✅ Streaming table validation

Row counts from `party_stream` and `instrument_stream` should closely match the source tables.

---

### ✅ MV creation validation

`DESCRIBE EXTENDED` output should show:

```
Type                =  MATERIALIZED VIEW
Refresh Schedule    =  TRIGGER ON UPDATE
Last Refreshed      =  <recent timestamp>
```

---

### ✅ Refresh type validation

After any refresh, check the event log:

```sql
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;
```

| `message` value | Meaning | Expected? |
|---|---|---|
| `ROW_BASED` | ✅ True incremental — only changed rows processed | Yes |
| `PARTITION_OVERWRITE` | ✅ Incremental at partition level | Yes |
| `NO_OP` | ℹ️ No changes in source — nothing to refresh | Yes (if source unchanged) |
| `COMPLETE_RECOMPUTE` | ⚠️ Full refresh triggered | Investigate |

---

### ✅ Data consistency validation

The `EXCEPT` query in Step 4 of `02_materialized_view.py` should return **0 rows**, confirming MV and standard view produce identical results.

---

### ✅ Incremental update test

| Test | Expected outcome |
|---|---|
| INSERT `TEST_ECI_99999` | Row appears in MV within 1-2 minutes |
| UPDATE `country_of_domicile = 'US'` | Field updated in MV within 1-2 minutes |
| DELETE `TEST_ECI_99999` | Row removed from MV within 1-2 minutes |

---

## 6. Understanding Incremental Refresh

### How TRIGGER ON UPDATE works

```
1. You INSERT / UPDATE / DELETE a row in the source party or instrument table
2. The Delta table's Change Data Feed records the change
3. The Streaming Table detects the CDF event and ingests only the changed row(s)
4. Databricks detects the Streaming Table changed and fires the MV trigger
5. The Materialized View refreshes — processing only the newly changed rows
6. Your query against the MV sees the updated result
```

Total latency from source change to MV updated: **typically 1-5 minutes** (depends on cluster warm-up and trigger polling interval, minimum 1 minute).

### Refresh policy options

| Approach | SQL | Behaviour |
|---|---|---|
| Auto (default) | `TRIGGER ON UPDATE` | Databricks chooses incremental or full based on cost model |
| Force incremental | `REFRESH POLICY INCREMENTAL` | Always incremental, fails if not possible |
| Force incremental (strict) | `REFRESH POLICY INCREMENTAL (STRICT)` | Always incremental, **errors** rather than falling back to full |
| Manual only | _(no clause)_ | Only refreshes when you run `REFRESH MATERIALIZED VIEW` |
| Scheduled | `SCHEDULE EVERY 1 HOUR` | Refreshes on a fixed time interval |

### Throttling (optional)

If the source updates very frequently and you don't need the MV to refresh every single time:

```sql
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ALTER TRIGGER ON UPDATE AT MOST EVERY INTERVAL 5 MINUTES;
```

---

## 7. Performance Comparison Guide

### What to measure

After running both notebooks, fill in this table:

| Query | Standard View (sec) | Materialized View (sec) | Speedup factor |
|---|---|---|---|
| `party` — full scan | | | |
| `instrument` — full scan | | | |
| `party` — aggregation | | | |
| `instrument` — aggregation | | | |

**Speedup factor** = Standard View time ÷ Materialized View time

### Where to find precise metrics

In Databricks: **SQL Editor → Query History**

Each query entry shows:
- Exact execution duration
- DBU consumption
- Bytes scanned

### What to expect

| Query type | Typical MV advantage |
|---|---|
| Full table scan | Moderate — MV skips EXPLODE overhead |
| Aggregation | Large — MV serves pre-grouped data |
| Filtered lookup | Moderate to large — MV can leverage Delta file pruning |
| First run (cold cache) | Large — standard view must scan source files from scratch |
| Repeated runs | Standard views benefit from Databricks caching; gap narrows |

### Trade-offs

| Aspect | Standard View | Materialized View |
|---|---|---|
| Query speed | Slower (compute on every query) | Faster (pre-computed) |
| Data freshness | Always real-time | Near real-time (TRIGGER ON UPDATE) |
| Storage cost | None | Stores a full copy of the result |
| Refresh cost | None | Serverless DBUs on each triggered refresh |
| Best for | Ad-hoc, infrequent, real-time | BI dashboards, repeated queries, large data |

---

## 8. TRIGGER ON UPDATE Behaviour

| Property | Detail |
|---|---|
| Trigger condition | Fires when Databricks detects changes in the upstream Streaming Table |
| Minimum interval | 1 minute — cannot trigger more than once per minute |
| Max upstream tables per MV | 10 |
| Max upstream views per MV | 30 |
| Max MVs with TRIGGER ON UPDATE per workspace | 1,000 |
| Feature status | Beta (as of October 2025) |

### Workspace limits

If you need more than 1,000 MVs with `TRIGGER ON UPDATE`, contact Databricks Support.

---

## 9. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `EXPLAIN` returns `NOT_INCREMENTALIZABLE` with `OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE blocks direct incremental refresh | Expected — use Streaming Table layer as designed in this runbook |
| `EXPLAIN` returns `ROW_TRACKING_NOT_ENABLED` | `ALTER TABLE` pre-requisite not applied | Re-run the `ALTER TABLE` cell in `02_materialized_view.py` |
| event_log shows `COMPLETE_RECOMPUTE` after incremental test | MV is pointing at Delta source directly instead of Streaming Table | Confirm MV `FROM` clause references `party_stream`, not `party` |
| MV row count doesn't match standard view | MV initial load still in progress | Wait a few minutes, then recheck |
| Trigger not firing after source change | Under 1 min since last trigger, or CDF not enabled | Confirm `delta.enableChangeDataFeed = true`, wait at least 1 minute |
| `CREATE STREAMING TABLE` fails | Serverless pipelines not enabled in workspace | Contact Databricks admin — serverless must be enabled |
| `CREATE MATERIALIZED VIEW` fails with permission error | Missing `CREATE MATERIALIZED VIEW` grant | Run: `GRANT CREATE MATERIALIZED VIEW ON SCHEMA <schema> TO <user>` |
| Cannot query MV from notebook | Compute mode incompatible | Use a SQL warehouse or Standard/Dedicated access mode cluster (DBR 15.4+) |

---

## 10. Cleanup

Uncomment and run only if you want to remove all objects created by this project:

```sql
-- Remove Materialized Views
DROP MATERIALIZED VIEW IF EXISTS x_prod.reference_data.party_identifiers_mv;
DROP MATERIALIZED VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_mv;

-- Remove Streaming Tables
DROP TABLE IF EXISTS x_prod.reference_data.party_stream;
DROP TABLE IF EXISTS `19519_ctg_dev`.refdata.instrument_stream;

-- Remove Standard Views
DROP VIEW IF EXISTS x_prod.reference_data.party_identifiers_vw;
DROP VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_vw;
```

> ⚠️ Dropping a Materialized View also deletes the underlying stored data and the associated serverless pipeline.

---

*Last updated: March 2026*
