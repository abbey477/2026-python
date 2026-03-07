# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # 📋 Standard View — Setup & Performance Benchmark
# MAGIC
# MAGIC **Notebook:** `01_standard_view`
# MAGIC **Purpose:** Create standard (regular) SQL views over `party` and `instrument` tables, then measure query execution time as the **baseline** for comparison against Materialized Views.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## What is a Standard View?
# MAGIC A standard view is a **saved SQL query** — it stores no data. Every time you query it, Databricks runs the full query against the source tables from scratch. This includes the `EXPLODE` operation to flatten nested arrays.
# MAGIC
# MAGIC > ⏱️ **Why measure time here?**
# MAGIC > This gives us the baseline cost of running the query cold every time. We compare this against the Materialized View notebook to see the performance benefit.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC | Property | Value |
# MAGIC |---|---|
# MAGIC | Party view | `x_prod.reference_data.party_identifiers_vw` |
# MAGIC | Instrument view | `` `19519_ctg_dev`.refdata.instrument_identifiers_vw `` |
# MAGIC | Data stored | ❌ None — query executes on every access |
# MAGIC | Refresh needed | ❌ Always real-time |

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 1 — Create Standard View: `party_identifiers_vw`
# MAGIC
# MAGIC This view flattens the `alternate_identifiers` array in the `party` table using `LATERAL VIEW EXPLODE`.
# MAGIC Each element in the array becomes its own row in the result.

# COMMAND ----------
# MAGIC %sql
CREATE OR REPLACE VIEW x_prod.reference_data.party_identifiers_vw
  COMMENT 'Standard view — flattened party alternate identifiers. No data stored. Use for performance comparison against party_identifiers_mv.'
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
# MAGIC ## Step 2 — Create Standard View: `instrument_identifiers_vw`
# MAGIC
# MAGIC Same pattern for the `instrument` table — flattens the `alternateIdentifiers` array.
# MAGIC Extracts all identifier fields plus the CDC metadata columns (`__START_AT`, `__END_AT`, etc.).

# COMMAND ----------
# MAGIC %sql
CREATE OR REPLACE VIEW `19519_ctg_dev`.refdata.instrument_identifiers_vw
  COMMENT 'Standard view — flattened instrument alternate identifiers. No data stored. Use for performance comparison against instrument_identifiers_mv.'
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
    instrument.__cob_date,
    instrument.__START_AT,
    instrument.__END_AT,
    instrument.__txn_id_long,
    instrument.__slice
FROM `19519_ctg_dev`.refdata.instrument instrument
LATERAL VIEW EXPLODE(instrument.alternateIdentifiers) exploded_table AS alt_id;

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 3 — Validate: Confirm Views Were Created
# MAGIC
# MAGIC Quick row count to confirm both views are accessible and returning data.
# MAGIC > ✅ Expected: counts match the source tables (or slightly higher due to EXPLODE expanding rows)

# COMMAND ----------
# MAGIC %sql
SELECT
  'party_identifiers_vw'      AS view_name,
  COUNT(*)                    AS row_count
FROM x_prod.reference_data.party_identifiers_vw

UNION ALL

SELECT
  'instrument_identifiers_vw' AS view_name,
  COUNT(*)                    AS row_count
FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw;

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 4 — ⏱️ Performance Benchmark: Full Scan
# MAGIC
# MAGIC **Run these queries and note the execution time shown in the cell output.**
# MAGIC After running, also check: **SQL Editor → Query History** for precise duration and DBU consumption.
# MAGIC
# MAGIC > ⚠️ Run each query **at least twice** — the first run may benefit from file-level caching.
# MAGIC > Record the **second run time** for a fair comparison with the Materialized View.

# COMMAND ----------

import time

# ── Party view timing ──────────────────────────────────────────
start = time.time()
party_df = spark.sql("SELECT * FROM x_prod.reference_data.party_identifiers_vw")
party_count = party_df.count()
party_time = time.time() - start

# ── Instrument view timing ─────────────────────────────────────
start = time.time()
instr_df = spark.sql("SELECT * FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw")
instr_count = instr_df.count()
instr_time = time.time() - start

print("=" * 55)
print("  STANDARD VIEW — FULL SCAN BENCHMARK")
print("=" * 55)
print(f"  party_identifiers_vw")
print(f"    Rows returned : {party_count:,}")
print(f"    Elapsed time  : {party_time:.2f} seconds  ⬅ record this")
print()
print(f"  instrument_identifiers_vw")
print(f"    Rows returned : {instr_count:,}")
print(f"    Elapsed time  : {instr_time:.2f} seconds  ⬅ record this")
print("=" * 55)
print("  ➡  Compare these times against 02_materialized_view.py")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 5 — ⏱️ Performance Benchmark: Aggregation Query
# MAGIC
# MAGIC Aggregations amplify the performance difference between standard views and materialized views
# MAGIC because the standard view must scan and EXPLODE **all rows** before grouping.

# COMMAND ----------

# ── Party aggregation timing ───────────────────────────────────
start = time.time()
party_agg = spark.sql("""
    SELECT identifier_type, COUNT(*) AS cnt
    FROM x_prod.reference_data.party_identifiers_vw
    GROUP BY identifier_type
    ORDER BY cnt DESC
""")
party_agg.show(truncate=False)
party_agg_time = time.time() - start

# ── Instrument aggregation timing ─────────────────────────────
start = time.time()
instr_agg = spark.sql("""
    SELECT assetIdType, COUNT(*) AS cnt
    FROM `19519_ctg_dev`.refdata.instrument_identifiers_vw
    GROUP BY assetIdType
    ORDER BY cnt DESC
""")
instr_agg.show(truncate=False)
instr_agg_time = time.time() - start

print("=" * 55)
print("  STANDARD VIEW — AGGREGATION BENCHMARK")
print("=" * 55)
print(f"  party aggregation     : {party_agg_time:.2f} seconds  ⬅ record this")
print(f"  instrument aggregation: {instr_agg_time:.2f} seconds  ⬅ record this")
print("=" * 55)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Query | Rows | Time (seconds) |
# MAGIC |---|---|---|
# MAGIC | `party_identifiers_vw` — full scan | _(fill in)_ | _(fill in)_ |
# MAGIC | `instrument_identifiers_vw` — full scan | _(fill in)_ | _(fill in)_ |
# MAGIC | `party_identifiers_vw` — aggregation | — | _(fill in)_ |
# MAGIC | `instrument_identifiers_vw` — aggregation | — | _(fill in)_ |
# MAGIC
# MAGIC > 📌 **Next step:** Run `02_materialized_view.py` and compare the times in its summary table.
# MAGIC
# MAGIC ---
# MAGIC > **Key point for reviewers:** Every number above was computed **live** from the source tables.
# MAGIC > No caching, no pre-computation. This is the true cost of a standard view on every access.
