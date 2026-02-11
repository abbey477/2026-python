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
print("="*60)
print("TEST 1: STANDARD VIEW")
print("="*60)

# Test standard view (assumes 'standard_view' already exists)
def query_standard():
    return spark.sql("SELECT * FROM standard_view").collect()

std_time, std_count = run_performance_test("Standard View", query_standard, iterations=5)

print(f"📊 Result: {std_time:.3f}s average, {std_count:,} records")
print("="*60)
print()
```

---

## Cell 4: Test Materialized View - ASYNC Refresh

```python
print("="*60)
print("TEST 2: MATERIALIZED VIEW - ASYNC REFRESH")
print("="*60)

# Test ASYNC: Just trigger refresh, don't wait
def async_refresh():
    spark.sql("REFRESH MATERIALIZED VIEW materialized_view")
    # Returns immediately, doesn't wait
    return None  # No records returned

async_time, _ = run_performance_test("MV ASYNC Refresh (trigger only)", async_refresh, iterations=5)

print(f"📊 Result: {async_time:.3f}s average (trigger time only)")
print("="*60)
print()

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
print("="*60)
print("TEST 3: MATERIALIZED VIEW - SYNC REFRESH")
print("="*60)

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

print(f"📊 Result: {sync_time:.3f}s average (full refresh time)")
print("="*60)
print()
```

---

## Cell 6: Test Materialized View - Query Only (No Refresh)

```python
print("="*60)
print("TEST 4: MATERIALIZED VIEW - QUERY ONLY (NO REFRESH)")
print("="*60)
print("(Assuming materialized view is already refreshed)\n")

# Test query performance (no refresh)
def query_materialized():
    return spark.sql("SELECT * FROM materialized_view").collect()

mv_query_time, mv_count = run_performance_test("MV Query Only", query_materialized, iterations=5)

print(f"📊 Result: {mv_query_time:.3f}s average, {mv_count:,} records")
print("="*60)
print()
```

---

## Cell 7: Test Materialized View - Query Only (Without Previous Refresh)

```python
print("="*60)
print("TEST 5: MATERIALIZED VIEW - QUERY WITHOUT REFRESH")
print("="*60)
print("(Testing query performance without calling refresh)\n")

# Test query performance (assumes view was refreshed earlier, no new refresh)
def query_materialized_no_refresh():
    return spark.sql("SELECT * FROM materialized_view").collect()

mv_no_refresh_time, mv_no_refresh_count = run_performance_test("MV Query (no refresh called)", query_materialized_no_refresh, iterations=5)

print(f"📊 Result: {mv_no_refresh_time:.3f}s average, {mv_no_refresh_count:,} records")
print("="*60)
```

---

## 📊 What This Tests

| Test | What Happens |
|------|--------------|
| **Cell 3: Standard View** | Queries standard view |
| **Cell 4: MV ASYNC Refresh** | Triggers refresh, returns immediately |
| **Cell 5: MV SYNC Refresh** | Triggers refresh, waits for completion |
| **Cell 6: MV Query (after refresh)** | Queries MV after refresh completes |
| **Cell 7: MV Query (no refresh)** | Queries MV without calling refresh |

**Each cell prints its own results immediately.**

---

## ⚙️ Adjust Settings

```python
# Change iterations for more accurate results
iterations=5   # Default
iterations=10  # More accurate
```

---

**7 cells total - Each cell runs independently and prints results! 🚀**
