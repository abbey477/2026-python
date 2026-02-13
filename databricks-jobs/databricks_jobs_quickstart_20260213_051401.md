# Databricks Multi-Task Job: Quick Start Guide
**Refresh Materialized View + Downstream Tasks**

---

## What You're Building

```
Task 1: Refresh Materialized View (15 min)
   ↓ (waits)
Task 2: Your downstream processing (5 min)
   ↓ (waits)
Task 3: Another task (3 min)
```

Total: ~23 minutes, runs automatically in sequence.

---

## Step 1: Find Your SQL Warehouse

1. Click **"SQL Warehouses"** (left sidebar)
2. Look for a warehouse that says **"Running"** or **"Serverless"**
3. If all are stopped, click one → Click **"Start"** → Wait 2 minutes
4. **Write down the name:** ___________________

---

## Step 2: Create the Job

### 2.1 Navigate to Jobs

1. Click **"Workflows"** (left sidebar)
2. Click **"Create Job"** (blue button, top right)

### 2.2 Add Task 1 - Refresh Materialized View

You'll see a form. Fill in:

| Field | Value |
|-------|-------|
| Task name | `refresh_mv` |
| Type | Select **"SQL"** from dropdown |
| SQL warehouse | Select your warehouse from Step 1 |
| Query | Paste the query below |

**Query:**
```sql
REFRESH MATERIALIZED VIEW `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

Click **"Create task"** (bottom right)

### 2.3 Add Task 2 - Downstream Processing

Click **"+ Add task"** button

| Field | Value |
|-------|-------|
| Task name | `process_data` |
| Type | **"SQL"** or **"Notebook"** (your choice) |
| **Depends on** | ✅ **Check the box for `refresh_mv`** ← CRITICAL! |
| SQL warehouse | (if SQL) Select same warehouse |
| Cluster | (if Notebook) Select a cluster |
| Query/Notebook | Your processing code |

**Example SQL query for Task 2:**
```sql
-- Your downstream processing
SELECT COUNT(*) as total_rows
FROM `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

Click **"Create task"**

### 2.4 Add More Tasks (Optional)

Repeat for Task 3, 4, etc:
- Click **"+ Add task"**
- Set **"Depends on"** to the previous task
- Configure and create

### 2.5 Name and Save

1. At the top, click on "New Job" to rename
2. Type: `MV_Refresh_Pipeline`
3. Press Enter
4. Click **"Save"** (top right)

---

## Step 3: Run the Job

### 3.1 Start Execution

1. Click **"Run now"** (big blue button, top right)

### 3.2 Watch It Run

You'll see:

```
Task 1: refresh_mv          [Running ━━━━━━━━] 15m 23s
Task 2: process_data        [Waiting...]
Task 3: another_task        [Waiting...]
```

When Task 1 completes:

```
Task 1: refresh_mv          [✅ Succeeded] 15m 23s
Task 2: process_data        [Running ━━━━━━━━] 3m 45s
Task 3: another_task        [Waiting...]
```

### 3.3 Check Results

When all tasks complete:

```
Task 1: refresh_mv          [✅ Succeeded] 15m 23s
Task 2: process_data        [✅ Succeeded] 3m 45s  
Task 3: another_task        [✅ Succeeded] 2m 12s

Total Duration: 21m 20s
```

---

## Step 4: View Run History

1. Click **"Runs"** tab (near top)
2. See all previous executions:

| Run | Start Time | Duration | Status |
|-----|------------|----------|--------|
| #3 | 2026-02-13 10:00 | 21m 20s | ✅ Succeeded |
| #2 | 2026-02-13 08:00 | 22m 15s | ✅ Succeeded |
| #1 | 2026-02-13 06:00 | 21m 45s | ✅ Succeeded |

---

## Common Task Types

### SQL Task
```
Type: SQL
SQL warehouse: Your warehouse
Query: Your SQL code
```

### Notebook Task
```
Type: Notebook  
Notebook path: /Workspace/path/to/notebook
Cluster: Your cluster
Parameters: (optional) {"key": "value"}
```

### Python Script Task
```
Type: Python script
Python file: /Workspace/path/to/script.py
Cluster: Your cluster
```

---

## Passing Data Between Tasks

### Method 1: Task Values (Simple)

**Task 1 - Set a value:**
```python
# In notebook
dbutils.jobs.taskValues.set(key="row_count", value="1000000")
```

**Task 2 - Get the value:**
```python
# In notebook
row_count = dbutils.jobs.taskValues.get(
    taskKey="refresh_mv", 
    key="row_count"
)
print(f"Processing {row_count} rows")
```

### Method 2: Job Parameters (Global)

**Set job parameters:**
1. Job page → **"Parameters"** tab
2. Add:
```json
{
  "catalog": "19519_ctg_dev",
  "schema": "refdata_denorm_materialized"
}
```

**Use in SQL task:**
```sql
REFRESH MATERIALIZED VIEW `${catalog}`.`${schema}`.`instrument_alternate_identifiers_test`
```

**Use in Notebook task:**
```python
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
```

---

## Scheduling the Job

### Add a Schedule

1. On job page, click **"Add trigger"**
2. Select **"Scheduled"**
3. Choose frequency:
   - **Daily at 2 AM:** Cron = `0 2 * * *`
   - **Every hour:** Cron = `0 * * * *`
   - **Weekdays at 9 AM:** Cron = `0 9 * * 1-5`
4. Select time zone
5. Click **"Save"**

---

## Email Notifications

1. Job page → **"Email notifications"** section
2. Add your email
3. Check:
   - ✅ On failure (recommended)
   - ✅ On success (optional)
4. Click **"Save"**

---

## Task Dependency Patterns

### Linear (Sequential)
```
Task 1 → Task 2 → Task 3
```
Each task depends on the previous one.

### Parallel (Fan-Out)
```
Task 1
  ├→ Task 2
  ├→ Task 3
  └→ Task 4
```
All three tasks depend on Task 1, run in parallel.

### Converge (Fan-In)
```
Task 1 ┐
Task 2 ├→ Task 4
Task 3 ┘
```
Task 4 depends on all three, waits for all to complete.

---

## Troubleshooting

### Problem: Task 2 not starting after Task 1

**Check:**
1. Did Task 1 succeed? (must be green ✅)
2. Does Task 2 have **"Depends on"** checked for Task 1?

**Fix:**
1. Edit Task 2
2. Check the **"Depends on"** box for Task 1
3. Save

### Problem: "SQL Warehouse is stopped"

**Fix:**
1. Go to **SQL Warehouses**
2. Click your warehouse
3. Click **"Start"**
4. Wait 2 minutes
5. Click **"Run now"** again on your job

### Problem: "Permission denied"

**Fix:**
Ask your admin for:
- USAGE permission on SQL Warehouse
- REFRESH permission on materialized view

---

## Complete Example

### Real-World Pipeline

**Job Name:** `Daily_MV_Refresh`

**Task 1: Refresh MV**
```
Type: SQL
Warehouse: Performance-Warehouse
Query:
  REFRESH MATERIALIZED VIEW 
  `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

**Task 2: Validate Data**
```
Type: SQL
Depends on: Task 1
Warehouse: Performance-Warehouse
Query:
  SELECT 
    COUNT(*) as total,
    CASE 
      WHEN COUNT(*) > 1000000 THEN 'PASS'
      ELSE 'FAIL'
    END as status
  FROM `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

**Task 3: Update Summary Table**
```
Type: SQL
Depends on: Task 2
Warehouse: Performance-Warehouse
Query:
  INSERT INTO analytics.daily_summary
  SELECT current_date(), COUNT(*)
  FROM `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

**Task 4: Send Email**
```
Type: Notebook
Depends on: Task 3
Cluster: General-Purpose
Notebook: /Notifications/send_success_email
```

**Schedule:** Daily at 2 AM (`0 2 * * *`)

**Notifications:** data-team@company.com on failure

---

## Quick Commands

### View Task Logs
1. Click on run in **"Runs"** tab
2. Click on task name
3. View logs

### Cancel Running Job
1. Go to running job
2. Click **"Cancel run"** (top right)

### Clone Job
1. Job page → **"⋮"** menu → **"Clone"**
2. Modify as needed

### Delete Job
1. Job page → **"⋮"** menu → **"Delete"**
2. Confirm

---

## Visual Guide: UI Locations

```
Databricks Workspace
├── SQL Warehouses (sidebar)
│   └── Find/Start warehouse
│
├── Workflows (sidebar)
│   ├── Create Job
│   │   ├── + Add task
│   │   │   ├── Task name
│   │   │   ├── Type (SQL/Notebook/Python)
│   │   │   ├── Depends on ← SET THIS!
│   │   │   └── Query/Notebook path
│   │   └── Save
│   │
│   └── View Job
│       ├── Run now
│       ├── Runs tab (history)
│       └── Tasks tab (edit)
│
└── Data (sidebar)
    └── Browse catalogs/schemas/views
```

---

## Summary Checklist

**Setup:**
- [ ] Found/started SQL Warehouse
- [ ] Created job in Workflows
- [ ] Added Task 1 (refresh MV)
- [ ] Added Task 2 (depends on Task 1)
- [ ] Added more tasks as needed
- [ ] Saved job

**Execution:**
- [ ] Clicked "Run now"
- [ ] Watched tasks run in sequence
- [ ] Verified all tasks succeeded
- [ ] Checked run duration

**Optional:**
- [ ] Added schedule
- [ ] Set up email notifications
- [ ] Configured parameters

---

**Document Version:** 1.0  
**Last Updated:** February 13, 2026, 05:14:01
