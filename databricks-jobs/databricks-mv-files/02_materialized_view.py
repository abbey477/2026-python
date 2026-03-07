# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # 🚀 Materialized View — Setup, Incremental Refresh & Benchmark
# MAGIC
# MAGIC **Notebook:** `02_materialized_view`
# MAGIC **Purpose:** Set up the full Materialized View architecture with true incremental updates, then benchmark query performance against the standard view baseline from `01_standard_view.py`.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Architecture
# MAGIC
# MAGIC ```
# MAGIC Source Delta Table
# MAGIC     └─► Streaming Table   ← handles CDC: INSERT / UPDATE / DELETE incrementally
# MAGIC             └─► Materialized View  ← EXPLODE flattening + TRIGGER ON UPDATE
# MAGIC ```
# MAGIC
# MAGIC > **Why two layers?**
# MAGIC > `EXPLODE` (used to flatten arrays) is not on Databricks' supported list for direct incremental refresh.
# MAGIC > The Streaming Table layer absorbs the CDC changes incrementally. The Materialized View on top
# MAGIC > then does the EXPLODE over an already-incremental dataset — giving true end-to-end incremental processing.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC | Object | Name | Purpose |
# MAGIC |---|---|---|
# MAGIC | Streaming Table | `x_prod.reference_data.party_stream` | CDC layer for party |
# MAGIC | Streaming Table | `` `19519_ctg_dev`.refdata.instrument_stream `` | CDC layer for instrument |
# MAGIC | Materialized View | `x_prod.reference_data.party_identifiers_mv` | Flattened party identifiers |
# MAGIC | Materialized View | `` `19519_ctg_dev`.refdata.instrument_identifiers_mv `` | Flattened instrument identifiers |

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## PRE-REQUISITE — Enable Source Table Optimisations
# MAGIC
# MAGIC These three Delta properties **must** be enabled on each source table before creating the Streaming Table or Materialized View:
# MAGIC
# MAGIC | Property | Why it's needed |
# MAGIC |---|---|
# MAGIC | `delta.enableRowTracking` | Allows Databricks to track individual row changes for incremental refresh |
# MAGIC | `delta.enableChangeDataFeed` | Enables the CDC feed that the Streaming Table reads from |
# MAGIC | `delta.enableDeletionVectors` | Enables efficient physical deletes (required for GDPR / data compliance) |
# MAGIC
# MAGIC > ✅ Safe to re-run — this operation is idempotent (running it again on an already-configured table has no effect).

# COMMAND ----------
# MAGIC %sql
-- Enable optimisations on party source table
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
  delta.enableDeletionVectors = true,
  delta.enableRowTracking     = true,
  delta.enableChangeDataFeed  = true
);

# COMMAND ----------
# MAGIC %sql
-- Enable optimisations on instrument source table
ALTER TABLE `19519_ctg_dev`.refdata.instrument
SET TBLPROPERTIES (
  delta.enableDeletionVectors = true,
  delta.enableRowTracking     = true,
  delta.enableChangeDataFeed  = true
);

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Confirm Properties Applied
# MAGIC
# MAGIC Look for `delta.enableDeletionVectors`, `delta.enableRowTracking`, and `delta.enableChangeDataFeed` all set to `true`.

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
# MAGIC Before creating anything, we run `EXPLAIN CREATE MATERIALIZED VIEW` to check whether Databricks
# MAGIC can incrementally refresh these specific queries.
# MAGIC
# MAGIC | Result | Meaning | Action |
# MAGIC |---|---|---|
# MAGIC | `INCREMENTALIZABLE` | MV can refresh directly against Delta source | You can optionally skip the Streaming Table layer |
# MAGIC | `NOT_INCREMENTALIZABLE` | EXPLODE or another operator blocks direct incremental refresh | The Streaming Table architecture (Steps 2–3) is required |

# COMMAND ----------
# MAGIC %sql
-- Check party query incrementalizability
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
-- Check instrument query incrementalizability
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
# MAGIC ## Step 2 — Create Streaming Tables (CDC Layer)
# MAGIC
# MAGIC Streaming Tables continuously ingest changes from the source Delta tables using the Change Data Feed.
# MAGIC They capture **inserts, updates, and deletes** incrementally — only processing new data since the last run.
# MAGIC
# MAGIC > 💡 Think of a Streaming Table as a continuously updated copy of the source, tracking only what changed.
# MAGIC > The Materialized View in Step 3 is built on top of this — not directly on the source.

# COMMAND ----------
# MAGIC %sql
-- Streaming Table for party: captures all changes incrementally from source
CREATE OR REFRESH STREAMING TABLE x_prod.reference_data.party_stream
  COMMENT 'CDC streaming table — captures all changes from party source table incrementally'
AS SELECT
    __cob_date,
    eci,
    country_of_domicile,
    country_of_asset,
    organization,
    alternate_identifiers
FROM STREAM(x_prod.reference_data.party);

# COMMAND ----------
# MAGIC %sql
-- Streaming Table for instrument: captures all changes incrementally from source
CREATE OR REFRESH STREAMING TABLE `19519_ctg_dev`.refdata.instrument_stream
  COMMENT 'CDC streaming table — captures all changes from instrument source table incrementally'
AS SELECT
    __cob_date,
    __START_AT,
    __END_AT,
    __txn_id_long,
    __slice,
    alternateIdentifiers
FROM STREAM(`19519_ctg_dev`.refdata.instrument);

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Confirm Streaming Tables Have Data
# MAGIC
# MAGIC Row counts should match (or closely match) the source tables on the first load.

# COMMAND ----------
# MAGIC %sql
SELECT
  'party_stream'      AS table_name,
  COUNT(*)            AS row_count
FROM x_prod.reference_data.party_stream

UNION ALL

SELECT
  'instrument_stream' AS table_name,
  COUNT(*)            AS row_count
FROM `19519_ctg_dev`.refdata.instrument_stream;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 3 — Create Materialized Views
# MAGIC
# MAGIC The Materialized Views are built **on top of the Streaming Tables** (not directly on the source).
# MAGIC This is the key design decision that enables true incremental refresh with `EXPLODE`.
# MAGIC
# MAGIC **`TRIGGER ON UPDATE`** means: Databricks monitors the upstream Streaming Table and automatically
# MAGIC refreshes this Materialized View whenever new changes are detected — no manual refresh needed.
# MAGIC
# MAGIC > ⏳ The initial create runs a full load (once). All subsequent refreshes are incremental.

# COMMAND ----------
# MAGIC %sql
-- Materialized View: party_identifiers_mv
-- Built on party_stream (not directly on party source table)
-- TRIGGER ON UPDATE = auto-refreshes when party source changes
CREATE OR REPLACE MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv
  TRIGGER ON UPDATE
  COMMENT 'Flattened party alternate identifiers. Auto-refreshes incrementally when party source changes.'
AS
SELECT
    ps.__cob_date,
    ps.eci,
    ps.country_of_domicile,
    ps.country_of_asset,
    ps.organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM x_prod.reference_data.party_stream ps
LATERAL VIEW EXPLODE(ps.alternate_identifiers) exploded_table AS alt_ids;

# COMMAND ----------
# MAGIC %sql
-- Materialized View: instrument_identifiers_mv
-- Built on instrument_stream (not directly on instrument source table)
-- TRIGGER ON UPDATE = auto-refreshes when instrument source changes
CREATE OR REPLACE MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv
  TRIGGER ON UPDATE
  COMMENT 'Flattened instrument alternate identifiers. Auto-refreshes incrementally when instrument source changes.'
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
FROM `19519_ctg_dev`.refdata.instrument_stream inst
LATERAL VIEW EXPLODE(inst.alternateIdentifiers) exploded_table AS alt_id;

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Confirm MVs Were Created Correctly
# MAGIC
# MAGIC `DESCRIBE EXTENDED` shows the full metadata. Key things to check:
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
# MAGIC ### ✅ Validate — Confirm Refresh Type Was Incremental
# MAGIC
# MAGIC After the initial create and any subsequent refresh, query the pipeline event log.
# MAGIC
# MAGIC | Message value | Meaning |
# MAGIC |---|---|
# MAGIC | `ROW_BASED` | ✅ True incremental — only changed rows processed |
# MAGIC | `PARTITION_OVERWRITE` | ✅ Incremental at partition level |
# MAGIC | `NO_OP` | ℹ️ No changes detected — nothing to refresh |
# MAGIC | `COMPLETE_RECOMPUTE` | ⚠️ Full refresh — investigate if unexpected |

# COMMAND ----------
# MAGIC %sql
-- Check refresh type for party MV
SELECT timestamp, message
FROM event_log(TABLE(x_prod.reference_data.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;

# COMMAND ----------
# MAGIC %sql
-- Check refresh type for instrument MV
SELECT timestamp, message
FROM event_log(TABLE(`19519_ctg_dev`.refdata.instrument_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC
LIMIT 5;

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 4 — Data Consistency Check
# MAGIC
# MAGIC Before benchmarking, confirm the Materialized View returns **identical results** to the standard view.
# MAGIC The `EXCEPT` query returns rows that appear in the MV but not in the view — expected result is 0 rows.

# COMMAND ----------
# MAGIC %sql
-- Party: MV vs Standard View row count comparison
SELECT
    (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_mv)  AS mv_count,
    (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_vw)  AS vw_count,
    CASE
        WHEN (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_mv)
           = (SELECT COUNT(*) FROM x_prod.reference_data.party_identifiers_vw)
        THEN '✅ MATCH — data is consistent'
        ELSE '❌ MISMATCH — investigate before benchmarking'
    END AS status;

# COMMAND ----------
# MAGIC %sql
-- Instrument: MV vs Standard View row count comparison
SELECT
    (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv)  AS mv_count,
    (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw)  AS vw_count,
    CASE
        WHEN (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv)
           = (SELECT COUNT(*) FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw)
        THEN '✅ MATCH — data is consistent'
        ELSE '❌ MISMATCH — investigate before benchmarking'
    END AS status;

# COMMAND ----------
# MAGIC %sql
-- Deep check: rows in MV that don't appear in standard view (expected: 0 rows)
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
# MAGIC ## Step 5 — ⏱️ Performance Benchmark: Full Scan
# MAGIC
# MAGIC Same queries as `01_standard_view.py` — but now reading from pre-computed Materialized View data.
# MAGIC The MV does **not** re-execute the EXPLODE or scan the source — it reads the stored result directly.
# MAGIC
# MAGIC > ⚠️ Run each query **at least twice** and record the **second run** for a fair comparison.

# COMMAND ----------

import time

# ── Party MV timing ────────────────────────────────────────────
start = time.time()
party_df = spark.sql("SELECT * FROM x_prod.reference_data.party_identifiers_mv")
party_count = party_df.count()
party_time = time.time() - start

# ── Instrument MV timing ───────────────────────────────────────
start = time.time()
instr_df = spark.sql("SELECT * FROM `19519_ctg_dev`.refdata.instrument_identifiers_mv")
instr_count = instr_df.count()
instr_time = time.time() - start

print("=" * 55)
print("  MATERIALIZED VIEW — FULL SCAN BENCHMARK")
print("=" * 55)
print(f"  party_identifiers_mv")
print(f"    Rows returned : {party_count:,}")
print(f"    Elapsed time  : {party_time:.2f} seconds  ⬅ record this")
print()
print(f"  instrument_identifiers_mv")
print(f"    Rows returned : {instr_count:,}")
print(f"    Elapsed time  : {instr_time:.2f} seconds  ⬅ record this")
print("=" * 55)
print("  ➡  Compare these times against 01_standard_view.py")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 6 — ⏱️ Performance Benchmark: Aggregation Query
# MAGIC
# MAGIC Aggregation queries tend to show the **largest speedup** from Materialized Views
# MAGIC because the standard view must scan and EXPLODE all rows first, then aggregate.
# MAGIC The Materialized View serves the pre-computed, already-flattened data directly.

# COMMAND ----------

# ── Party MV aggregation timing ───────────────────────────────
start = time.time()
party_agg = spark.sql("""
    SELECT identifier_type, COUNT(*) AS cnt
    FROM x_prod.reference_data.party_identifiers_mv
    GROUP BY identifier_type
    ORDER BY cnt DESC
""")
party_agg.show(truncate=False)
party_agg_time = time.time() - start

# ── Instrument MV aggregation timing ─────────────────────────
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
print(f"  party aggregation     : {party_agg_time:.2f} seconds  ⬅ record this")
print(f"  instrument aggregation: {instr_agg_time:.2f} seconds  ⬅ record this")
print("=" * 55)

# COMMAND ----------
# MAGIC %md
# MAGIC ---
# MAGIC ## Step 7 — End-to-End Incremental Update Test
# MAGIC
# MAGIC This section proves the incremental refresh works for **INSERT, UPDATE, and DELETE** operations.
# MAGIC After each change to the source table, wait ~1-2 minutes for `TRIGGER ON UPDATE` to fire,
# MAGIC then confirm the Materialized View reflects the change.
# MAGIC
# MAGIC > 🔁 The trigger monitors the Streaming Table (which monitors the source). The chain is:
# MAGIC > `Source change → Streaming Table detects it → MV trigger fires → MV refreshes`

# COMMAND ----------
# MAGIC %md
# MAGIC ### 7A — Baseline: Record Current Row Count

# COMMAND ----------
# MAGIC %sql
SELECT COUNT(*) AS row_count_before_test
FROM x_prod.reference_data.party_identifiers_mv;

# COMMAND ----------
# MAGIC %md
# MAGIC ### 7B — Test INSERT: Add a New Record

# COMMAND ----------
# MAGIC %sql
-- Insert a test record into the source party table
-- Adjust struct fields to match your actual party table schema
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
# MAGIC > ⏳ **Wait 1-2 minutes** for `TRIGGER ON UPDATE` to detect the change and refresh the MV, then run the next cell.

# COMMAND ----------
# MAGIC %sql
-- Confirm the new row appeared in the MV
-- Expected: 1 row with eci = 'TEST_ECI_99999'
SELECT * FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### 7C — Test UPDATE: Modify the Inserted Record

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
-- Confirm the update is reflected in the MV
-- Expected: country_of_domicile = 'US'
SELECT eci, country_of_domicile
FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### 7D — Test DELETE: Remove the Test Record

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
-- Expected: 0 rows
SELECT COUNT(*) AS should_be_zero
FROM x_prod.reference_data.party_identifiers_mv
WHERE eci = 'TEST_ECI_99999';

# COMMAND ----------
# MAGIC %md
# MAGIC ### ✅ Validate — Check Event Log After Each Trigger
# MAGIC
# MAGIC Confirm the refresh that fired after the INSERT/UPDATE/DELETE was incremental, not a full recompute.

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
# MAGIC Fill in the times from Steps 5–6 and compare against `01_standard_view.py`:
# MAGIC
# MAGIC | Query | Standard View (sec) | Materialized View (sec) | Speedup |
# MAGIC |---|---|---|---|
# MAGIC | `party` — full scan | _(from notebook 01)_ | _(from step 5)_ | _(calculate)_ |
# MAGIC | `instrument` — full scan | _(from notebook 01)_ | _(from step 5)_ | _(calculate)_ |
# MAGIC | `party` — aggregation | _(from notebook 01)_ | _(from step 6)_ | _(calculate)_ |
# MAGIC | `instrument` — aggregation | _(from notebook 01)_ | _(from step 6)_ | _(calculate)_ |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Key Takeaways for Reviewers
# MAGIC
# MAGIC | Aspect | Standard View | Materialized View |
# MAGIC |---|---|---|
# MAGIC | Data stored | ❌ None | ✅ Pre-computed Delta table |
# MAGIC | Query time | Slow — full scan + EXPLODE every time | Fast — reads stored result |
# MAGIC | Data freshness | Always real-time | Near real-time (TRIGGER ON UPDATE) |
# MAGIC | Handles INSERT / UPDATE / DELETE | ✅ Always | ✅ Via Streaming Table CDC layer |
# MAGIC | Incremental refresh | N/A | ✅ Only changed rows processed |
# MAGIC | Best for | Ad-hoc, infrequent, real-time queries | BI dashboards, repeated queries, large tables |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Manual Refresh Commands (if ever needed)
# MAGIC
# MAGIC ```sql
# MAGIC -- Normal refresh (incremental if possible)
# MAGIC REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv;
# MAGIC REFRESH MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv;
# MAGIC
# MAGIC -- Force full refresh (clears all data and recomputes from scratch)
# MAGIC REFRESH MATERIALIZED VIEW x_prod.reference_data.party_identifiers_mv FULL;
# MAGIC REFRESH MATERIALIZED VIEW `19519_ctg_dev`.refdata.instrument_identifiers_mv FULL;
# MAGIC ```
