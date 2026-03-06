# Databricks Sandbox Environment Setup Guide

## Overview

This guide walks through adding a **sandbox** environment to an existing DBX repo that already has `dev`, `test`, and `prod` environments. The sandbox runs on the **same Databricks workspace** as test but uses a **different folder path**.

---

## Prerequisites

- Existing DBX repo cloned locally
- Access to the Databricks workspace on AWS
- IntelliJ IDEA (or any editor)
- Python 3.8+ and pip installed
- DBX and Databricks CLI installed (same version as your team)

---

## Step 1 — Create the Sandbox Branch

```bash
git checkout test
git pull
git checkout -b sandbox
```

---

## Step 2 — Install DBX Locally (if not already installed)

```bash
# recommended: use a virtual environment
python -m venv .venv

# activate (Mac/Linux)
source .venv/bin/activate

# activate (Windows)
.venv\Scripts\activate

# install dbx and databricks CLI
pip install dbx
pip install databricks-cli

# verify
dbx --version
databricks --version

# install project dependencies
pip install -r requirements.txt
```

---

## Step 3 — Get Your Databricks Host and Token

### Get the Host URL
1. Log into your Databricks workspace on AWS
2. Look at the browser URL bar — copy everything before `/browse?o=...`
3. It will look like:
```
https://dbc-a1b2345c-d6e7.cloud.databricks.com
```
> **Note:** Ignore the `?o=4839439494330` part — that is just the workspace ID used for navigation, not part of the host.

### Generate a Token
1. Log into your Databricks workspace
2. Click your **profile icon** → top right corner
3. Click **Settings**
4. Click **Developer** on the left menu
5. Click **Access Tokens** → **Manage**
6. Click **Generate New Token**
7. Give it a name e.g. `sandbox-local`
8. Set expiry or leave blank for no expiry
9. Click **Generate**
10. **Copy the token immediately** — it is only shown once

---

## Step 4 — Configure `~/.databrickscfg`

Open the file in a text editor:

**Windows (PowerShell):**
```powershell
notepad $HOME\.databrickscfg
```

**Mac/Linux:**
```bash
nano ~/.databrickscfg
```

Add the sandbox profile (same host/token as test since it's the same workspace):

```ini
[sandbox]
host  = https://dbc-a1b2345c-d6e7.cloud.databricks.com
token = dapiXXXXXXXXXXXXXXXXXXXXXXXX
```

Save the file.

### Verify it works:
```bash
databricks --profile sandbox workspace ls /
```

---

## Step 5 — Update `.dbx/project.json`

Open `.dbx/project.json` in IntelliJ and add the sandbox block, modelled after the `test` environment but with a different path:

```json
{
  "environments": {
    "default": {
      "profile": "default",
      "storage_type": "mlflow",
      "properties": {
        "workspace_directory": "/dbx/projects/my-project",
        "artifact_location": "dbfs:/dbx/projects/my-project"
      }
    },
    "test": {
      "profile": "test",
      "storage_type": "mlflow",
      "properties": {
        "workspace_directory": "/dbx/projects/my-project/test",
        "artifact_location": "dbfs:/dbx/projects/my-project/test"
      }
    },
    "sandbox": {
      "profile": "sandbox",
      "storage_type": "mlflow",
      "properties": {
        "workspace_directory": "/dbx/projects/my-project/sandbox",
        "artifact_location": "dbfs:/dbx/projects/my-project/sandbox"
      }
    }
  }
}
```

> **Note:** Replace `my-project` with your actual project name. Match the path pattern used by your existing environments.

---

## Step 6 — Update `conf/deployment.yml`

Open `conf/deployment.yml` and add a `sandbox` block, copied from `test` with renamed jobs:

```yaml
environments:
  default:
    jobs:
      - name: my-job

  test:
    jobs:
      - name: my-job-test
        tasks:
          - task_key: main
            spark_python_task:
              python_file: src/jobs/my_job.py
            libraries:
              - whl: dist/*.whl

  # ADD THIS BLOCK
  sandbox:
    jobs:
      - name: my-job-sandbox        # rename from my-job-test
        tasks:
          - task_key: main
            spark_python_task:
              python_file: src/jobs/my_job.py
            libraries:
              - whl: dist/*.whl
```

> **Note:** Replace job names and task config with your actual values from the `test` block.

---

## Step 7 — Deploy to Sandbox

```bash
# always explicitly pass --environment=sandbox
# never rely on default

# dry run first to validate config
dbx deploy --environment=sandbox --dry-run

# actual deploy
dbx deploy --environment=sandbox

# run a specific job
dbx launch --environment=sandbox --job=my-job-sandbox
```

---

## Key File Summary

| File | What Changed |
|------|-------------|
| `.dbx/project.json` | Added `sandbox` env block with new workspace path |
| `conf/deployment.yml` | Added `sandbox` env block with renamed jobs |
| `~/.databrickscfg` | Added `[sandbox]` profile with host and token |

---

## Important Rules

- **Always pass** `--environment=sandbox` explicitly — never let it fall back to `default`
- The workspace directory path for sandbox **does not need to exist** upfront — DBX will create it on first deploy
- The `?o=XXXXXXX` in your browser URL is **not** part of the host — exclude it from `.databrickscfg`
- AWS Databricks host format: `https://dbc-xxxxxxxx-xxxx.cloud.databricks.com`
- Azure Databricks host format (for reference): `https://adb-xxxxxxxxx.x.azuredatabricks.net`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `environment sandbox not found` | Check `conf/deployment.yml` has a `sandbox` block |
| `Authentication error` | Re-run `databricks configure --token --profile sandbox` |
| `dbx: command not found` | Activate your virtual env: `source .venv/bin/activate` |
| `profile sandbox not found` | Check `~/.databrickscfg` has a `[sandbox]` section |
| Wrong workspace being used | Make sure you're passing `--environment=sandbox` explicitly |
