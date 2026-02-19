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

## 2. Create the Pipeline (UI Steps)

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
| Storage options | **Unity Catalog** (since your table is in x_prod) |
| Catalog | `x_prod` |
| Schema | `reference_data` |
| Cluster policy | None (default) |

- Click **Create** at the bottom of the form

### Step 3 — Open the Auto-Created Notebook
- After creating the pipeline, Databricks creates an empty notebook
- Click the notebook link shown on the pipeline page to open it
- Delete any default content in the first cell

---

## 3. The Notebook Code

Paste the following into your notebook (`example_dlt_01`):

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

## 4. Run the Pipeline

- Go back to **Jobs & Pipelines** → click your pipeline `abi-sampe-dlt`
- Make sure the notebook is linked under **Settings → Source code**
- Click the **Start (▶) button**
- Watch the graph — your materialized view node will appear
- Wait for status: **Completed ✅**

> The first run creates the full materialized view. Every run after that processes only new/changed rows.

---

## 5. Where to Find the Materialized View in Catalog

After the pipeline completes, go to:

```
Catalog → x_prod → reference_data → party_identifiers_mv
```

It will be listed with a **Materialized View** icon (different from a regular table).

---

## 6. Automatic Refresh Options

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

## 7. Troubleshooting

| Error | Fix |
|---|---|
| Materialized view not available | Make sure Product edition = **Advanced** |
| Table not found | Check the full name: `x_prod.reference_data.party` |
| Pipeline runs but MV not updating | Enable Change Data Feed on source table (see below) |
| Permission error | Check that your user has access to `x_prod` catalog |

To enable Change Data Feed on your master table — run this **once** in the SQL Editor:

```sql
ALTER TABLE x_prod.reference_data.party
SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

---

*End of Guide*
