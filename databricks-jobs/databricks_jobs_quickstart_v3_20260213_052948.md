# Databricks Materialized View Refresh Pipeline - Complete Guide
**3-Task Sequential Workflow with Performance Metrics**

Version: 3.0 | Created: February 13, 2026, 05:29:48

---

## Understanding the Architecture

### Why Different Compute Types?

```
Task 1: SQL Warehouse    → Can REFRESH materialized views (required!)
Task 2: General Cluster  → Can run Python code, read from materialized views
Task 3: General Cluster  → Can send notifications, call APIs
```

**Key Concept:** Each task uses the compute type best suited for its job.

---

## How Tasks Communicate

### The Data Flow

```
┌─────────────────────────────────────────┐
│  Databricks Job Orchestrator            │
│  (Manages workflow, no compute itself)  │
└─────────────────────────────────────────┘
         │
         ├─► Task 1: refresh_mv
         │   Compute: SQL Warehouse
         │   Action: REFRESH MATERIALIZED VIEW
         │   Output: Updated materialized view ✅
         │   Duration: ~15 min
         │   Auto-stops when done
         │
         ├─► Task 2: print_metrics
         │   Compute: General Purpose Cluster
         │   Input: Reads materialized view (from Task 1)
         │   Action: spark.sql("SELECT COUNT(*) FROM mv")
         │   Output: Metrics → Task Values
         │   Duration: ~2 min
         │   Cluster stays running
         │
         └─► Task 3: send_notification
             Compute: Same General Purpose Cluster (reused!)
             Input: Gets metrics from Task 2 (via Task Values)
             Action: Send email/Slack notification
             Duration: ~30 sec
             Cluster auto-stops after completion
```

### What Each Task Can and Cannot Do

| Operation | SQL Warehouse | General Cluster |
|-----------|---------------|-----------------|
| REFRESH materialized view | ✅ YES (only option!) | ❌ NO - Error |
| READ materialized view | ✅ YES | ✅ YES |
| Run Python code | ❌ NO | ✅ YES |
| Install Python libraries | ❌ NO | ✅ YES |
| Send HTTP requests | ❌ NO | ✅ YES |
| Complex calculations | ✅ YES (SQL only) | ✅ YES (any language) |

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
│   │   │   │   └── Uses SQL Warehouse compute
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
│   │   │   │   │   └── Uses General Purpose compute
│   │   │   │   └── [Create task] button
│   │   │   │
│   │   │   └── + Add task (button)
│   │   │       │
│   │   │       └── Task 3 Configuration
│   │   │           ├── Task name: send_notification
│   │   │           ├── Type: Notebook ▼
│   │   │           ├── Depends on: ✅ print_metrics ← CHECK THIS!
│   │   │           ├── Notebook path: /Workspace/notification_notebook
│   │   │           ├── Cluster: [Same as Task 2] ▼
│   │   │           │   └── Reuses same cluster (efficient!)
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

**Why:** Only SQL Warehouse can REFRESH materialized views

1. Click **"SQL Warehouses"** (left sidebar)
2. Find a warehouse (look for "Serverless" or "Pro")
3. If stopped:
   - Click on warehouse name
   - Click **"Start"** button
   - Wait 2 minutes for "Running" status
4. **Note the warehouse name:** ___________________

**What this warehouse will do:**
- Execute the REFRESH MATERIALIZED VIEW command
- Auto-stop after Task 1 completes (saves cost)

---

### Step 2: Create Notebooks

#### 2.1 Create Metrics Notebook

**Why:** General cluster can run Python, read materialized view data

1. Click **"Workspace"** (left sidebar)
2. Navigate to your folder (or use root `/Workspace`)
3. Click **"Create"** → **"Notebook"**
4. Name: `metrics_notebook`
5. Default Language: **Python**
6. Click **"Create"**

**Paste this code:**

```python
# This notebook runs on GENERAL PURPOSE CLUSTER (not SQL Warehouse)
# It CAN read from materialized views
# It CANNOT refresh materialized views

from datetime import datetime

# Configuration
catalog = "19519_ctg_dev"
schema = "refdata_denorm_materialized"
view_name = "instrument_alternate_identifiers_test"
full_view = f"`{catalog}`.`{schema}`.`{view_name}`"

print("=" * 80)
print("MATERIALIZED VIEW REFRESH - PERFORMANCE METRICS")
print("=" * 80)
print(f"\nRunning on: General Purpose Cluster")
print(f"Task: Reading materialized view (refreshed by Task 1)")

# READ from materialized view (this works on general cluster!)
print(f"\nQuerying: {full_view}")
row_count_df = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_view}")
row_count = row_count_df.collect()[0]['cnt']

# Get view metadata
view_details = spark.sql(f"DESCRIBE DETAIL {full_view}").collect()[0]
last_refresh = view_details['lastRefreshStartTime']
size_bytes = view_details['sizeInBytes']
size_gb = size_bytes / (1024**3) if size_bytes else 0

# Calculate metrics
refresh_end = datetime.now()

print(f"\n{'='*80}")
print("VIEW INFORMATION")
print(f"{'='*80}")
print(f"Full Name: {full_view}")
print(f"Last Refresh Started: {last_refresh}")
print(f"Metrics Collected At: {refresh_end.strftime('%Y-%m-%d %H:%M:%S')}")

print(f"\n{'='*80}")
print("DATA METRICS")
print(f"{'='*80}")
print(f"Total Rows: {row_count:,}")
print(f"Data Size: {size_gb:.2f} GB ({size_bytes:,} bytes)")
print(f"Avg Row Size: {size_bytes/row_count if row_count > 0 else 0:.2f} bytes")

# Save metrics to pass to next task
dbutils.jobs.taskValues.set(key="row_count", value=str(row_count))
dbutils.jobs.taskValues.set(key="size_gb", value=f"{size_gb:.2f}")
dbutils.jobs.taskValues.set(key="refresh_time", value=last_refresh.strftime('%Y-%m-%d %H:%M:%S') if last_refresh else 'N/A')
dbutils.jobs.taskValues.set(key="view_name", value=view_name)

print(f"\n{'='*80}")
print("✅ METRICS COLLECTION COMPLETE")
print(f"{'='*80}")
print("\nNote: This task ran on General Purpose Cluster")
print("      Task 1 (SQL Warehouse) did the actual REFRESH")
print("      This task just READ the refreshed data")
```

**Save the notebook** (Ctrl+S or Cmd+S)

**What this notebook does:**
- Runs on General Purpose Cluster (has Python/Spark)
- Reads from the materialized view (already refreshed by Task 1)
- Cannot do REFRESH (would error if attempted)
- Passes metrics to Task 3 using task values

---

#### 2.2 Create Notification Notebook

**Why:** Send notifications using Python libraries (not possible in SQL Warehouse)

1. Click **"Workspace"** (left sidebar)
2. Click **"Create"** → **"Notebook"**
3. Name: `notification_notebook`
4. Default Language: **Python**
5. Click **"Create"**

**Paste this code:**

```python
# This notebook runs on GENERAL PURPOSE CLUSTER (same as Task 2)
# Cluster is reused from Task 2 (cost efficient!)

from datetime import datetime

print("=" * 80)
print("NOTIFICATION TASK - SENDING COMPLETION ALERT")
print("=" * 80)
print(f"\nRunning on: General Purpose Cluster (reused from Task 2)")

# Get metrics from Task 2 using task values
# (This is how tasks communicate!)
try:
    row_count = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="row_count")
    size_gb = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="size_gb")
    refresh_time = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="refresh_time")
    view_name = dbutils.jobs.taskValues.get(taskKey="print_metrics", key="view_name")
    
    print(f"\n✅ Successfully retrieved metrics from Task 2:")
    print(f"   - View: {view_name}")
    print(f"   - Rows: {row_count}")
    print(f"   - Size: {size_gb} GB")
    print(f"   - Refresh Time: {refresh_time}")
except Exception as e:
    print(f"\n⚠️  Could not retrieve metrics: {e}")
    row_count = "N/A"
    size_gb = "N/A"
    refresh_time = "N/A"
    view_name = "unknown"

# Build notification message
completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

notification_message = f"""
{'='*80}
MATERIALIZED VIEW REFRESH - COMPLETED SUCCESSFULLY ✅
{'='*80}

View Name: {view_name}
Catalog: 19519_ctg_dev
Schema: refdata_denorm_materialized

TIMING:
  Refresh Started: {refresh_time}
  Notification Sent: {completion_time}

PERFORMANCE METRICS:
  Total Rows: {row_count}
  Data Size: {size_gb} GB
  
WORKFLOW:
  Task 1 (SQL Warehouse): Refreshed materialized view
  Task 2 (General Cluster): Collected metrics  
  Task 3 (General Cluster): Sending this notification

STATUS: All tasks completed successfully ✅

{'='*80}
"""

print(notification_message)

# Option 1: Console output (always works)
print("\n✅ Notification message generated and printed to logs")

# Option 2: Email notification (uncomment and configure)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

msg = MIMEMultipart()
msg['Subject'] = f'MV Refresh Complete: {view_name}'
msg['From'] = 'databricks@company.com'
msg['To'] = 'your-email@company.com'
msg.attach(MIMEText(notification_message, 'plain'))

# Configure your SMTP settings
smtp_server = 'smtp.company.com'
smtp_port = 587

# Send email
server = smtplib.SMTP(smtp_server, smtp_port)
server.starttls()
# server.login('username', 'password')  # If authentication required
server.send_message(msg)
server.quit()

print("✅ Email notification sent")
"""

# Option 3: Slack webhook (uncomment and configure)
"""
import requests
import json

webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

slack_payload = {
    "text": "✅ Materialized View Refresh Complete",
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "MV Refresh Pipeline Completed"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*View:*\n{view_name}"},
                {"type": "mrkdwn", "text": f"*Status:*\n✅ Success"}
            ]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Rows:*\n{row_count}"},
                {"type": "mrkdwn", "text": f"*Size:*\n{size_gb} GB"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Completed:* {completion_time}"
            }
        }
    ]
}

response = requests.post(webhook_url, data=json.dumps(slack_payload))
if response.status_code == 200:
    print("✅ Slack notification sent")
else:
    print(f"⚠️  Slack notification failed: {response.status_code}")
"""

# Option 4: Microsoft Teams webhook (uncomment and configure)
"""
import requests
import json

teams_webhook = "https://outlook.office.com/webhook/YOUR/WEBHOOK/URL"

teams_payload = {
    "@type": "MessageCard",
    "@context": "https://schema.org/extensions",
    "summary": "MV Refresh Complete",
    "themeColor": "00FF00",
    "title": "✅ Materialized View Refresh Complete",
    "sections": [
        {
            "facts": [
                {"name": "View", "value": view_name},
                {"name": "Rows", "value": row_count},
                {"name": "Size", "value": f"{size_gb} GB"},
                {"name": "Completed", "value": completion_time}
            ]
        }
    ]
}

response = requests.post(teams_webhook, json=teams_payload)
if response.status_code == 200:
    print("✅ Teams notification sent")
else:
    print(f"⚠️  Teams notification failed: {response.status_code}")
"""

print("\n" + "=" * 80)
print("✅ NOTIFICATION TASK COMPLETE")
print("=" * 80)
print("\nNote: This task ran on General Purpose Cluster")
print("      Same cluster as Task 2 (reused for efficiency)")
print("      Python libraries (requests, smtplib) are available here")
```

**Save the notebook** (Ctrl+S or Cmd+S)

**What this notebook does:**
- Runs on General Purpose Cluster (reused from Task 2)
- Gets metrics from Task 2 via task values
- Can use Python libraries (requests, smtplib) to send notifications
- Cannot run on SQL Warehouse (no Python support)

---

### Step 3: Create the Job

#### 3.1 Navigate to Workflows

1. Click **"Workflows"** (left sidebar)
2. Click **"Create Job"** (blue button, top right)

---

#### 3.2 Add Task 1: Refresh Materialized View

**Compute: SQL Warehouse** ← Only option for REFRESH!

| Field | Value |
|-------|-------|
| Task name | `refresh_mv` |
| Type | **SQL** |
| SQL warehouse | Select your warehouse from Step 1 |
| Query | See below |

**Query:**
```sql
-- This runs on SQL WAREHOUSE (only compute that supports REFRESH)
-- General Purpose clusters CANNOT run this command
REFRESH MATERIALIZED VIEW `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
```

Click **"Create task"**

**What happens when this runs:**
- Job sends query to SQL Warehouse
- SQL Warehouse refreshes the materialized view
- View is now updated with latest data
- SQL Warehouse auto-stops (saves cost)
- Task 1 completes ✅
- Job moves to Task 2

---

#### 3.3 Add Task 2: Print Performance Metrics

**Compute: General Purpose Cluster** ← Needed for Python

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
- **Cluster name:** `General-Purpose`
- **Cluster mode:** Single Node (for testing) or Standard
- **Databricks Runtime:** Latest LTS version
- Leave other defaults

Click **"Create task"**

**What happens when this runs:**
- Task 2 waits for Task 1 to complete
- General Purpose cluster starts (or reuses if running)
- Cluster loads and executes `metrics_notebook`
- Notebook reads from materialized view (refreshed by Task 1)
- Notebook prints metrics to logs
- Notebook saves metrics to task values
- Cluster stays running for Task 3
- Task 2 completes ✅
- Job moves to Task 3

---

#### 3.4 Add Task 3: Send Notification

**Compute: General Purpose Cluster** ← Reuses cluster from Task 2!

Click **"+ Add task"**

| Field | Value |
|-------|-------|
| Task name | `send_notification` |
| Type | **Notebook** |
| **Depends on** | ✅ **Check `print_metrics`** ← CRITICAL! |
| Source | **Workspace** |
| Notebook path | `/Workspace/notification_notebook` |
| Cluster | **Select SAME cluster as Task 2** ← Efficient! |

Click **"Create task"**

**What happens when this runs:**
- Task 3 waits for Task 2 to complete
- Reuses the same cluster (already running from Task 2)
- Cluster loads and executes `notification_notebook`
- Notebook gets metrics from Task 2 via task values
- Notebook sends notification
- Cluster auto-stops (saves cost)
- Task 3 completes ✅
- Job completes ✅

---

#### 3.5 Name and Save Job

1. At the top, click on **"New Job"** 
2. Type: `MV_Refresh_Pipeline`
3. Press Enter
4. Click **"Save"** (top right)

---

### Step 4: Visual Verification

You should see a workflow diagram like this:

```
┌─────────────────────────────┐
│   refresh_mv                │
│   Type: SQL                 │
│   Compute: SQL Warehouse    │
│   Duration: ~15 min         │
└──────────┬──────────────────┘
           │ Depends on
           ↓
┌─────────────────────────────┐
│   print_metrics             │
│   Type: Notebook            │
│   Compute: General Cluster  │
│   Duration: ~2 min          │
└──────────┬──────────────────┘
           │ Depends on
           ↓
┌─────────────────────────────┐
│   send_notification         │
│   Type: Notebook            │
│   Compute: Same Cluster     │
│   Duration: ~30 sec         │
└─────────────────────────────┘
```

---

## Understanding the Execution Flow

### Behind the Scenes

```
Job Orchestrator starts
│
├─► Task 1: refresh_mv
│   ├─► Send query to SQL Warehouse
│   ├─► SQL Warehouse starts (if stopped)
│   ├─► Execute: REFRESH MATERIALIZED VIEW
│   ├─► Materialized view updated ✅
│   ├─► SQL Warehouse auto-stops
│   └─► Task 1 complete ✅
│
├─► Task 2: print_metrics (waits for Task 1)
│   ├─► Start General Purpose cluster
│   ├─► Load /Workspace/metrics_notebook
│   ├─► Execute Python code:
│   │   ├─► spark.sql("SELECT COUNT(*) FROM mv")  ← Reads refreshed view
│   │   ├─► Calculate metrics
│   │   ├─► Print to logs
│   │   └─► Save to task values
│   ├─► Cluster stays running
│   └─► Task 2 complete ✅
│
└─► Task 3: send_notification (waits for Task 2)
    ├─► Reuse cluster from Task 2 (already running!)
    ├─► Load /Workspace/notification_notebook
    ├─► Execute Python code:
    │   ├─► Get task values from Task 2
    │   ├─► Build notification message
    │   ├─► Send via email/Slack/Teams
    │   └─► Print confirmation
    ├─► Cluster auto-stops
    └─► Task 3 complete ✅

Job complete ✅
Total duration: ~18 minutes
```

---

### Step 5: Run the Job

#### 5.1 Execute

1. Click **"Run now"** (big blue button, top right)

#### 5.2 Watch Execution

**Minute 0-15: Task 1 Running**
```
┌─────────────────────────────────────────┐
│ Task 1: refresh_mv                      │
│ Status: Running ━━━━━━━━━━ 12m 34s     │
│ Compute: SQL Warehouse (active)         │
│                                         │
│ Task 2: print_metrics                   │
│ Status: Waiting for Task 1...           │
│ Compute: Cluster not started yet        │
│                                         │
│ Task 3: send_notification               │
│ Status: Waiting for Task 2...           │
│ Compute: Cluster not started yet        │
└─────────────────────────────────────────┘
```

**Minute 15-17: Task 2 Running**
```
┌─────────────────────────────────────────┐
│ Task 1: refresh_mv                      │
│ Status: ✅ Succeeded (15m 23s)          │
│ Compute: SQL Warehouse (stopped)        │
│                                         │
│ Task 2: print_metrics                   │
│ Status: Running ━━━━━━━━━━ 1m 45s      │
│ Compute: General Cluster (starting...)  │
│                                         │
│ Task 3: send_notification               │
│ Status: Waiting for Task 2...           │
│ Compute: Cluster will be reused         │
└─────────────────────────────────────────┘
```

**Minute 17-18: Task 3 Running**
```
┌─────────────────────────────────────────┐
│ Task 1: refresh_mv                      │
│ Status: ✅ Succeeded (15m 23s)          │
│ Compute: SQL Warehouse (stopped)        │
│                                         │
│ Task 2: print_metrics                   │
│ Status: ✅ Succeeded (2m 15s)           │
│ Compute: General Cluster (running)      │
│                                         │
│ Task 3: send_notification               │
│ Status: Running ━━━━━━━━━━ 0m 18s      │
│ Compute: General Cluster (reused!)      │
└─────────────────────────────────────────┘
```

**Minute 18: All Complete**
```
┌─────────────────────────────────────────┐
│ Task 1: refresh_mv                      │
│ Status: ✅ Succeeded (15m 23s)          │
│ Compute: SQL Warehouse (stopped)        │
│                                         │
│ Task 2: print_metrics                   │
│ Status: ✅ Succeeded (2m 15s)           │
│ Compute: General Cluster (stopped)      │
│                                         │
│ Task 3: send_notification               │
│ Status: ✅ Succeeded (0m 28s)           │
│ Compute: General Cluster (stopped)      │
│                                         │
│ Total Duration: 18m 06s                 │
└─────────────────────────────────────────┘
```

---

### Step 6: View Task Outputs

#### 6.1 Task 1 Output (SQL Warehouse)

1. Click on **"refresh_mv"** task
2. Click **"Logs"**
3. You'll see:

```
Query: REFRESH MATERIALIZED VIEW `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
Status: Success
Duration: 15m 23s
Warehouse: Performance-Test-Warehouse
```

---

#### 6.2 Task 2 Output (General Cluster - Python)

1. Click on **"print_metrics"** task
2. Click **"Logs"** or **"Output"**
3. You'll see:

```
================================================================================
MATERIALIZED VIEW REFRESH - PERFORMANCE METRICS
================================================================================

Running on: General Purpose Cluster
Task: Reading materialized view (refreshed by Task 1)

Querying: `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`

================================================================================
VIEW INFORMATION
================================================================================
Full Name: `19519_ctg_dev`.`refdata_denorm_materialized`.`instrument_alternate_identifiers_test`
Last Refresh Started: 2026-02-13 05:00:00
Metrics Collected At: 2026-02-13 05:15:23

================================================================================
DATA METRICS
================================================================================
Total Rows: 1,234,567
Data Size: 2.45 GB (2,630,000,000 bytes)
Avg Row Size: 2,130.45 bytes

================================================================================
✅ METRICS COLLECTION COMPLETE
================================================================================

Note: This task ran on General Purpose Cluster
      Task 1 (SQL Warehouse) did the actual REFRESH
      This task just READ the refreshed data
```

---

#### 6.3 Task 3 Output (General Cluster - Python)

1. Click on **"send_notification"** task
2. Click **"Logs"** or **"Output"**
3. You'll see:

```
================================================================================
NOTIFICATION TASK - SENDING COMPLETION ALERT
================================================================================

Running on: General Purpose Cluster (reused from Task 2)

✅ Successfully retrieved metrics from Task 2:
   - View: instrument_alternate_identifiers_test
   - Rows: 1234567
   - Size: 2.45 GB
   - Refresh Time: 2026-02-13 05:00:00

================================================================================
MATERIALIZED VIEW REFRESH - COMPLETED SUCCESSFULLY ✅
================================================================================

View Name: instrument_alternate_identifiers_test
Catalog: 19519_ctg_dev
Schema: refdata_denorm_materialized

TIMING:
  Refresh Started: 2026-02-13 05:00:00
  Notification Sent: 2026-02-13 05:15:51

PERFORMANCE METRICS:
  Total Rows: 1234567
  Data Size: 2.45 GB
  
WORKFLOW:
  Task 1 (SQL Warehouse): Refreshed materialized view
  Task 2 (General Cluster): Collected metrics  
  Task 3 (General Cluster): Sending this notification

STATUS: All tasks completed successfully ✅

================================================================================

✅ Notification message generated and printed to logs

================================================================================
✅ NOTIFICATION TASK COMPLETE
================================================================================

Note: This task ran on General Purpose Cluster
      Same cluster as Task 2 (reused for efficiency)
      Python libraries (requests, smtplib) are available here
```

---

## Why This Architecture?

### Compute Type Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                     SQL WAREHOUSE                           │
├─────────────────────────────────────────────────────────────┤
│ ✅ Can REFRESH materialized views (ONLY option)             │
│ ✅ Can run SQL queries                                       │
│ ✅ Auto-scaling, serverless                                 │
│ ✅ Optimized for SQL operations                             │
│ ❌ Cannot run Python code                                   │
│ ❌ Cannot install libraries                                 │
│ ❌ Cannot send HTTP requests                                │
│                                                             │
│ Best for: REFRESH operations, SQL analytics                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  GENERAL PURPOSE CLUSTER                    │
├─────────────────────────────────────────────────────────────┤
│ ✅ Can run Python/Scala/R code                              │
│ ✅ Can install Python libraries                             │
│ ✅ Can send HTTP requests (email, Slack, etc.)              │
│ ✅ Can READ materialized views                              │
│ ✅ Full Spark functionality                                 │
│ ❌ Cannot REFRESH materialized views                        │
│                                                             │
│ Best for: Complex processing, ML, notifications             │
└─────────────────────────────────────────────────────────────┘
```

---

### What If We Tried Different Approaches?

#### Attempt 1: All Tasks on SQL Warehouse ❌

```
Task 1: REFRESH MV (SQL Warehouse) ✅
Task 2: Get metrics (SQL Warehouse) ✅ - Could work with SQL only
Task 3: Send notification (SQL Warehouse) ❌ - CANNOT send emails/Slack
```

**Problem:** SQL Warehouse can't run Python or send notifications

---

#### Attempt 2: All Tasks on General Cluster ❌

```
Task 1: REFRESH MV (General Cluster) ❌ - FORBIDDEN!
Task 2: Get metrics (General Cluster) ✅
Task 3: Send notification (General Cluster) ✅
```

**Problem:** This is the error you got originally!
```
[MATERIALIZED_VIEW_OPERATION_NOT_ALLOWED.REQUIRES_DBSQL_PRO_PLUS]
Cannot REFRESH the Materialized View from general compute
```

---

#### Attempt 3: Mixed Compute (Current Solution) ✅

```
Task 1: REFRESH MV (SQL Warehouse) ✅
Task 2: Get metrics (General Cluster) ✅
Task 3: Send notification (General Cluster) ✅
```

**Why this works:**
- Each task uses the right compute
- SQL Warehouse for REFRESH (only option)
- General Cluster for Python (flexibility)
- Seamless handoff via materialized view data

---

## Cost Optimization

### Compute Usage Timeline

```
Time      SQL Warehouse          General Cluster
00:00     Starting...            Stopped
00:02     Running (Task 1)       Stopped
...
15:23     Task 1 complete        Stopped
15:23     Auto-stopping          Starting...
15:25     Stopped ✅             Running (Task 2)
...
17:38     Stopped                Task 2 complete
17:38     Stopped                Running (Task 3)
18:06     Stopped                Task 3 complete
18:06     Stopped                Auto-stopping
18:08     Stopped ✅             Stopped ✅
```

**Cost savings:**
- SQL Warehouse: Only runs for 15 minutes (Task 1)
- General Cluster: Only runs for 3 minutes (Tasks 2 & 3)
- Cluster reuse: Task 3 doesn't restart cluster
- Auto-stop: Both compute types stop when idle

---

## Troubleshooting by Compute Type

### Error: "Cannot REFRESH from general compute"

```
Task 1: Type is Notebook (wrong!)
Error: MATERIALIZED_VIEW_OPERATION_NOT_ALLOWED
```

**Fix:**
1. Task 1 must be Type: **SQL** (not Notebook)
2. Task 1 must use **SQL Warehouse** (not General Cluster)

---

### Error: "Notebook not found"

```
Task 2: Cannot find /Workspace/metrics_notebook
```

**Fix:**
1. Go to Workspace sidebar
2. Verify notebook exists at exact path
3. Update task with correct path

---

### Error: "Cluster starting timeout"

```
Task 2: Cluster starting... (stuck)
```

**Fix:**
1. Use smaller cluster for testing (Single Node)
2. Or reuse existing cluster
3. Check cluster permissions

---

### Error: "Task values not found"

```
Task 3: Cannot get metrics from Task 2
```

**Fix:**
1. Verify Task 2 has: `dbutils.jobs.taskValues.set(...)`
2. Verify Task 3 uses correct taskKey: `print_metrics`
3. Check Task 2 completed successfully

---

## Advanced: Alternative Architectures

### Scenario 1: All SQL Processing

```
Task 1: REFRESH MV (SQL Warehouse)
Task 2: Aggregate data (SQL Warehouse)
Task 3: Insert summary (SQL Warehouse)
```

**All tasks on same SQL Warehouse - efficient for SQL-only workflows!**

---

### Scenario 2: ML Pipeline

```
Task 1: REFRESH MV (SQL Warehouse)
Task 2: Train model (ML Runtime Cluster)
Task 3: Deploy model (ML Runtime Cluster)
Task 4: Send results (General Cluster)
```

**Different cluster types for different workloads!**

---

### Scenario 3: Parallel Processing

```
Task 1: REFRESH MV (SQL Warehouse)
├─► Task 2a: Process region A (Cluster 1)
├─► Task 2b: Process region B (Cluster 2)
└─► Task 2c: Process region C (Cluster 3)
    └─► Task 3: Combine results (Cluster 1)
```

**Parallel tasks on different clusters for speed!**

---

## Summary

**Key Takeaways:**

1. **SQL Warehouse:**
   - ONLY option for REFRESH MATERIALIZED VIEW
   - Auto-stops after task completes
   - Optimized for SQL operations

2. **General Purpose Cluster:**
   - Runs Python/Scala/R code
   - Can READ materialized views
   - Can send notifications
   - Cluster reused across tasks

3. **Task Communication:**
   - Materialized view = data bridge
   - Task values = metadata bridge
   - Job orchestrator manages flow

4. **Cost Efficiency:**
   - Each compute type runs only when needed
   - Cluster reuse saves startup time
   - Auto-stop prevents waste

**The Pipeline:**
```
SQL Warehouse (15 min) → Writes MV →
General Cluster (2 min) → Reads MV, writes task values →
General Cluster (30 sec) → Reads task values, sends notification
```

**Total: ~18 minutes, fully automated, cost-optimized!**

---

**Document Version:** 3.0  
**Last Updated:** February 13, 2026, 05:29:48
