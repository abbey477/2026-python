# Performance Test: Standard View vs Materialized View
**Python-only version - Simple and clean**

**Prerequisites:** 
- `test_sales` table already exists
- `standard_view` already exists
- `materialized_view` already exists

---

## Cell 1: Setup - Import Libraries

```python
import time

print("✓ Libraries loaded")
```

---

## Cell 2: Reusable Test Function

```python
def run_performance_test(test_name, query_func, iterations=5):
    """
    Reusable function to test any query
    - Clears cache before each run
    - Runs multiple iterations
    - Returns average time and record count
    """
    times = []
    record_count = None
    
    for i in range(iterations):
        spark.catalog.clearCache()
        
        start = time.time()
        result = query_func()
        elapsed = time.time() - start
        
        times.append(elapsed)
        
        # Get record count from first run
        if i == 0 and result is not None:
            record_count = len(result)
        
        print(f"  Run {i+1}: {elapsed:.3f}s")
    
    avg = sum(times) / len(times)
    
    if record_count is not None:
        print(f"✓ {test_name}: {avg:.3f}s average, {record_count:,} records\n")
    else:
        print(f"✓ {test_name}: {avg:.3f}s average\n")
    
    return avg, record_count

print("✓ Test function loaded")
```

---

## Cell 3: Test Standard View

```python
print("Testing Standard View (cache disabled)...\n")

# Test standard view (assumes 'standard_view' already exists)
def query_standard():
    return spark.sql("SELECT * FROM standard_view").collect()

std_time, std_count = run_performance_test("Standard View", query_standard, iterations=5)
```

---

## Cell 4: Test Materialized View - ASYNC Refresh

```python
print("Testing Materialized View - ASYNC Refresh...\n")

# Test ASYNC: Just trigger refresh, don't wait
def async_refresh():
    spark.sql("REFRESH MATERIALIZED VIEW materialized_view")
    # Returns immediately, doesn't wait
    return None  # No records returned

async_time, _ = run_performance_test("MV ASYNC Refresh (trigger only)", async_refresh, iterations=5)

# Wait for last refresh to complete before continuing
print("Waiting for refresh to complete...")
while True:
    try:
        spark.sql("SELECT 1 FROM materialized_view LIMIT 1").collect()
        break
    except:
        time.sleep(0.5)
print("✓ Ready for next test\n")
```

---

## Cell 5: Test Materialized View - SYNC Refresh

```python
print("Testing Materialized View - SYNC Refresh...\n")

# Test SYNC: Trigger refresh AND wait for completion
def sync_refresh():
    spark.sql("REFRESH MATERIALIZED VIEW materialized_view")
    
    # Wait for completion
    while True:
        try:
            spark.sql("SELECT 1 FROM materialized_view LIMIT 1").collect()
            break
        except:
            time.sleep(0.5)
    
    return None  # No records returned

sync_time, _ = run_performance_test("MV SYNC Refresh (wait for completion)", sync_refresh, iterations=5)
```

---

## Cell 6: Test Materialized View - Query Only

```python
print("Testing Materialized View - Query Performance...\n")

# Ensure view is refreshed first
print("Refreshing view once...")
spark.sql("REFRESH MATERIALIZED VIEW materialized_view")
while True:
    try:
        spark.sql("SELECT 1 FROM materialized_view LIMIT 1").collect()
        break
    except:
        time.sleep(0.5)
print("✓ View ready\n")

# Test query performance (no refresh)
def query_materialized():
    return spark.sql("SELECT * FROM materialized_view").collect()

mv_query_time, mv_count = run_performance_test("MV Query Only", query_materialized, iterations=5)
```

---

## Cell 7: Compare Results

```python
print("="*60)
print("📊 PERFORMANCE COMPARISON")
print("="*60)
print(f"Standard View Query:             {std_time:.3f}s  ({std_count:,} records)")
print(f"MV ASYNC Refresh (trigger):      {async_time:.3f}s")
print(f"MV SYNC Refresh (full):          {sync_time:.3f}s")
print(f"MV Query Only:                   {mv_query_time:.3f}s  ({mv_count:,} records)")
print("="*60)
print(f"\nTime Differences:")
print(f"  Standard View vs MV Query:     {std_time - mv_query_time:.3f}s")
print(f"  SYNC vs ASYNC trigger:         {sync_time - async_time:.3f}s")
print("="*60)
```

---

## 📊 What This Tests

| Test | What Happens |
|------|--------------|
| **Standard View Query** | Queries existing standard view |
| **MV ASYNC Refresh** | Triggers refresh, returns immediately |
| **MV SYNC Refresh** | Triggers refresh, waits for completion |
| **MV Query Only** | Queries materialized view (no refresh) |

---

## ⚙️ Adjust Settings

```python
# Change iterations for more accurate results
iterations=5   # Default
iterations=10  # More accurate
```

---

**7 cells total - Copy and run in order! 🚀**
