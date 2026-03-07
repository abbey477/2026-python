# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # 🚀 Materialized View — Setup, Incremental Refresh & Benchmark
# MAGIC
# MAGIC **Notebook:** `02_materialized_view`
# MAGIC **Run after `01_standard_view.py`** — uses the same queries so times are directly comparable.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## What is a Materialized View?
# MAGIC A materialized view **physically stores pre-computed query results** as a Delta table.
# MAGIC Unlike a standard view which re-executes its query on every access, a materialized view
# MAGIC serves pre-computed data — dramatically reducing query latency.
# MAGIC
# MAGIC When the source table changes (INSERT, UPDATE, DELETE), Databricks automatically detects
# MAGIC the change and refreshes only the affected rows — this is **incremental refresh**.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC | Property | Value |
# MAGIC |---|---|
# MAGIC | Party MV | `x_prod.reference_data.party_identifiers_mv` |
# MAGIC | Instrument MV | `` `19519_ctg_dev`.refdata.instrument_identifiers_mv `` |
# MAGIC | Data stored | ✅ Yes — pre-computed Delta table |
# MAGIC | Refresh mode | `TRIGGER ON UPDATE` — auto-refreshes when source changes |
# MAGIC | Incremental | ✅ Only changed rows processed on each refresh |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## PRE-REQUISITE — Enable Source Table Optimisations
# MAGIC
# MAGIC These Delta table properties enable incremental refresh.
# MAGIC They must be set on each source table **before** creating the Materialized View.
# MAGIC
# MAGIC | Property | Why it is needed |
# MAGIC |---|---|
# MAGIC | `delta.enableRowTracking` | Allows Databricks to identify which rows changed since the last refresh |
# MAGIC | `delta.enableChangeDataFeed` | Exposes the CDC feed so the MV can read only new changes |
# MAGIC | `delta.enableDeletionVectors` | Enables efficient physical deletes (needed for DELETE propagation) |
# MAGIC
# MAGIC > ✅ **Safe to re-run** — idempotent. Running on an already-configured table has no effect.

# COMMAND ----------
# MAGIC %sql
-- Enable optimisations on the party source table
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
  delta.enableDeletionVectors = true,
  delta.enableRowTracking     = true,
  delta.enableChangeDataFeed  = true
);

# COMMAND ----------
# MAGIC %sql
-- Enable optimisations on the instrument source table
ALTER TABLE `19519_ctg_dev`.refdata.instrument
SET TBLPROPERTIES (
  delta.enableDeletionVectors = true,
  delta.enableRowTracking     = true,
  delta.enableChangeDataFeed  = true
);

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Confirm Properties Were Applied
# MAGIC
# MAGIC Look for all three properties set to `true` in the output below.

# COMMAND ----------
# MAGIC %sql
SHOW TBLPROPERTIES x_prod.reference_data.party;

# COMMAND ----------
# MAGIC %sql
SHOW TBLPROPERTIES `19519_ctg_dev`.refdata.instrument;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 1 — Check Incrementalizability
# MAGIC
# MAGIC `EXPLAIN CREATE MATERIALIZED VIEW` tells us whether Databricks can incrementally refresh
# MAGIC these specific queries. Run it before creating anything.
# MAGIC
# MAGIC | Result | Meaning | What to do |
# MAGIC |---|---|---|
# MAGIC | `INCREMENTALIZABLE` | Query supports incremental refresh directly on the source | Proceed — Steps 2 and 3 will work as written |
# MAGIC | `NOT_INCREMENTALIZABLE` | An operator (likely EXPLODE) blocks direct incremental refresh | MV will still be created and will work — but refreshes will be full recomputes rather than incremental |
# MAGIC
# MAGIC > 💡 Even if `NOT_INCREMENTALIZABLE`, the MV is still worth creating for **query performance** —
# MAGIC > it still serves pre-computed data. Only the refresh mechanism differs.

# COMMAND ----------
# MAGIC %sql
-- Check whether the party query can be incrementally refreshed
EXPLAIN CREATE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
AS
SELECT
    cp.__cob_date,
    cp.eci,
    cp.country_of_domicile,
    cp.country_of_asset,
    cp.organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM x_prod.reference_data.party cp
LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids;

# COMMAND ----------
# MAGIC %sql
-- Check whether the instrument query can be incrementally refreshed
EXPLAIN CREATE MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv
AS
SELECT
    alt_id.instrumentId, alt_id.isAssetExpired, alt_id.statusCode,
    alt_id.assetId, alt_id.assetIdType, alt_id.sourceId,
    alt_id.rdrDerivedKey, alt_id.cerdCorpIdentifier, alt_id.sourceSystemName,
    instrument.__cob_date, instrument.__START_AT, instrument.__END_AT,
    instrument.__txn_id_long, instrument.__slice
FROM `19519_ctg_dev`.refdata.instrument instrument
LATERAL VIEW EXPLODE(instrument.alternateIdentifiers) exploded_table AS alt_id;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 2 — Create Materialized View: `party_identifiers_mv`
# MAGIC
# MAGIC - `TRIGGER ON UPDATE` means Databricks **automatically monitors the source table** and refreshes
# MAGIC   this MV whenever a change is detected — no manual refresh required.
# MAGIC - The initial `CREATE` triggers a full data load. All subsequent refreshes attempt to be incremental.
# MAGIC - The view is backed by a **serverless pipeline** created automatically by Databricks.

# COMMAND ----------
# MAGIC %sql
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  TRIGGER ON UPDATE
  COMMENT 'Materialized view — flattened party alternate identifiers. Auto-refreshes when party source table changes.'
AS
SELECT
    cp.__cob_date,
    cp.eci,
    cp.country_of_domicile,
    cp.country_of_asset,
    cp.organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM x_prod.reference_data.party cp
LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids;

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 3 — Create Materialized View: `instrument_identifiers_mv`

# COMMAND ----------
# MAGIC %sql
CREATE OR REPLACE MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv
  TRIGGER ON UPDATE
  COMMENT 'Materialized view — flattened instrument alternate identifiers. Auto-refreshes when instrument source table changes.'
AS
SELECT
    alt_id.instrumentId          AS instrumentId,
    alt_id.isAssetExpired        AS isAssetExpired,
    alt_id.statusCode            AS statusCode,
    alt_id.assetId               AS assetId,
    alt_id.assetIdType           AS assetIdType,
    alt_id.sourceId              AS sourceId,
    alt_id.rdrDerivedKey         AS rdrDerivedKey,
    alt_id.cerdCorpIdentifier    AS cerdCorpIdentifier,
    alt_id.sourceSystemName      AS sourceSystemName,
    inst.__cob_date,
    inst.__START_AT,
    inst.__END_AT,
    inst.__txn_id_long,
    inst.__slice
FROM `19519_ctg_dev`.refdata.instrument inst
LATERAL VIEW EXPLODE(inst.alternateIdentifiers) exploded_table AS alt_id;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 4 — Validate: Confirm MVs Were Created Correctly
# MAGIC
# MAGIC `DESCRIBE EXTENDED` shows the full MV metadata. Key things to check:
# MAGIC - **Type** = `MATERIALIZED VIEW`
# MAGIC - **Refresh Schedule** = `TRIGGER ON UPDATE`
# MAGIC - **Last Refreshed** = a recent timestamp (confirms initial load completed)

# COMMAND ----------
# MAGIC %sql
DESCRIBE EXTENDED x_prod.reference_data.party_identifiers_mv;

# COMMAND ----------
# MAGIC %sql
DESCRIBE EXTENDED `19519_ctg_dev`.refdata.instrument_identifiers_mv;

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Row Counts
# MAGIC
# MAGIC Counts should match (or closely match) the standard view counts from `01_standard_view.py`.

# COMMAND ----------
# MAGIC %sql
SELECT
  'party_identifiers_mv'      AS mv_name,
  COUNT(*)                    AS row_count
FROM x_prod.reference_data.party_identifiers_mv

UNION ALL

SELECT
  'instrument_identifiers_mv' AS mv_name,
  COUNT(*)                    AS row_count
FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv;

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Confirm Refresh Type
# MAGIC
# MAGIC After creation (and after any subsequent refresh), query the pipeline event log to confirm
# MAGIC whether the refresh was incremental or a full recompute.
# MAGIC
# MAGIC | `message` value | Meaning |
# MAGIC |---|---|
# MAGIC | `ROW_BASED` | ✅ True incremental — only changed rows processed |
# MAGIC | `PARTITION_OVERWRITE` | ✅ Incremental at partition level |
# MAGIC | `NO_OP` | ℹ️ No changes in source — nothing to refresh |
# MAGIC | `COMPLETE_RECOMPUTE` | ⚠️ Full refresh — expected if EXPLODE is not incrementalizable |

# COMMAND ----------
# MAGIC %sql
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;

# COMMAND ----------
# MAGIC %sql
SELECT timestamp, message
FROM event_log(TABLE(`19519_ctg_dev`.refdata.instrument_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 5 — Data Consistency Check
# MAGIC
# MAGIC Confirm the Materialized View returns **identical results** to the standard view.
# MAGIC The `EXCEPT` query returns rows present in the MV but not in the view — expected result is **0 rows**.

# COMMAND ----------
# MAGIC %sql
-- Party: row count comparison
SELECT
    (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_mv)  AS mv_count,
    (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_vw)  AS vw_count,
    CASE
        WHEN (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_mv)
           = (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_vw)
        THEN 'MATCH - data is consistent'
        ELSE 'MISMATCH - investigate before benchmarking'
    END AS status;

# COMMAND ----------
# MAGIC %sql
-- Instrument: row count comparison
SELECT
    (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv)  AS mv_count,
    (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw)  AS vw_count,
    CASE
        WHEN (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv)
           = (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw)
        THEN 'MATCH - data is consistent'
        ELSE 'MISMATCH - investigate before benchmarking'
    END AS status;

# COMMAND ----------
# MAGIC %sql
-- Deep check: rows in MV that are NOT in the standard view (expected: 0 rows)
SELECT mv.*, 'MV_ONLY' AS source
FROM x_prod.reference_data.party_identifiers_mv mv
LIMIT 100
EXCEPT
SELECT vw.*, 'MV_ONLY' AS source
FROM x_prod.reference_data.party_identifiers_vw vw
LIMIT 100;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 6 — ⏱️ Benchmark: Full Scan
# MAGIC
# MAGIC The MV **does not** re-execute the EXPLODE or scan the source on each query.
# MAGIC It reads the pre-computed, stored Delta table directly.
# MAGIC
# MAGIC > ⚠️ Run this cell **twice** and record the **second run** for a fair comparison.

# COMMAND ----------

import time

# ── Party MV full scan ─────────────────────────────────────────
start = time.time()
party_df    = spark.sql("SELECT * FROM x_prod.reference_data.party_identifiers_mv")
party_count = party_df.count()
party_time  = time.time() - start

# ── Instrument MV full scan ────────────────────────────────────
start = time.time()
instr_df    = spark.sql("SELECT * FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv")
instr_count = instr_df.count()
instr_time  = time.time() - start

print("=" * 55)
print("  MATERIALIZED VIEW — FULL SCAN BENCHMARK")
print("=" * 55)
print(f"  party_identifiers_mv")
print(f"    Rows returned : {party_count:,}")
print(f"    Elapsed time  : {party_time:.2f} seconds  <-- record this")
print()
print(f"  instrument_identifiers_mv")
print(f"    Rows returned : {instr_count:,}")
print(f"    Elapsed time  : {instr_time:.2f} seconds  <-- record this")
print("=" * 55)
print("  --> Compare these times against 01_standard_view.py")

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 7 — ⏱️ Benchmark: Aggregation Query
# MAGIC
# MAGIC The MV serves the pre-flattened data directly — no EXPLODE overhead at query time.
# MAGIC This is where the largest speedup over the standard view is typically seen.

# COMMAND ----------

import time

# ── Party MV aggregation ───────────────────────────────────────
start = time.time()
party_agg = spark.sql("""
    SELECT identifier_type, COUNT(*) AS cnt
    FROM x_prod.reference_data.party_identifiers_mv
    GROUP BY identifier_type
    ORDER BY cnt DESC
""")
party_agg.show(truncate=False)
party_agg_time = time.time() - start

# ── Instrument MV aggregation ──────────────────────────────────
start = time.time()
instr_agg = spark.sql("""
    SELECT assetIdType, COUNT(*) AS cnt
    FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv
    GROUP BY assetIdType
    ORDER BY cnt DESC
""")
instr_agg.show(truncate=False)
instr_agg_time = time.time() - start

print("=" * 55)
print("  MATERIALIZED VIEW — AGGREGATION BENCHMARK")
print("=" * 55)
print(f"  party aggregation     : {party_agg_time:.2f} seconds  <-- record this")
print(f"  instrument aggregation: {instr_agg_time:.2f} seconds  <-- record this")
print("=" * 55)

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 8 — End-to-End Incremental Update Test
# MAGIC
# MAGIC This section proves the MV stays in sync when the source table changes.
# MAGIC After each DML operation on the source, `TRIGGER ON UPDATE` detects the change
# MAGIC and automatically refreshes the MV — no manual refresh needed.
# MAGIC
# MAGIC > ⏳ After each INSERT / UPDATE / DELETE, wait **1-2 minutes** before checking the MV.
# MAGIC > This is the TRIGGER ON UPDATE polling interval (minimum 1 minute).

# COMMAND ----------
# MAGIC %md
# MAGIC ### 8A — Baseline Row Count Before Test

# COMMAND ----------
# MAGIC %sql
SELECT COUNT(*) AS row_count_before_test
FROM x_prod.reference_data.party_identifiers_mv;

# COMMAND ----------
# MAGIC %md
# MAGIC ### 8B — Test INSERT

# COMMAND ----------
# MAGIC %sql
-- Insert a test record into the source party table
-- Adjust struct field values to match your actual party table schema if needed
INSERT INTO x_prod.reference_data.party
VALUES (
    current_date(),
    'TEST_ECI_99999',
    'GB',
    'GB',
    named_struct('country_of_incorporation', 'GB'),
    array(named_struct('identifier_type', 'TEST_TYPE', 'identifier_value', 'TEST_VALUE'))
);

# COMMAND ----------
# MAGIC %md
# MAGIC > ⏳ **Wait 1-2 minutes** for `TRIGGER ON UPDATE` to fire, then run the next cell.

# COMMAND ----------
# MAGIC %sql
-- Confirm the new row appeared in the MV
-- Expected: 1 row with eci = 'TEST_ECI_99999'
SELECT * FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### 8C — Test UPDATE

# COMMAND ----------
# MAGIC %sql
UPDATE x_prod.reference_data.party
SET country_of_domicile = 'US'
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC > ⏳ **Wait 1-2 minutes**, then run the next cell.

# COMMAND ----------
# MAGIC %sql
-- Confirm the update is visible in the MV
-- Expected: country_of_domicile = 'US'
SELECT eci, country_of_domicile
FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### 8D — Test DELETE

# COMMAND ----------
# MAGIC %sql
DELETE FROM x_prod.reference_data.party
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC > ⏳ **Wait 1-2 minutes**, then run the next cell.

# COMMAND ----------
# MAGIC %sql
-- Confirm the row is gone from the MV
-- Expected: 0
SELECT COUNT(*) AS should_be_zero
FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Event Log After Incremental Test
# MAGIC
# MAGIC Confirm the refreshes triggered by the INSERT / UPDATE / DELETE were incremental.

# COMMAND ----------
# MAGIC %sql
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 10;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Final Summary
# MAGIC
# MAGIC Fill in from Steps 6-7 and compare against `01_standard_view.py`:
# MAGIC
# MAGIC | Query | Standard View (sec) | Materialized View (sec) | Speedup |
# MAGIC |---|---|---|---|
# MAGIC | `party` — full scan | _(from notebook 01)_ | _(from step 6)_ | _(calculate: 01 / 02)_ |
# MAGIC | `instrument` — full scan | _(from notebook 01)_ | _(from step 6)_ | _(calculate: 01 / 02)_ |
# MAGIC | `party` — aggregation | _(from notebook 01)_ | _(from step 7)_ | _(calculate: 01 / 02)_ |
# MAGIC | `instrument` — aggregation | _(from notebook 01)_ | _(from step 7)_ | _(calculate: 01 / 02)_ |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Key Takeaways for Reviewers
# MAGIC
# MAGIC | Aspect | Standard View | Materialized View |
# MAGIC |---|---|---|
# MAGIC | Data stored | None | Pre-computed Delta table |
# MAGIC | Query time | Slow — full scan + EXPLODE on every access | Fast — reads stored result |
# MAGIC | Data freshness | Always real-time | Near real-time via TRIGGER ON UPDATE |
# MAGIC | Handles INSERT / UPDATE / DELETE | Yes — always live | Yes — auto-refreshes on source change |
# MAGIC | Best for | Ad-hoc, infrequent, real-time queries | Dashboards, repeated queries, large tables |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Manual Refresh Commands (if ever needed)
# MAGIC
# MAGIC ```sql
# MAGIC -- Standard incremental refresh
# MAGIC REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;
# MAGIC REFRESH MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv;
# MAGIC
# MAGIC -- Force full recompute (clears all stored data and rebuilds from scratch)
# MAGIC REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv FULL;
# MAGIC REFRESH MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv FULL;
# MAGIC ```
# MAGIC
# MAGIC ### Cleanup (only if removing everything)
# MAGIC
# MAGIC ```sql
# MAGIC DROP MATERIALIZED VIEW IF EXISTS x_prod.reference_data.party_identifiers_mv;
# MAGIC DROP MATERIALIZED VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_mv;
# MAGIC DROP VIEW IF EXISTS x_prod.reference_data.party_identifiers_vw;
# MAGIC DROP VIEW IF EXISTS `19519_ctg_dev`.refdata.instrument_identifiers_vw;
# MAGIC ```
