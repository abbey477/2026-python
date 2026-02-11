# Performance Test: Standard View vs Materialized View
**Python-only - Query Performance Comparison**

**Prerequisites:** 
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
    Reusable function to test query performance
    - Disables cache before each run
    - Runs multiple iterations
    - Returns average time and record count
    """
    times = []
    record_count = None
    
    for i in range(iterations):
        # Disable cache for fair comparison
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
print("TEST 1: STANDARD VIEW - QUERY PERFORMANCE")
print("="*60)

def query_standard():
    return spark.sql("SELECT * FROM standard_view").collect()

std_time, std_count = run_performance_test("Standard View", query_standard, iterations=5)

print(f"📊 Result: {std_time:.3f}s average, {std_count:,} records")
print("="*60)
print()
```

---

## Cell 4: Test Materialized View - ASYNC

```python
print("="*60)
print("TEST 2: MATERIALIZED VIEW - ASYNC (QUERY PERFORMANCE)")
print("="*60)
print("(Assuming materialized view already refreshed by pipeline)\n")

# Query materialized view (no refresh, pipeline handles it)
def query_mv_async():
    return spark.sql("SELECT * FROM materialized_view").collect()

mv_async_time, mv_async_count = run_performance_test("MV Query (async)", query_mv_async, iterations=5)

print(f"📊 Result: {mv_async_time:.3f}s average, {mv_async_count:,} records")
print("="*60)
print()
```

---

## Cell 5: Test Materialized View - SYNC

```python
print("="*60)
print("TEST 3: MATERIALIZED VIEW - SYNC (QUERY PERFORMANCE)")
print("="*60)
print("(Assuming materialized view already refreshed by pipeline)\n")

# Query materialized view (no refresh, pipeline handles it)
def query_mv_sync():
    return spark.sql("SELECT * FROM materialized_view").collect()

mv_sync_time, mv_sync_count = run_performance_test("MV Query (sync)", query_mv_sync, iterations=5)

print(f"📊 Result: {mv_sync_time:.3f}s average, {mv_sync_count:,} records")
print("="*60)
```

---

## 📊 What This Tests

| Test | What It Measures |
|------|------------------|
| **Standard View** | Query performance (recomputes every time) |
| **MV ASYNC** | Query performance on materialized view |
| **MV SYNC** | Query performance on materialized view |

**Note:** 
- NO refresh commands are triggered
- Pipeline has already refreshed the materialized view
- Only query performance is measured
- Cache is disabled for fair comparison

---

## ⚙️ Adjust Settings

```python
# Change iterations
iterations=5   # Default
iterations=10  # More accurate
```

---

**5 cells total - Each prints its own results! 🚀**
