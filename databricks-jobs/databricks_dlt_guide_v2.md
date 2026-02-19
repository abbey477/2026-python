# Databricks DLT — Materialized View Guide
> Step-by-step guide for beginners

---

## 1. What is a Materialized View?

A Materialized View is a pre-computed query result stored as a table. When the source (master) table changes, the view automatically updates with only the new/changed rows — not the full table.

| | Regular View | Materialized View |
|---|---|---|
| Stores data? | No — runs query live | Yes — stores results |
| Updates | On every query | Only when source changes (delta only) |

---

## 2. SQL Notebook vs Python Notebook

Both work for DLT. Choose based on your needs:

| | SQL Notebook | Python Notebook |
|---|---|---|
| Syntax | Pure SQL — clean and simple | Requires imports and function wrappers |
| Best for | Single MV with a SQL query | Multiple MVs, conditional logic, loops |
| Easier for beginners? | ✅ Yes | ❌ More verbose |
| Dynamic logic? | ❌ No | ✅ Yes |

> **Recommendation:** Use a **SQL notebook** for this exercise. Your query is already SQL — no need to wrap it in Python.

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

You don't control the refresh type — DLT picks the most efficient one each run:

| Refresh type | What it means |
|---|---|
| `INCREMENTAL` | Only new/changed rows processed |
| `GROUP_AGGREGATE` | Aggregation recalculated for changed groups only |
| `COMPLETE_RECOMPUTE` | Full reload — DLT decided it was faster |
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

## 12. Enable Row Tracking (Required for Incremental Refresh)

Run this **once** on your source table to enable incremental refresh:

```sql
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (
    delta.enableChangeDataFeed = true,
    delta.enableRowTracking = true
);
```

---

## 13. Troubleshooting

| Problem | Fix |
|---|---|
| Materialized view not available | Make sure Product edition = **Advanced** |
| Table not found | Check the full name: `x_prod.reference_data.party` |
| MV always doing full reload | Enable row tracking on source table (see Section 12) |
| MV always `COMPLETE_RECOMPUTE` | Remove any non-deterministic functions like `current_timestamp()` |
| Permission error | Check your user has access to both source and target catalogs |
| MV corrupted / out of sync | Use Full refresh (see Section 9) |

---

*End of Guide*
