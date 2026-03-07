# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # Databricks Materialized View — Project Runbook
# MAGIC
# MAGIC > **Goal:** Compare query performance between standard views and materialized views on the `party` and `instrument` tables, with automatic incremental updates (INSERT / UPDATE / DELETE) on the materialized view via `TRIGGER ON UPDATE`.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Table of Contents
# MAGIC
# MAGIC 1. [What We Are Building](#1-what-we-are-building)
# MAGIC 2. [Objects Created](#2-objects-created)
# MAGIC 3. [Files & How to Import](#3-files--how-to-import)
# MAGIC 4. [Execution Order](#4-execution-order)
# MAGIC 5. [Validation Checklist](#5-validation-checklist)
# MAGIC 6. [How Incremental Refresh Works](#6-how-incremental-refresh-works)
# MAGIC 7. [Performance Comparison Guide](#7-performance-comparison-guide)
# MAGIC 8. [TRIGGER ON UPDATE Reference](#8-trigger-on-update-reference)
# MAGIC 9. [Refresh Options & Incremental Behaviour](#9-refresh-options--incremental-behaviour)
# MAGIC 10. [Troubleshooting](#10-troubleshooting)
# MAGIC 11. [Cleanup](#11-cleanup)

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 1. What We Are Building
# MAGIC
# MAGIC ### Standard View vs Materialized View
# MAGIC
# MAGIC | | Standard View | Materialized View |
# MAGIC |---|---|---|
# MAGIC | Stores data | ❌ No — just a saved SQL query | ✅ Yes — pre-computed Delta table |
# MAGIC | Query time | Slow — re-executes full query on every access | Fast — reads stored result directly |
# MAGIC | Always up to date | ✅ Real-time | ✅ Near real-time (auto-refreshes on source change) |
# MAGIC | Handles INSERT / UPDATE / DELETE | ✅ Always live | ✅ Via `TRIGGER ON UPDATE` |
# MAGIC | Compute cost per query | Higher | Lower (refresh cost is separate) |
# MAGIC
# MAGIC ### Why `TRIGGER ON UPDATE`?
# MAGIC
# MAGIC With `TRIGGER ON UPDATE`, Databricks monitors the source table and automatically refreshes the materialized view whenever it detects a change — no scheduled jobs, no manual refresh commands.
# MAGIC
# MAGIC > **Note on EXPLODE and incremental refresh:**
# MAGIC > `EXPLODE` (used to flatten nested arrays) may not be on Databricks' supported list for incremental refresh.
# MAGIC > If `EXPLAIN CREATE MATERIALIZED VIEW` returns `NOT_INCREMENTALIZABLE`, refreshes will be full recomputes
# MAGIC > rather than row-level incremental. The MV still delivers significant query performance benefits regardless.

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 2. Objects Created
# MAGIC
# MAGIC | Object | Full Name | Type |
# MAGIC |---|---|---|
# MAGIC | Party materialized view | `x_prod.reference_data.party_identifiers_mv` | Materialized View |
# MAGIC | Instrument materialized view | `` `19519_ctg_dev`.refdata.instrument_identifiers_mv `` | Materialized View |
# MAGIC | Party standard view | `x_prod.reference_data.party_identifiers_vw` | Standard View |
# MAGIC | Instrument standard view | `` `19519_ctg_dev`.refdata.instrument_identifiers_vw `` | Standard View |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 3. Files & How to Import
# MAGIC
# MAGIC | File | Purpose | Run order |
# MAGIC |---|---|---|
# MAGIC | `01_standard_view.py` | Creates standard views, measures baseline query time | 1st |
# MAGIC | `02_materialized_view.py` | Creates MVs, validates incremental refresh, benchmarks | 2nd |
# MAGIC | `00_runbook.py` | This notebook — full reference | — |
# MAGIC
# MAGIC ### Importing into Databricks
# MAGIC
# MAGIC 1. In your Databricks workspace, open the **Workspace** sidebar
# MAGIC 2. Navigate to your target folder
# MAGIC 3. Click **⋮ (kebab menu) → Import**
# MAGIC 4. Select the `.py` file
# MAGIC 5. Attach to a **Unity Catalog-enabled Pro or Serverless SQL warehouse**
# MAGIC 6. Run cells **top to bottom** — each cell is labelled and independent
# MAGIC
# MAGIC > ⚠️ **Compute requirement:** Materialized Views require a **Unity Catalog-enabled Pro or Serverless SQL warehouse**.
# MAGIC > Classic compute does not support `CREATE MATERIALIZED VIEW` or incremental refresh.

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 4. Execution Order
# MAGIC
# MAGIC ```
# MAGIC Step 1  →  Run 01_standard_view.py
# MAGIC            - Creates party_identifiers_vw and instrument_identifiers_vw
# MAGIC            - Measures full scan and aggregation query time
# MAGIC            - Record the times printed in the output
# MAGIC
# MAGIC Step 2  →  Run 02_materialized_view.py
# MAGIC            - Enables rowTracking + changeDataFeed on source tables
# MAGIC            - Runs EXPLAIN to check incrementalizability
# MAGIC            - Creates party_identifiers_mv and instrument_identifiers_mv with TRIGGER ON UPDATE
# MAGIC            - Validates data consistency vs standard views
# MAGIC            - Measures same queries against MVs
# MAGIC            - Tests INSERT / UPDATE / DELETE incremental propagation
# MAGIC
# MAGIC Step 3  →  Fill in the summary tables in both notebooks with your recorded times
# MAGIC ```
# MAGIC
# MAGIC ### Within `02_materialized_view.py`, cell order matters:
# MAGIC
# MAGIC | Cell group | What it does | Requires |
# MAGIC |---|---|---|
# MAGIC | PRE-REQUISITE | `ALTER TABLE` to enable row tracking and CDF | Source tables must exist |
# MAGIC | Step 1 | `EXPLAIN CREATE` to check incrementalizability | Pre-requisite complete |
# MAGIC | Steps 2–3 | Create Materialized Views with `TRIGGER ON UPDATE` | Step 1 run (regardless of result) |
# MAGIC | Step 4 | Validate MV metadata and row counts | MVs created and loaded |
# MAGIC | Step 5 | Data consistency check vs standard view | Standard view from notebook 01 must exist |
# MAGIC | Steps 6–7 | Benchmark timing | MV initial load must be complete |
# MAGIC | Step 8 | INSERT / UPDATE / DELETE incremental test | MV must be running with TRIGGER ON UPDATE |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 5. Validation Checklist
# MAGIC
# MAGIC ### Pre-requisite properties
# MAGIC
# MAGIC After running the `ALTER TABLE` cells, run `SHOW TBLPROPERTIES` and confirm:
# MAGIC
# MAGIC ```
# MAGIC delta.enableDeletionVectors  =  true
# MAGIC delta.enableRowTracking      =  true
# MAGIC delta.enableChangeDataFeed   =  true
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Incrementalizability result
# MAGIC
# MAGIC | Output from EXPLAIN | Meaning | Effect on MV |
# MAGIC |---|---|---|
# MAGIC | `INCREMENTALIZABLE` | Query supports row-level incremental refresh | Refreshes process only changed rows |
# MAGIC | `NOT_INCREMENTALIZABLE — OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE blocks direct incremental refresh | Refreshes are full recomputes — MV still works and delivers query performance benefit |
# MAGIC | `NOT_INCREMENTALIZABLE — ROW_TRACKING_NOT_ENABLED` | Row tracking not enabled | Re-run the `ALTER TABLE` pre-requisite cell |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### MV metadata check
# MAGIC
# MAGIC After creation, `DESCRIBE EXTENDED` must show:
# MAGIC
# MAGIC ```
# MAGIC Type                =  MATERIALIZED VIEW
# MAGIC Refresh Schedule    =  TRIGGER ON UPDATE
# MAGIC Last Refreshed      =  <recent timestamp>
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Refresh type check
# MAGIC
# MAGIC After any refresh, query the event log using the cell below.
# MAGIC
# MAGIC | `message` value | Meaning |
# MAGIC |---|---|
# MAGIC | `ROW_BASED` | ✅ True incremental — only changed rows processed |
# MAGIC | `PARTITION_OVERWRITE` | ✅ Incremental at partition level |
# MAGIC | `NO_OP` | ℹ️ No changes in source — nothing to do |
# MAGIC | `COMPLETE_RECOMPUTE` | ⚠️ Full refresh — expected if EXPLODE is not incrementalizable |

# COMMAND ----------
# MAGIC %sql
-- Run after any refresh to check whether it was incremental or a full recompute
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ### Data consistency check
# MAGIC
# MAGIC The `EXCEPT` query in Step 5 of `02_materialized_view.py` must return **0 rows**.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Incremental update test (Step 8)
# MAGIC
# MAGIC | Operation | Expected result |
# MAGIC |---|---|
# MAGIC | `INSERT TEST_ECI_99999` | Row appears in MV within 1–2 minutes |
# MAGIC | `UPDATE country_of_domicile = 'US'` | Updated value visible in MV within 1–2 minutes |
# MAGIC | `DELETE TEST_ECI_99999` | Row gone from MV within 1–2 minutes |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 6. How Incremental Refresh Works
# MAGIC
# MAGIC ### The flow for each source change
# MAGIC
# MAGIC ```
# MAGIC 1. Row inserted / updated / deleted in source party or instrument table
# MAGIC 2. Delta Change Data Feed records the change in the transaction log
# MAGIC 3. Databricks detects the CDF event (polling every ~1 minute minimum)
# MAGIC 4. TRIGGER ON UPDATE fires — MV refreshes with only the changed rows
# MAGIC 5. Query against the MV returns the updated result
# MAGIC ```
# MAGIC
# MAGIC ### Typical latency
# MAGIC
# MAGIC **1–5 minutes** from source change to MV updated — depends on cluster warm-up and trigger polling interval (minimum 1 minute).
# MAGIC
# MAGIC ### Refresh policy options
# MAGIC
# MAGIC | Approach | SQL clause | Behaviour |
# MAGIC |---|---|---|
# MAGIC | Auto (default, this runbook) | `TRIGGER ON UPDATE` | Databricks picks incremental or full based on cost model |
# MAGIC | Strict incremental | `REFRESH POLICY INCREMENTAL (STRICT)` | Errors rather than falling back to full recompute |
# MAGIC | Time-based schedule | `SCHEDULE EVERY 1 HOUR` | Refreshes on a fixed interval regardless of source changes |
# MAGIC | Manual only | _(no clause)_ | Only refreshes when `REFRESH MATERIALIZED VIEW` is run explicitly |
# MAGIC
# MAGIC ### Throttling (optional — if source updates too frequently)

# COMMAND ----------
# MAGIC %sql
-- Cap how often the MV refreshes even if source changes more frequently
ALTER MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  ALTER TRIGGER ON UPDATE AT MOST EVERY INTERVAL 5 MINUTES;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 7. Performance Comparison Guide
# MAGIC
# MAGIC ### Summary table — fill in after running both notebooks
# MAGIC
# MAGIC | Query | Standard View (sec) | Materialized View (sec) | Speedup factor |
# MAGIC |---|---|---|---|
# MAGIC | `party` — full scan | | | |
# MAGIC | `instrument` — full scan | | | |
# MAGIC | `party` — aggregation | | | |
# MAGIC | `instrument` — aggregation | | | |
# MAGIC
# MAGIC **Speedup factor** = Standard View time ÷ Materialized View time
# MAGIC
# MAGIC ### Where to find precise metrics
# MAGIC
# MAGIC **SQL Editor → Query History** — each entry shows exact duration, DBU consumption, and bytes scanned.
# MAGIC
# MAGIC ### What to expect
# MAGIC
# MAGIC | Query type | Expected MV advantage |
# MAGIC |---|---|
# MAGIC | Full table scan | Moderate — MV skips EXPLODE overhead at query time |
# MAGIC | Aggregation | Large — MV serves pre-flattened data; no array expansion needed |
# MAGIC | Filtered lookup | Moderate — MV benefits from Delta file pruning on stored data |
# MAGIC | Repeated queries | Large — standard view re-executes from scratch every time; MV does not |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 8. TRIGGER ON UPDATE Reference
# MAGIC
# MAGIC | Property | Detail |
# MAGIC |---|---|
# MAGIC | Minimum trigger interval | 1 minute |
# MAGIC | Maximum upstream tables per MV | 10 |
# MAGIC | Maximum upstream views per MV | 30 |
# MAGIC | Maximum MVs with TRIGGER ON UPDATE per workspace | 1,000 (contact Databricks Support if more needed) |
# MAGIC | Feature status | Beta (as of October 2025) |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 9. Refresh Options & Incremental Behaviour
# MAGIC
# MAGIC ### The two independent questions
# MAGIC
# MAGIC Every materialized view refresh involves two separate decisions:
# MAGIC
# MAGIC ```
# MAGIC Question 1 — WHEN does the refresh fire?     → your refresh option controls this
# MAGIC Question 2 — HOW does it process the data?   → EXPLAIN CREATE result controls this
# MAGIC ```
# MAGIC
# MAGIC These are **completely independent**. Your choice of refresh option has no effect on whether
# MAGIC the refresh is incremental or a full recompute. That decision comes entirely from `EXPLAIN CREATE`.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### All refresh options are subject to the same EXPLAIN CREATE result
# MAGIC
# MAGIC | Refresh Option | Auto-fires on source change? | If INCREMENTALIZABLE | If NOT_INCREMENTALIZABLE |
# MAGIC |---|---|---|---|
# MAGIC | `TRIGGER ON UPDATE` | ✅ Yes — within ~1 min | Incremental refresh | **Full recompute** |
# MAGIC | `SCHEDULE EVERY` | ⏰ On next interval tick | Incremental refresh | **Full recompute** |
# MAGIC | `SCHEDULE CRON` | ⏰ At scheduled time | Incremental refresh | **Full recompute** |
# MAGIC | Manual `REFRESH` | ❌ Only when you run it | Incremental refresh | **Full recompute** |
# MAGIC | `REFRESH ASYNC` | ❌ Only when you run it | Incremental refresh | **Full recompute** |
# MAGIC | Lakeflow Job | ⏰ Only when job runs | Incremental refresh | **Full recompute** |
# MAGIC | `REFRESH FULL` | ❌ Only when you run it | Always full recompute — ignores EXPLAIN result by design | Always full recompute |
# MAGIC
# MAGIC > **Key point:** `TRIGGER ON UPDATE` does not guarantee incremental refresh. It only guarantees *automatic* firing.
# MAGIC > The refresh method is determined solely by the query.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### What NOT_INCREMENTALIZABLE means in practice
# MAGIC
# MAGIC If `EXPLAIN CREATE` returns `NOT_INCREMENTALIZABLE` (which is expected with `EXPLODE`):
# MAGIC
# MAGIC - **Every single refresh is a full recompute** — no exceptions
# MAGIC - Even a single-row INSERT in the source causes Databricks to scan the entire source table, re-explode every array, and rewrite all rows in the MV
# MAGIC - This applies regardless of which refresh option triggered it
# MAGIC - Row tracking and CDF being enabled does not change this outcome
# MAGIC
# MAGIC ```
# MAGIC Source change (e.g. 1 row inserted)
# MAGIC     │
# MAGIC     ▼
# MAGIC Refresh fires (via any option)
# MAGIC     │
# MAGIC     ▼
# MAGIC NOT_INCREMENTALIZABLE → Full recompute always
# MAGIC     ┌──────────────────────────────────────────┐
# MAGIC     │  Clear entire MV                         │
# MAGIC     │  Re-execute full query from scratch      │
# MAGIC     │  Rewrite ALL rows back into the MV       │
# MAGIC     └──────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### What INCREMENTALIZABLE means in practice
# MAGIC
# MAGIC If `EXPLAIN CREATE` returns `INCREMENTALIZABLE`, Databricks has the *option* to refresh incrementally —
# MAGIC but it is not guaranteed. Databricks runs a **cost model** on each refresh and may still choose a full
# MAGIC recompute if it calculates that to be cheaper.
# MAGIC
# MAGIC ```
# MAGIC INCREMENTALIZABLE
# MAGIC     │
# MAGIC     ▼
# MAGIC Databricks cost model runs
# MAGIC     ├── Incremental is cheaper → Incremental refresh ✅ (only changed rows)
# MAGIC     └── Full recompute is cheaper → Full recompute ⚠️  (all rows, but still correct)
# MAGIC ```
# MAGIC
# MAGIC | EXPLAIN result | Refresh method |
# MAGIC |---|---|
# MAGIC | `NOT_INCREMENTALIZABLE` | Always full recompute — locked in, no choice |
# MAGIC | `INCREMENTALIZABLE` | Usually incremental — but Databricks may still choose full recompute |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Refresh option comparison — auto-sync with master table
# MAGIC
# MAGIC When a row is inserted, updated, or deleted in the `party` or `instrument` source table:
# MAGIC
# MAGIC | Option | MV syncs automatically? | Staleness window |
# MAGIC |---|---|---|
# MAGIC | `TRIGGER ON UPDATE` | ✅ Yes | ~1–2 minutes |
# MAGIC | `SCHEDULE EVERY 1 HOUR` | ⏰ Eventually | Up to 1 hour |
# MAGIC | `SCHEDULE CRON` (daily 8am) | ⏰ Eventually | Up to 24 hours |
# MAGIC | Manual `REFRESH` | ❌ No | Until you run the command |
# MAGIC | Lakeflow Job | ⏰ Eventually | Depends on job schedule |
# MAGIC
# MAGIC `TRIGGER ON UPDATE` is the only option where a change to the master table automatically
# MAGIC and immediately propagates to the MV without human or scheduled intervention.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Options to fix NOT_INCREMENTALIZABLE (if true incremental is required)
# MAGIC
# MAGIC | Approach | How | Trade-off |
# MAGIC |---|---|---|
# MAGIC | Pre-flatten arrays in source | Store data already flat so no `EXPLODE` needed in the MV query | Requires source table schema change |
# MAGIC | Streaming Table as intermediate layer | Streaming Table handles CDC; MV sits on top and does `EXPLODE` | Adds one object to manage |
# MAGIC | Accept full recompute | Keep current design — `TRIGGER ON UPDATE` still auto-fires, just reprocesses all rows | Higher compute cost per refresh on large tables |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 10. Troubleshooting
# MAGIC
# MAGIC | Problem | Likely cause | Fix |
# MAGIC |---|---|---|
# MAGIC | `EXPLAIN` returns `NOT_INCREMENTALIZABLE — OPERATOR_NOT_INCREMENTALIZABLE` | EXPLODE is not on Databricks' incremental-supported clause list | Expected — MV still works, refreshes will be full recomputes |
# MAGIC | `EXPLAIN` returns `ROW_TRACKING_NOT_ENABLED` | `ALTER TABLE` pre-requisite not applied | Re-run the `ALTER TABLE` cells in `02_materialized_view.py` |
# MAGIC | event_log shows `COMPLETE_RECOMPUTE` | EXPLODE blocks incremental refresh | Expected if EXPLAIN returned `NOT_INCREMENTALIZABLE` |
# MAGIC | MV row count does not match standard view | Initial load still in progress | Wait a few minutes and recheck; or run `REFRESH MATERIALIZED VIEW` |
# MAGIC | Trigger not firing after source change | Less than 1 min since last trigger, or CDF not enabled | Confirm `delta.enableChangeDataFeed = true`, wait at least 1 minute |
# MAGIC | `CREATE MATERIALIZED VIEW` fails — permission error | Missing `CREATE MATERIALIZED VIEW` privilege | Run: `GRANT CREATE MATERIALIZED VIEW ON SCHEMA <schema> TO <user>` |
# MAGIC | Cannot query MV from a notebook | Incompatible compute attached | Use a SQL warehouse or Standard/Dedicated access mode cluster on DBR 15.4+ |
# MAGIC | `SHOW TBLPROPERTIES` does not show CDF | Table is not a Unity Catalog managed Delta table | Confirm table catalog and contact your data platform team |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## 11. Cleanup
# MAGIC
# MAGIC Run only when you want to permanently remove all objects created by this project.
# MAGIC
# MAGIC > ⚠️ Dropping a Materialized View deletes the stored data and the associated serverless pipeline permanently.

# COMMAND ----------
# MAGIC %sql
-- Uncomment and run only when intentionally removing all project objects

-- DROP MATERIALIZED VIEW IF EXISTS x_prod.reference_data.party_identifiers_mv;
-- DROP MATERIALIZED VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_mv;
-- DROP VIEW IF EXISTS x_prod.reference_data.party_identifiers_vw;
-- DROP VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_vw;
