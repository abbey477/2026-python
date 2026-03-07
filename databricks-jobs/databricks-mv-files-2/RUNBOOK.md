# Databricks Materialized View — Project Runbook

> **Goal:** Compare query performance between standard views and materialized views on the `party` and `instrument` tables, with automatic incremental updates (INSERT / UPDATE / DELETE) on the materialized view via `TRIGGER ON UPDATE`.

---

## Table of Contents

1. [What We Are Building](#1-what-we-are-building)
2. [Objects Created](#2-objects-created)
3. [Files & How to Import](#3-files--how-to-import)
4. [Execution Order](#4-execution-order)
5. [Validation Checklist](#5-validation-checklist)
6. [How Incremental Refresh Works](#6-how-incremental-refresh-works)
7. [Performance Comparison Guide](#7-performance-comparison-guide)
8. [TRIGGER ON UPDATE Reference](#8-trigger-on-update-reference)
9. [Refresh Options & Incremental Behaviour](#9-refresh-options--incremental-behaviour)
10. [Troubleshooting](#10-troubleshooting)
11. [Cleanup](#11-cleanup)

---

## 1. What We Are Building

### Standard View vs Materialized View

| | Standard View | Materialized View |
|---|---|---|
| Stores data | ❌ No — just a saved SQL query | ✅ Yes — pre-computed Delta table |
| Query time | Slow — re-executes full query on every access | Fast — reads stored result directly |
| Always up to date | ✅ Real-time | ✅ Near real-time (auto-refreshes on source change) |
| Handles INSERT / UPDATE / DELETE | ✅ Always live | ✅ Via `TRIGGER ON UPDATE` |
| Compute cost per query | Higher | Lower (refresh cost is separate) |

### Why `TRIGGER ON UPDATE`?

With `TRIGGER ON UPDATE`, Databricks monitors the source table and automatically refreshes the materialized view whenever it detects a change — no scheduled jobs, no manual refresh commands.

> **Note on EXPLODE and incremental refresh:**
> `EXPLODE` (used to flatten nested arrays) may not be on Databricks' supported list for incremental refresh. If `EXPLAIN CREATE MATERIALIZED VIEW` returns `NOT_INCREMENTALIZABLE`, refreshes will be full recomputes rather than row-level incremental. The MV still delivers significant query performance benefits regardless.

---

## 2. Objects Created

| Object | Full Name | Type |
|---|---|---|
| Party materialized view | `x_prod.reference_data.party_identifiers_mv` | Materialized View |
| Instrument materialized view | `` `19519_ctg_dev`.refdata.instrument_identifiers_mv `` | Materialized View |
| Party standard view | `x_prod.reference_data.party_identifiers_vw` | Standard View |
| Instrument standard view | `` `19519_ctg_dev`.refdata.instrument_identifiers_vw `` | Standard View |

---

## 3. Files & How to Import

| File | Purpose | Run order |
|---|---|---|
| `01_standard_view.py` | Creates standard views, measures baseline query time | 1st |
| `02_materialized_view.py` | Creates MVs, validates incremental refresh, benchmarks | 2nd |
| `RUNBOOK.md` | This document — full reference | — |

### Importing into Databricks

1. In your Databricks workspace, open the **Workspace** sidebar
2. Navigate to your target folder
3. Click **⋮ (kebab menu) → Import**
4. Select the `.py` file
5. Attach to a **Unity Catalog-enabled Pro or Serverless SQL warehouse**
6. Run cells **top to bottom** — each cell is labelled and independent

> ⚠️ **Compute requirement:** Materialized Views require a **Unity Catalog-enabled Pro or Serverless SQL warehouse**.
> Classic compute does not support `CREATE MATERIALIZED VIEW` or incremental refresh.

---

## 4. Execution Order

```
Step 1  →  Run 01_standard_view.py
           - Creates party_identifiers_vw and instrument_identifiers_vw
           - Measures full scan and aggregation query time
           - Record the times printed in the output

Step 2  →  Run 02_materialized_view.py
           - Enables rowTracking + changeDataFeed on source tables
           - Runs EXPLAIN to check incrementalizability
           - Creates party_identifiers_mv and instrument_identifiers_mv with TRIGGER ON UPDATE
           - Validates data consistency vs standard views
           - Measures same queries against MVs
           - Tests INSERT / UPDATE / DELETE incremental propagation

Step 3  →  Fill in the summary tables in both notebooks with your recorded times
```

### Within `02_materialized_view.py`, cell order matters:

| Cell group | What it does | Requires |
|---|---|---|
| PRE-REQUISITE | `ALTER TABLE` to enable row tracking and CDF | Source tables must exist |
| Step 1 | `EXPLAIN CREATE` to check incrementalizability | Pre-requisite complete |
| Steps 2–3 | Create Materialized Views with `TRIGGER ON UPDATE` | Step 1 run (regardless of result) |
| Step 4 | Validate MV metadata and row counts | MVs created and loaded |
| Step 5 | Data consistency check vs standard view | Standard view from notebook 01 must exist |
| Steps 6–7 | Benchmark timing | MV initial load must be complete |
| Step 8 | INSERT / UPDATE / DELETE incremental test | MV must be running with TRIGGER ON UPDATE |

---

## 5. Validation Checklist

### Pre-requisite properties

After running the `ALTER TABLE` cells, run `SHOW TBLPROPERTIES` and confirm:

```
delta.enableDeletionVectors  =  true
delta.enableRowTracking      =  true
delta.enableChangeDataFeed   =  true
```

---

### Incrementalizability result

| Output from EXPLAIN | Meaning | Effect on MV |
|---|---|---|
| `INCREMENTALIZABLE` | Query supports row-level incremental refresh | Refreshes process only changed rows |
| `NOT_INCREMENTALIZABLE — OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE blocks direct incremental refresh | Refreshes are full recomputes — MV still works and delivers query performance benefit |
| `NOT_INCREMENTALIZABLE — ROW_TRACKING_NOT_ENABLED` | Row tracking not enabled | Re-run the `ALTER TABLE` pre-requisite cell |

---

### MV metadata check

After creation, `DESCRIBE EXTENDED` must show:

```
Type                =  MATERIALIZED VIEW
Refresh Schedule    =  TRIGGER ON UPDATE
Last Refreshed      =  <recent timestamp>
```

---

### Refresh type check

After any refresh, query the event log:

```sql
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;
```

| `message` value | Meaning |
|---|---|
| `ROW_BASED` | ✅ True incremental — only changed rows processed |
| `PARTITION_OVERWRITE` | ✅ Incremental at partition level |
| `NO_OP` | ℹ️ No changes in source — nothing to do |
| `COMPLETE_RECOMPUTE` | ⚠️ Full refresh — expected if EXPLODE is not incrementalizable |

---

### Data consistency check

The `EXCEPT` query in Step 5 of `02_materialized_view.py` must return **0 rows**.

---

### Incremental update test (Step 8)

| Operation | Expected result |
|---|---|
| `INSERT TEST_ECI_99999` | Row appears in MV within 1–2 minutes |
| `UPDATE country_of_domicile = 'US'` | Updated value visible in MV within 1–2 minutes |
| `DELETE TEST_ECI_99999` | Row gone from MV within 1–2 minutes |

---

## 6. How Incremental Refresh Works

### The flow for each source change

```
1. Row inserted / updated / deleted in source party or instrument table
2. Delta Change Data Feed records the change in the transaction log
3. Databricks detects the CDF event (polling every ~1 minute minimum)
4. TRIGGER ON UPDATE fires — MV refreshes with only the changed rows
5. Query against the MV returns the updated result
```

### Typical latency

**1–5 minutes** from source change to MV updated — depends on cluster warm-up and trigger polling interval (minimum 1 minute per Databricks limits).

### Refresh policy options

| Approach | SQL clause | Behaviour |
|---|---|---|
| Auto (default, this runbook) | `TRIGGER ON UPDATE` | Databricks picks incremental or full based on cost model |
| Strict incremental | `REFRESH POLICY INCREMENTAL (STRICT)` | Errors rather than falling back to full recompute |
| Time-based schedule | `SCHEDULE EVERY 1 HOUR` | Refreshes on a fixed interval regardless of source changes |
| Manual only | _(no clause)_ | Only refreshes when `REFRESH MATERIALIZED VIEW` is run explicitly |

### Throttling (optional — if source updates too frequently)

```sql
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ALTER TRIGGER ON UPDATE AT MOST EVERY INTERVAL 5 MINUTES;
```

---

## 7. Performance Comparison Guide

### Summary table to fill in

| Query | Standard View (sec) | Materialized View (sec) | Speedup factor |
|---|---|---|---|
| `party` — full scan | | | |
| `instrument` — full scan | | | |
| `party` — aggregation | | | |
| `instrument` — aggregation | | | |

**Speedup factor** = Standard View time ÷ Materialized View time

### Where to find precise metrics in Databricks

**SQL Editor → Query History** — each query entry shows exact duration, DBU consumption, and bytes scanned.

### What to expect

| Query type | Expected MV advantage |
|---|---|
| Full table scan | Moderate — MV skips EXPLODE overhead at query time |
| Aggregation | Large — MV serves pre-flattened data; no array expansion needed |
| Filtered lookup | Moderate — MV benefits from Delta file pruning on stored data |
| Repeated queries | Large — standard view re-executes from scratch every time; MV does not |

---

## 8. TRIGGER ON UPDATE Reference

| Property | Detail |
|---|---|
| Minimum trigger interval | 1 minute |
| Maximum upstream tables per MV | 10 |
| Maximum upstream views per MV | 30 |
| Maximum MVs with TRIGGER ON UPDATE per workspace | 1,000 (contact Databricks Support if more needed) |
| Feature status | Beta (as of October 2025) |

---

## 9. Refresh Options & Incremental Behaviour

### The two independent questions

Every materialized view refresh involves two separate decisions:

```
Question 1 — WHEN does the refresh fire?     → your refresh option controls this
Question 2 — HOW does it process the data?   → EXPLAIN CREATE result controls this
```

These are **completely independent**. Your choice of refresh option has no effect on whether the refresh is incremental or a full recompute. That decision comes entirely from `EXPLAIN CREATE`.

---

### All refresh options are subject to the same EXPLAIN CREATE result

| Refresh Option | Auto-fires on source change? | If INCREMENTALIZABLE | If NOT_INCREMENTALIZABLE |
|---|---|---|---|
| `TRIGGER ON UPDATE` | ✅ Yes — within ~1 min | Incremental refresh | **Full recompute** |
| `SCHEDULE EVERY` | ⏰ On next interval tick | Incremental refresh | **Full recompute** |
| `SCHEDULE CRON` | ⏰ At scheduled time | Incremental refresh | **Full recompute** |
| Manual `REFRESH` | ❌ Only when you run it | Incremental refresh | **Full recompute** |
| `REFRESH ASYNC` | ❌ Only when you run it | Incremental refresh | **Full recompute** |
| Lakeflow Job | ⏰ Only when job runs | Incremental refresh | **Full recompute** |
| `REFRESH FULL` | ❌ Only when you run it | Always full recompute — ignores EXPLAIN result by design |

> **Key point:** `TRIGGER ON UPDATE` does not guarantee incremental refresh. It only guarantees *automatic* firing. The refresh method is determined solely by the query.

---

### What NOT_INCREMENTALIZABLE means in practice

If `EXPLAIN CREATE` returns `NOT_INCREMENTALIZABLE` (which is expected with `EXPLODE`):

- **Every single refresh is a full recompute** — no exceptions
- Even a single-row INSERT in the source causes Databricks to scan the entire source table, re-explode every array, and rewrite all rows in the MV
- This applies regardless of which refresh option triggered it
- Row tracking and CDF being enabled does not change this outcome

```
Source change (e.g. 1 row inserted)
    │
    ▼
Refresh fires (via any option)
    │
    ▼
NOT_INCREMENTALIZABLE → Full recompute always
    ┌──────────────────────────────────────────┐
    │  Clear entire MV                         │
    │  Re-execute full query from scratch      │
    │  Rewrite ALL rows back into the MV       │
    └──────────────────────────────────────────┘
```

---

### What INCREMENTALIZABLE means in practice

If `EXPLAIN CREATE` returns `INCREMENTALIZABLE`, Databricks has the *option* to refresh incrementally — but it is not guaranteed. Databricks runs a **cost model** on each refresh and may still choose a full recompute if it calculates that to be cheaper.

```
INCREMENTALIZABLE
    │
    ▼
Databricks cost model runs
    ├── Incremental is cheaper → Incremental refresh ✅ (only changed rows)
    └── Full recompute is cheaper → Full recompute ⚠️ (all rows, but still correct)
```

| EXPLAIN result | Refresh method |
|---|---|
| `NOT_INCREMENTALIZABLE` | Always full recompute — locked in, no choice |
| `INCREMENTALIZABLE` | Usually incremental — but Databricks may still choose full recompute |

---

### Refresh option comparison — auto-sync with master table

When a row is inserted, updated, or deleted in the `party` or `instrument` source table:

| Option | MV syncs automatically? | Staleness window |
|---|---|---|
| `TRIGGER ON UPDATE` | ✅ Yes | ~1–2 minutes |
| `SCHEDULE EVERY 1 HOUR` | ⏰ Eventually | Up to 1 hour |
| `SCHEDULE CRON` (daily 8am) | ⏰ Eventually | Up to 24 hours |
| Manual `REFRESH` | ❌ No | Until you run the command |
| Lakeflow Job | ⏰ Eventually | Depends on job schedule |

`TRIGGER ON UPDATE` is the only option where a change to the master table automatically and immediately propagates to the MV without human or scheduled intervention.

---

### Options to fix NOT_INCREMENTALIZABLE (if true incremental is required)

| Approach | How | Trade-off |
|---|---|---|
| Pre-flatten arrays in source | Store data already flat so no `EXPLODE` needed in the MV query | Requires source table schema change |
| Streaming Table as intermediate layer | Streaming Table handles CDC; MV sits on top and does `EXPLODE` | Adds one object to manage |
| Accept full recompute | Keep current design — `TRIGGER ON UPDATE` still auto-fires, just reprocesses all rows | Higher compute cost per refresh on large tables |

---

## 10. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `EXPLAIN` returns `NOT_INCREMENTALIZABLE — OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE is not on Databricks' incremental-supported clause list | Expected — MV still works, refreshes will be full recomputes |
| `EXPLAIN` returns `ROW_TRACKING_NOT_ENABLED` | `ALTER TABLE` pre-requisite not applied | Re-run the `ALTER TABLE` cells in `02_materialized_view.py` |
| event_log shows `COMPLETE_RECOMPUTE` | EXPLODE blocks incremental refresh | Expected if EXPLAIN returned `NOT_INCREMENTALIZABLE` |
| MV row count does not match standard view | Initial load still in progress | Wait a few minutes and recheck; or run `REFRESH MATERIALIZED VIEW <name>` |
| Trigger not firing after source change | Less than 1 min since last trigger, or CDF not enabled | Confirm `delta.enableChangeDataFeed = true`, wait at least 1 minute |
| `CREATE MATERIALIZED VIEW` fails — permission error | Missing `CREATE MATERIALIZED VIEW` privilege | Run: `GRANT CREATE MATERIALIZED VIEW ON SCHEMA <schema> TO <user>` |
| Cannot query MV from a notebook | Incompatible compute attached | Use a SQL warehouse or Standard/Dedicated access mode cluster on DBR 15.4+ |
| `SHOW TBLPROPERTIES` does not show CDF | Table is not a Unity Catalog managed Delta table | Confirm table catalog and contact your data platform team |

---

## 11. Cleanup

Run only when you want to permanently remove all objects created by this project:

```sql
DROP MATERIALIZED VIEW IF EXISTS x_prod.reference_data.party_identifiers_mv;
DROP MATERIALIZED VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_mv;
DROP VIEW IF EXISTS x_prod.reference_data.party_identifiers_vw;
DROP VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_vw;
```

> ⚠️ Dropping a Materialized View deletes the stored data and the associated serverless pipeline permanently.

---

*Last updated: March 2026*
