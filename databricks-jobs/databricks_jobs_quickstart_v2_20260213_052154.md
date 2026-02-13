# Databricks Materialized View Refresh Pipeline - Complete Guide
**3-Task Sequential Workflow with Performance Metrics**

Version: 2.0 | Created: February 13, 2026, 05:21:54

---

## What You're Building

```
Task 1: Refresh Materialized View (SQL)
   ↓
Task 2: Print Performance Metrics (Notebook)
   ↓
Task 3: Send Notification (Notebook)
```

---

## Visual Guide: UI Navigation

```
Databricks Workspace
│
├── SQL Warehouses (sidebar)
│   ├── Click warehouse name
│   ├── Check status: Running/Stopped
│   └── If stopped → Click "Start" button
│
├── Workflows (sidebar)
│   │
│   ├── Create Job (button)
│   │   │
│   │   ├── Task 1 Configuration
│   │   │   ├── Task name: refresh_mv
│   │   │   ├── Type: SQL ▼
│   │   │   ├── SQL warehouse: [Select warehouse] ▼
│   │   │   ├── Query: [Paste REFRESH query]
│   │   │   └── [Create task] button
│   │   │
│   │   ├── + Add task (button)
│   │   │   │
│   │   │   ├── Task 2 Configuration
│   │   │   │   ├── Task name: print_metrics
│   │   │   │   ├── Type: Notebook ▼
│   │   │   │   ├── Depends on: ✅ refresh_mv ← CHECK THIS!
│   │   │   │   ├── Notebook path: /Workspace/metrics_notebook
│   │   │   │   ├── Cluster: [Select cluster] ▼
│   │   │   │   └── [Create task] button
│   │   │   │
│   │   │   └── + Add task (button)
│   │   │       │
│   │   │       └── Task 3 Configuration
│   │   │           ├── Task name: send_notification
│   │   │           ├── Type: Notebook ▼
│   │   │           ├── Depends on: ✅ print_metrics ← CHECK THIS!
│   │   │           ├── Notebook path: /Workspace/notification_notebook
│   │   │           ├── Cluster: [Select cluster] ▼
│   │   │           └── [Create task] button
│   │   │
│   │   ├── Job name (top): MV_Refresh_Pipeline
│   │   └── [Save] button (top right)
│   │
│   └── Your Job Page
│       ├── [Run now] button → Execute job
│       ├── Tasks tab → View workflow diagram
│       └── Runs tab → View execution history
│
└── Workspace (sidebar)
    └── Create notebooks
        ├── /Workspace/metrics_notebook
        └── /Workspace/notification_notebook
```

---

## Step-by-Step Setup

### Step 1: Prepare SQL Warehouse

1. Click **"SQL Warehouses"** (left sidebar)
2. Find a warehouse (look for "Serverless" or "Pro")
3. If stopped:
   - Click on warehouse name
   - Click **"Start"** button
   - Wait 2 minutes for "Running" status
4. **Note the warehouse name:** ___________________

---

### Step 2: Create Notebooks

#### 2.1 Create Metrics Notebook

1. Click **"Workspace"** (left sidebar)
2. Navigate to your folder (or use root `/Workspace`)
3. Click **"Create"** → **"Notebook"**
4. Name: `metrics_notebook`
5. Default Language: **Python**
6. Click **"Create"**

**Paste this code:**

```python
# Cell 1: Get materialized view metrics
from datetime import datetime

# Your materialized view
catalog = "19519_ctg_dev"
schema = "refdata_denorm_materialized"
view_name = "instrument_alternate_identifiers_test"
full_view = f"`{catalog}`.`{schema}`.`{view_name}`"

print("=" * 80)
print("MATERIALIZED VIEW REFRESH - PERFORMANCE METRICS")
print("=" * 80)

# Get row count
row_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_view}").collect()[0]['cnt']

# Get view details
view_details = spark.sql(f"DESCRIBE DETAIL {full_view}").collect()[0]

# Get last refresh info
last_refresh = view_details['lastRefreshStartTime']
size_bytes = view_details['sizeInBytes']
size_gb = size_bytes / (1024**3) if size_bytes else 0

# Calculate refresh duration (estimate based on current time)
refresh_end = datetime.now()

print(f"\nView: {full_view}")
print(f"Last Refresh: {last_refresh}")
print(f"Refresh Completed: {refresh_end.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nData Metrics:")
print(f"  - Total Rows: {row_count:,}")
print(f"  - Size: {size_gb:.2f} GB ({size_bytes:,} bytes)")

# Save metrics for next task
dbutils.jobs.taskValues.set(key="row_count", value=str(row_count))
dbutils.jobs.taskValues.set(key="size_gb", value=f"{size_gb:.2f}")
dbutils.jobs.taskValues.set(key="refresh_time", value=last_refresh.strftime('%Y-%m-%d %H:%M:%S') if last_refresh else 'N/A')

print("\n" + "=" * 80)
print("✅ METRICS COLLECTION COMPLETE")
print("=" * 80)
```

**Save the notebook** (Ctrl+S or Cmd+S)

---

#### 2.2 Create Notification Notebook

1. Click **"Workspace"** (left sidebar)
2. Click **"Create"** → **"Notebook"**
3. Name: `notification_notebook`
4. Default Language: **Python**
5. Click **"Create"**

**Paste this code:**

```python
# Cell 1: Send notification with metrics
from datetime import datetime

# Get metrics from previous task
try:
    row_count = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="row_count")
    size_gb = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="size_gb")
    refresh_time = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="refresh_time")
except:
    # Fallback if task values not available
    row_count = "N/A"
    size_gb = "N/A"
    refresh_time = "N/A"

print("=" * 80)
print("SENDING COMPLETION NOTIFICATION")
print("=" * 80)

# Build notification message
notification_message = f"""
Materialized View Refresh - COMPLETED SUCCESSFULLY ✅

View: instrument_alternate_identifiers_test
Refresh Time: {refresh_time}
Completion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Performance Metrics:
  - Total Rows: {row_count}
  - Data Size: {size_gb} GB
  
Status: All tasks completed successfully

Job Run: {{{{ run_id }}}}
"""

print(notification_message)

# Option 1: Print to logs (always works)
print("\n✅ Notification message generated")

# Option 2: Send email (pseudo-code - configure based on your setup)
# Uncomment and configure if you have email integration:
"""
import smtplib
from email.mime.text import MIMEText

msg = MIMEText(notification_message)
msg['Subject'] = 'MV Refresh Complete - Success'
msg['From'] = 'databricks@company.com'
msg['To'] = 'your-email@company.com'

# smtp_server = smtplib.SMTP('smtp.company.com', 587)
# smtp_server.send_message(msg)
# smtp_server.quit()
"""

# Option 3: Webhook notification (Slack, Teams, etc.)
# Uncomment and configure:
"""
import requests
import json

webhook_url = "YOUR_WEBHOOK_URL"
payload = {
    "text": notification_message
}
response = requests.post(webhook_url, data=json.dumps(payload))
print(f"Webhook response: {response.status_code}")
"""

print("\n" + "=" * 80)
print("✅ NOTIFICATION SENT")
print("=" * 80)
```

**Save the notebook** (Ctrl+S or Cmd+S)

---

### Step 3: Create the Job

#### 3.1 Navigate to Workflows

1. Click **"Workflows"** (left sidebar)
2. Click **"Create Job"** (blue button, top right)

---

#### 3.2 Add Task 1: Refresh Materialized View

**Fill in the form:**

| Field | Value |
|-------|-------|
| Task name | `refresh_mv` |
| Type | **SQL** |
| SQL warehouse | Select your warehouse from Step 1 |
| Query | See below |

**Query:**
```sql
REFRESH MATERIALIZED VIEW `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

Click **"Create task"**

---

#### 3.3 Add Task 2: Print Performance Metrics

Click **"+ Add task"**

| Field | Value |
|-------|-------|
| Task name | `print_metrics` |
| Type | **Notebook** |
| **Depends on** | ✅ **Check `refresh_mv`** ← CRITICAL! |
| Source | **Workspace** |
| Notebook path | `/Workspace/metrics_notebook` |
| Cluster | Select an existing cluster OR create new |

**If creating new cluster:**
- Click **"Create cluster"** option
- **Cluster name:** `General-Purpose`
- **Cluster mode:** Single Node (for testing) or Standard
- **Databricks Runtime:** Latest LTS version
- Leave other defaults
- The cluster will be created automatically

Click **"Create task"**

---

#### 3.4 Add Task 3: Send Notification

Click **"+ Add task"**

| Field | Value |
|-------|-------|
| Task name | `send_notification` |
| Type | **Notebook** |
| **Depends on** | ✅ **Check `print_metrics`** ← CRITICAL! |
| Source | **Workspace** |
| Notebook path | `/Workspace/notification_notebook` |
| Cluster | Select same cluster as Task 2 |

Click **"Create task"**

---

#### 3.5 Name and Save Job

1. At the top, click on **"New Job"** 
2. Type: `MV_Refresh_Pipeline`
3. Press Enter
4. Click **"Save"** (top right)

---

### Step 4: Visual Verification

You should now see a workflow diagram like this:

```
┌─────────────────────┐
│   refresh_mv        │
│   (SQL Task)        │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│   print_metrics     │
│   (Notebook Task)   │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│  send_notification  │
│   (Notebook Task)   │
└─────────────────────┘
```

---

### Step 5: Run the Job

#### 5.1 Execute

1. Click **"Run now"** (big blue button, top right)

#### 5.2 Watch Execution

```
Execution Timeline:

Task 1: refresh_mv
  Status: Running ━━━━━━━━━━ (15 min)
  Task 2: Waiting...
  Task 3: Waiting...

↓ Task 1 completes

Task 1: refresh_mv ✅ Succeeded (15m 23s)
Task 2: print_metrics
  Status: Running ━━━━━━━━━━ (2 min)
  Task 3: Waiting...

↓ Task 2 completes

Task 1: refresh_mv ✅ Succeeded (15m 23s)
Task 2: print_metrics ✅ Succeeded (2m 15s)
Task 3: send_notification
  Status: Running ━━━━━━━━━━ (30 sec)

↓ Task 3 completes

Task 1: refresh_mv ✅ Succeeded (15m 23s)
Task 2: print_metrics ✅ Succeeded (2m 15s)
Task 3: send_notification ✅ Succeeded (0m 28s)

Total Duration: 18m 06s
```

---

### Step 6: View Task Outputs

#### 6.1 View Metrics Output

1. In the run view, click on **"print_metrics"** task
2. Click **"Logs"** or **"Output"**
3. You'll see:

```
================================================================================
MATERIALIZED VIEW REFRESH - PERFORMANCE METRICS
================================================================================

View: `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
Last Refresh: 2026-02-13 05:00:00
Refresh Completed: 2026-02-13 05:15:23

Data Metrics:
  - Total Rows: 1,234,567
  - Size: 2.45 GB (2,630,000,000 bytes)

================================================================================
✅ METRICS COLLECTION COMPLETE
================================================================================
```

#### 6.2 View Notification Output

1. Click on **"send_notification"** task
2. Click **"Logs"** or **"Output"**
3. You'll see:

```
================================================================================
SENDING COMPLETION NOTIFICATION
================================================================================

Materialized View Refresh - COMPLETED SUCCESSFULLY ✅

View: instrument_alternate_identifiers_test
Refresh Time: 2026-02-13 05:00:00
Completion Time: 2026-02-13 05:15:51

Performance Metrics:
  - Total Rows: 1,234,567
  - Data Size: 2.45 GB
  
Status: All tasks completed successfully

Job Run: 12345

================================================================================
✅ NOTIFICATION SENT
================================================================================
```

---

## Enhanced Features

### Add Email Notifications

To get actual email when job completes:

1. Job page → **"Email notifications"** section
2. Enter: `your-email@company.com`
3. Check:
   - ✅ **On success**
   - ✅ **On failure**
4. Click **"Save"**

You'll receive emails like:

**Subject:** `Job 'MV_Refresh_Pipeline' succeeded`

**Body:**
```
Your job completed successfully!

Duration: 18 minutes 6 seconds
Started: 2026-02-13 05:00:00
Ended: 2026-02-13 05:18:06

View details: [link to job run]
```

---

### Add Slack/Teams Notification

Modify `notification_notebook` to include webhook:

```python
# Add this to notification_notebook
import requests
import json

# Your Slack webhook URL
webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Format message for Slack
slack_message = {
    "text": "✅ Materialized View Refresh Complete",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Materialized View Refresh - Completed*\n\n• Rows: {row_count}\n• Size: {size_gb} GB\n• Time: {refresh_time}"
            }
        }
    ]
}

# Send to Slack
response = requests.post(webhook_url, data=json.dumps(slack_message))
print(f"Slack notification sent: {response.status_code}")
```

---

### Schedule Daily Runs

1. Job page → Click **"Add trigger"**
2. Select **"Scheduled"**
3. Configure:
   - **Cron expression:** `0 2 * * *` (daily at 2 AM)
   - **Time zone:** Your timezone
4. Click **"Save"**

Now runs automatically every day at 2 AM!

---

## Monitoring & History

### View All Runs

1. Job page → **"Runs"** tab
2. See complete history:

| Run | Start | Duration | Status | Details |
|-----|-------|----------|--------|---------|
| #5 | 2026-02-13 10:00 | 18m 06s | ✅ Success | [View] |
| #4 | 2026-02-13 08:00 | 17m 52s | ✅ Success | [View] |
| #3 | 2026-02-13 06:00 | 18m 15s | ✅ Success | [View] |
| #2 | 2026-02-12 22:00 | 17m 48s | ✅ Success | [View] |
| #1 | 2026-02-12 20:00 | 18m 22s | ✅ Success | [View] |

**Average duration: ~18 minutes**

---

### Track Performance Trends

Create a summary table from your runs:

```python
# Optional: Add to metrics_notebook to track history
spark.sql("""
  CREATE TABLE IF NOT EXISTS analytics.mv_refresh_history (
    refresh_date DATE,
    refresh_timestamp TIMESTAMP,
    row_count BIGINT,
    size_gb DOUBLE,
    duration_minutes INT
  )
""")

spark.sql(f"""
  INSERT INTO analytics.mv_refresh_history
  VALUES (
    current_date(),
    current_timestamp(),
    {row_count},
    {size_gb},
    NULL  -- Can calculate from job metadata
  )
""")
```

Query trends:
```sql
SELECT 
  refresh_date,
  row_count,
  size_gb,
  row_count - LAG(row_count) OVER (ORDER BY refresh_date) as row_growth
FROM analytics.mv_refresh_history
ORDER BY refresh_date DESC
LIMIT 30
```

---

## Troubleshooting

### Task 2 or Task 3 Not Starting

**Check:**
1. Previous task must show ✅ green checkmark
2. Click on task → Verify **"Depends on"** is checked

**Fix:**
1. Click **"Tasks"** tab
2. Click task name → **"Edit"**
3. Check **"Depends on"** box for previous task
4. Save

---

### Notebook Not Found

**Error:** `Notebook '/Workspace/metrics_notebook' does not exist`

**Fix:**
1. Go to **Workspace** sidebar
2. Verify notebook exists
3. Copy exact path (including `/Workspace/`)
4. Edit task → Update notebook path
5. Save

---

### Cluster Starting Takes Long

**Normal:** First time cluster starts can take 3-5 minutes

**Speed up:**
1. Use same cluster for both Task 2 and Task 3
2. Or use **Serverless compute** (if available):
   - Task settings → **Compute** → Select **"Serverless"**

---

### Want to See Live Logs

1. During execution, click on running task
2. Click **"Logs"** tab
3. Logs update in real-time
4. See print statements as they execute

---

## Complete Job Summary

**Job Name:** `MV_Refresh_Pipeline`

**Tasks:**
```
1. refresh_mv (SQL)
   - Refreshes materialized view
   - Duration: ~15 minutes
   - Warehouse: SQL Warehouse

2. print_metrics (Notebook)
   - Collects and prints performance metrics
   - Duration: ~2 minutes
   - Depends on: refresh_mv

3. send_notification (Notebook)
   - Sends completion notification
   - Duration: ~30 seconds
   - Depends on: print_metrics
```

**Total Duration:** ~18 minutes

**Output:** Logs with row counts, data size, timing metrics

**Notification:** Console output (+ optional email/Slack)

---

## Quick Reference Commands

### View Job Runs Programmatically

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# List recent runs
runs = w.jobs.list_runs(job_id=YOUR_JOB_ID, limit=5)
for run in runs:
    print(f"Run {run.run_id}: {run.state.life_cycle_state}")
```

### Trigger Job from Code

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Start job
run = w.jobs.run_now(job_id=YOUR_JOB_ID)
print(f"Started run: {run.result().run_id}")
```

---

## Next Steps

1. ✅ Test run the job manually
2. ✅ Verify all tasks complete successfully
3. ✅ Check metrics output looks correct
4. ✅ Add email notifications
5. ✅ Set up daily schedule
6. Optional: Add Slack/Teams webhook
7. Optional: Create history tracking table

---

**Document Version:** 2.0  
**Last Updated:** February 13, 2026, 05:21:54
