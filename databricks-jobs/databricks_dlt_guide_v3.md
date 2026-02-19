# Databricks DLT — Materialized View Guide
> Step-by-step guide for beginners
> **Version 3**

---

## Table of Contents

1. What is a Materialized View?
2. SQL Notebook vs Python Notebook — Quick Overview
3. Create the Pipeline (UI Steps)
4. The Notebook Code
5. Run the Pipeline
6. Where to Find the Materialized View in Catalog
7. Automatic Refresh Options
8. Refresh Types — What DLT Does Automatically
9. Force a Full Refresh
10. Prevent Accidental Full Refreshes
11. Check Refresh Status & Type
12. Source Table Properties — Enable for Best Performance
13. Performance — Getting the Most Out of Your Materialized View
14. SQL vs Python — Full Feature Comparison & Control
15. Troubleshooting

---

## 1. What is a Materialized View?

A Materialized View is a pre-computed query result stored as a table. When the source (master) table changes, the view automatically updates with only the new/changed rows — not the full table.

| | Regular View | Materialized View |
|---|---|---|
| Stores data? | No — runs query live | Yes — stores results |
| Updates | On every query | Only when source changes (delta only) |

---

## 2. SQL Notebook vs Python Notebook — Quick Overview

Both work for DLT. Choose based on your needs:

| | SQL Notebook | Python Notebook |
|---|---|---|
| Syntax | Pure SQL — clean and simple | Requires imports and function wrappers |
| Best for | Single MV with a SQL query | Multiple MVs, conditional logic, loops |
| Easier for beginners? | ✅ Yes | ❌ More verbose |
| Dynamic logic? | ❌ No | ✅ Yes |
| More features & control? | ❌ | ✅ Yes — see Section 14 |

> **Recommendation:** Use a **SQL notebook** for this exercise. Your query is already SQL — no need to wrap it in Python. See Section 14 for a full breakdown of when to switch to Python.

---

## 3. Create the Pipeline (UI Steps)

### Step 1 — Open Jobs & Pipelines
- In the left sidebar, click **Jobs & Pipelines**
- Click **ETL pipeline** ("Build ETL pipelines using SQL and Python")

### Step 2 — Fill in the Create Pipeline Form

| Field | What to enter |
|---|---|
| Pipeline name | e.g. `abi-sampe-dlt` |
| Product edition | **Advanced** (required for Materialized Views) |
| Pipeline mode | **Triggered** |
| Source code | Leave blank — Databricks will create a notebook |
| Storage options | **Unity Catalog** |
| Catalog | Your target catalog *(not x_prod — use a separate one)* |
| Schema | Your target schema |
| Cluster policy | None (default) |

- Click **Create** at the bottom of the form

> ⚠️ Set the destination catalog/schema to somewhere **other than x_prod** so the MV is separate from the master table.

### Step 3 — Open the Auto-Created Notebook
- After creating the pipeline, Databricks creates an empty notebook
- Click the notebook link shown on the pipeline page to open it
- Delete any default content in the first cell
- Make sure the notebook language is set to **SQL**

---

## 4. The Notebook Code

### SQL Notebook (recommended)

```sql
CREATE OR REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv
COMMENT "Materialized view — updates when party table changes"
AS
SELECT
    __cob_date,
    eci,
    country_of_domicile,
    country_of_asset,
    organization.country_of_incorporation,
    alt_ids.identifier_type,
    alt_ids.identifier_value
FROM
    x_prod.reference_data.party cp
    LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids
```

### Python Notebook (alternative)

```python
import dlt

@dlt.materialized_view(
    name="party_identifiers_mv",
    comment="Materialized view — updates when party table changes"
)
def party_identifiers_mv():
    return spark.sql("""
        SELECT
            __cob_date,
            eci,
            country_of_domicile,
            country_of_asset,
            organization.country_of_incorporation,
            alt_ids.identifier_type,
            alt_ids.identifier_value
        FROM
            x_prod.reference_data.party cp
            LATERAL VIEW EXPLODE(cp.alternate_identifiers) exploded_table AS alt_ids
    """)
```

- Save with **Ctrl+S** after pasting

---

## 5. Run the Pipeline

- Go back to **Jobs & Pipelines** → click your pipeline `abi-sampe-dlt`
- Make sure the notebook is linked under **Settings → Source code**
- Click the **Start (▶) button**
- Watch the graph — your materialized view node will appear
- Wait for status: **Completed ✅**

> The first run creates the full materialized view. Every run after that processes only new/changed rows.

---

## 6. Where to Find the Materialized View in Catalog

After the pipeline completes, go to:

```
Catalog → your_catalog → your_schema → party_identifiers_mv
```

It will be listed with a **Materialized View** icon (different from a regular table).

---

## 7. Automatic Refresh Options

By default the pipeline is **manual** (you click Start). To make it automatic:

### Option A — Schedule (simplest)
- Open pipeline `abi-sampe-dlt`
- Click the **Schedule** button (clock icon, top right)
- Set frequency — e.g. every day at 6am
- Pipeline runs automatically on that schedule

### Option B — Trigger from a Job (most control)
- Go to **Jobs & Pipelines → Create new → Job**
- Add a task: type = **Delta Live Tables**, select `abi-sampe-dlt`
- Set the job to run after your master table is updated

| Situation | Use |
|---|---|
| `party` table updates on a fixed schedule | Option A — Schedule |
| `party` table updates unpredictably | Option B — Job trigger |

---

## 8. Refresh Types — What DLT Does Automatically

You don't control the refresh type — DLT picks the most efficient one each run based on a cost model:

| Refresh type | What it means |
|---|---|
| `INCREMENTAL` | Only new/changed rows processed |
| `GROUP_AGGREGATE` | Aggregation recalculated for changed groups only |
| `COMPLETE_RECOMPUTE` | Full reload — DLT decided it was faster or required |
| `NO_OP` | Nothing changed, nothing to do |

> ⚠️ If your query uses non-deterministic functions like `current_timestamp()`, DLT will always do a `COMPLETE_RECOMPUTE`. Your current query does not use these, so you should get incremental refreshes.

---

## 9. Force a Full Refresh

Use when the MV is corrupted, out of sync, or you changed the query logic.

### Option A — From the UI
- Open pipeline `abi-sampe-dlt`
- Click the **dropdown arrow** next to the Start button
- Select **Full refresh**

### Option B — From the SQL Editor
```sql
-- Synchronous (waits until complete)
REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv FULL;

-- Asynchronous (returns immediately, runs in background)
REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv FULL ASYNC;
```

### Option C — Drop and Recreate (last resort)
```sql
DROP MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv;
```
Then run the pipeline normally — it will recreate from scratch.

---

## 10. Prevent Accidental Full Refreshes

Add this to your Python notebook code to block full refreshes on large/expensive MVs:

```python
@dlt.materialized_view(
    name="party_identifiers_mv",
    table_properties={"pipelines.reset.allowed": "false"}  # blocks full refresh
)
```

---

## 11. Check Refresh Status & Type

### Check last refresh status
Run in SQL Editor:
```sql
DESCRIBE EXTENDED your_catalog.your_schema.party_identifiers_mv;
```
Look for `last refresh status type`:
- `INCREMENTAL` — delta refresh ran
- `RECOMPUTE` — full reload ran
- `NO_OPERATION` — nothing changed

### Check what type DLT chose and why
```sql
SELECT timestamp, message
FROM event_log(TABLE(your_catalog.your_schema.party_identifiers_mv))
WHERE event_type = 'planning_information'
ORDER BY timestamp DESC;
```

---

## 12. Source Table Properties — Enable for Best Performance

These three properties work together to give DLT everything it needs for fast, incremental refreshes. Run this **once** on your source table:

```sql
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
    delta.enableRowTracking = true,
    delta.enableDeletionVectors = true,
    delta.enableChangeDataFeed = true
);
```

### What each one does

**`delta.enableRowTracking`**
Assigns a hidden unique ID to every row in the table. Without this, DLT knows *something* changed but not *which rows* — so it falls back to a full reload. With row tracking, DLT can find and process only the exact rows that changed. This is **required** for incremental refresh.

**`delta.enableDeletionVectors`**
Normally when you delete rows from a Delta table, Databricks has to rewrite the entire data file even if only one row was deleted — very expensive. Deletion Vectors instead write a small separate file that *marks* deleted rows, without touching the original data. This makes deletes fast and cheap. DLT uses this to apply deletes to the MV without scanning the whole table. This is **optional but strongly recommended**.

**`delta.enableChangeDataFeed`**
Keeps a log of every change to the table — recording what happened (insert / update / delete) and what the row looked like before and after the change. Think of it as an audit trail. DLT reads this feed to understand exactly what type of change occurred so it can apply the right operation to the MV. This is **required** for incremental refresh.

### How they work together

| Property | What it answers | Required? |
|---|---|---|
| `enableRowTracking` | *Which specific row changed?* | ✅ Required |
| `enableDeletionVectors` | *How to handle deletes efficiently?* | Recommended |
| `enableChangeDataFeed` | *What type of change was it?* | ✅ Required |

> ⚠️ These only affect *how* the data is tracked behind the scenes. They do **not** change your actual data or table structure.

---

## 13. Performance — Getting the Most Out of Your Materialized View

### How DLT decides between incremental and full refresh

DLT uses an internal engine called **Enzyme** that runs a cost analysis every time the pipeline executes. It compares the cost of doing an incremental refresh vs a full recompute and picks whichever is cheaper. You don't control this directly — but you can influence it by following the best practices below.

### Things that HELP incremental refresh

- ✅ Enable all three source table properties (Section 12)
- ✅ Use **serverless compute** for your pipeline — incremental refresh only works on serverless
- ✅ Use simple, deterministic SQL — `SELECT`, `GROUP BY`, `WHERE`, `INNER JOIN`, `LEFT JOIN`, `UNION ALL`, `WITH` (CTEs) all support incremental refresh
- ✅ Keep queries focused — avoid selecting columns you don't need
- ✅ Use **liquid clustering** instead of partitioning for large tables (see below)

### Things that FORCE a full refresh (avoid these)

- ❌ Non-deterministic functions: `current_timestamp()`, `rand()`, `uuid()`, `random()`
- ❌ Complex joins: cross joins, semi joins, anti joins, or a large number of joins
- ❌ Using classic (non-serverless) compute — always does a full recompute
- ❌ Source tables with row filters or column masks applied
- ❌ Source tables without row tracking enabled

### Liquid Clustering — better than partitioning

Standard partitioning splits data into fixed folders (e.g. by date). If your query doesn't filter on the partition column, it still scans everything. Liquid Clustering is smarter — Databricks automatically figures out the best clustering keys based on your query patterns.

Apply it to your MV in SQL:
```sql
CREATE OR REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv
CLUSTER BY (eci, __cob_date)   -- choose columns you filter/join on most
AS
SELECT ...
```

Or let Databricks choose automatically:
```sql
CREATE OR REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv
CLUSTER BY AUTO
AS
SELECT ...
```

### Z-Ordering — for existing tables

Z-Ordering co-locates related data in the same files, so queries that filter on those columns skip more files. Run this on your source table periodically:
```sql
OPTIMIZE x_prod.reference_data.party ZORDER BY (eci, __cob_date);
```

### Refresh timeout — avoid long-running refreshes timing out

By default Databricks allows up to 2 days for a refresh. You can set a shorter explicit timeout so it fails fast rather than hanging:
```sql
SET STATEMENT_TIMEOUT = 3600;  -- 1 hour in seconds
REFRESH MATERIALIZED VIEW your_catalog.your_schema.party_identifiers_mv;
```

### Synchronous vs Asynchronous refresh

| | Synchronous (default) | Asynchronous |
|---|---|---|
| Behaviour | Waits until refresh is complete | Returns immediately, runs in background |
| Use when | You need fresh data before next step | You want to trigger and move on |
| Command | `REFRESH MATERIALIZED VIEW mv_name` | `REFRESH MATERIALIZED VIEW mv_name ASYNC` |

### When to use a Streaming Table instead of a Materialized View

Materialized views are great for most cases, but consider a **Streaming Table** when:
- Your source data is very large (billions of rows) and a full refresh would be too costly
- Records should only be processed **once** (e.g. from Kafka or Auto Loader)
- You delete old records from the source but still need them in the downstream table
- You need guaranteed exactly-once processing

---

## 14. SQL vs Python — Full Feature Comparison & Control

### Feature comparison table

| Feature | SQL | Python |
|---|---|---|
| Create a materialized view | ✅ | ✅ |
| Data quality expectations | ✅ | ✅ |
| Cluster by / partitioning | ✅ | ✅ |
| Comments and table properties | ✅ | ✅ |
| Readable for pure SQL queries | ✅ Cleaner | ❌ More boilerplate |
| Loop to create multiple MVs dynamically | ❌ | ✅ |
| Conditional logic (`if/else`) | ❌ | ✅ |
| Read config from files or widgets | ❌ | ✅ |
| Complex DataFrame transformations | ❌ | ✅ |
| Use Python libraries (pandas, etc.) | ❌ | ✅ |
| Event hooks for custom monitoring | ❌ | ✅ |
| Mix SQL and Python in same pipeline | ❌ | ✅ (via `spark.sql()`) |

> **Bottom line: Python has more features and control. SQL is simpler and cleaner for pure query logic.**

---

### What Python can do that SQL cannot

#### 1. Create multiple MVs dynamically with a loop

Instead of writing a separate `CREATE` statement for every table, Python lets you loop:

```python
import dlt

tables = ["party", "accounts", "transactions"]

for table_name in tables:
    @dlt.materialized_view(name=f"{table_name}_mv")
    def create_mv():
        return spark.read.table(f"x_prod.reference_data.{table_name}")
```

SQL requires you to write each one manually — no looping possible.

---

#### 2. Conditional logic — change behaviour based on environment

```python
import dlt
import os

env = os.getenv("ENV", "dev")  # reads environment variable

@dlt.materialized_view(name="party_identifiers_mv")
def party_identifiers_mv():
    if env == "prod":
        return spark.read.table("x_prod.reference_data.party")
    else:
        return spark.read.table("x_dev.reference_data.party")
```

Useful when the same pipeline runs in dev, test, and prod environments. SQL cannot do this.

---

#### 3. Event hooks — custom monitoring and alerting

Event hooks let you run custom code when something happens in the pipeline — e.g. send a Slack alert when an MV is created or fails:

```python
import dlt

def on_flow_complete(event):
    if event["level"] == "ERROR":
        print(f"Pipeline failed: {event['msg']}")  # replace with Slack/email alert

dlt.create_event_hook(on_flow_complete)

@dlt.materialized_view(name="party_identifiers_mv")
def party_identifiers_mv():
    return spark.sql("SELECT ...")
```

SQL has no equivalent for this.

---

#### 4. Complex transformations using Python/Spark functions

When SQL functions aren't enough, Python gives you the full Spark API and any Python library:

```python
import dlt
from pyspark.sql.functions import col, regexp_replace, upper

@dlt.materialized_view(name="party_identifiers_mv")
def party_identifiers_mv():
    df = spark.read.table("x_prod.reference_data.party")
    # Clean and standardise data using Spark functions
    return df.withColumn(
        "eci_clean",
        upper(regexp_replace(col("eci"), r"\s+", ""))
    )
```

---

#### 5. Mix SQL and Python in the same pipeline

Python notebooks can contain both SQL logic and Python logic. You can call `spark.sql()` for the parts that are easier in SQL, and use Python for everything else:

```python
import dlt

@dlt.materialized_view(name="party_identifiers_mv")
def party_identifiers_mv():
    # SQL handles the query
    df = spark.sql("""
        SELECT * FROM x_prod.reference_data.party
    """)
    # Python handles the post-processing
    return df.filter(df.eci.isNotNull())
```

---

### When to use each

| Situation | Use |
|---|---|
| Your query is pure SQL | **SQL notebook** — simpler and cleaner |
| Single MV, no dynamic logic needed | **SQL notebook** |
| You are new to Databricks | **SQL notebook** — easier to read and debug |
| Multiple MVs from the same template | **Python notebook** |
| Pipeline runs in multiple environments (dev/prod) | **Python notebook** |
| You need custom monitoring or alerting | **Python notebook** |
| Complex transformations beyond SQL | **Python notebook** |
| Production-grade pipelines | **Python notebook** |

---

## 15. Troubleshooting

| Problem | Fix |
|---|---|
| Materialized view not available | Make sure Product edition = **Advanced** |
| Table not found | Check the full name: `x_prod.reference_data.party` |
| MV always doing full reload | Enable row tracking and change data feed on source table (Section 12) |
| MV always `COMPLETE_RECOMPUTE` | Remove non-deterministic functions like `current_timestamp()` |
| MV always `COMPLETE_RECOMPUTE` | Switch pipeline compute to **serverless** |
| Permission error | Check your user has access to both source and target catalogs |
| MV corrupted / out of sync | Use Full refresh (Section 9) |
| Refresh timing out | Set explicit `STATEMENT_TIMEOUT` before refresh (Section 13) |
| Queries on MV are slow | Add `CLUSTER BY` on frequently filtered columns (Section 13) |

---

*End of Guide — Version 3*
