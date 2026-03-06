# Snyk Path Traversal Fix — CWE-23
**File:** `cicd/scripts/Permissions_grant.py` | **Line:** 34

---

## What the Vulnerability Is

Snyk flagged that `sys.argv[1]` (user input from the command line) flows directly into `open()` without any checks. This means someone could pass a malicious value like `../../etc/passwd` and the script would try to open that file.

---

## The Fix — 4 Lines Added at Line 76

### Before (vulnerable)
```python
env = sys.argv[1]
```

### After (fixed)
```python
env = sys.argv[1].strip()

allowed_envs = ["dev", "staging", "prod"]  # ← update with your actual env names
if env not in allowed_envs:
    print(f"Error: '{env}' is not a valid environment.")
    sys.exit(1)
```

---

## What Each Line Means

| Line | What it does |
|------|-------------|
| `env = sys.argv[1].strip()` | Same as before, just removes accidental spaces. No behaviour change. |
| `allowed_envs = ["dev", "staging", "prod"]` | A guest list of valid environment names your script is allowed to accept. |
| `if env not in allowed_envs:` | Checks if what was passed is on the guest list. |
| `print(...)` + `sys.exit(1)` | If not on the list, print a clear error and stop the script immediately. |

---

## Will It Break Anything?

**No — as long as your pipeline passes a value that's in `allowed_envs`.**

Before applying, check how the script is called in your CI/CD pipeline:

```bash
# Example — what value is passed as the argument?
python Permissions_grant.py prod
```

Make sure every environment name your pipeline uses is included in the list:

```python
allowed_envs = ["dev", "staging", "prod"]  # add/remove as needed
```

If `prod` is the only env you use, just leave `"prod"` in the list.

---

## Why This Fixes the Snyk Issue

- Before: any value could be passed → attacker could manipulate the file path
- After: only known, safe values are accepted → file path can never point outside your intended folder
- The rest of the script (file reading, permissions logic, Databricks calls) is **completely unchanged**

---

## Summary

> Just add 4 lines after `env = sys.argv[1]`, update the `allowed_envs` list to match your real environment names, and you're done.
