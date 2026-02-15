# Databricks View Performance Testing Guide

This guide provides PySpark code for testing view performance in Databricks, organized into notebook cells.

---

## Cell 1: Import and Function Definition

```python
import time
import statistics

def test_queries(query_set_name, queries_dict, num_runs=3):
    """
    Test multiple queries with minimal output
    
    Parameters:
    - query_set_name: name of the query set (e.g. "Client", "Product")
    - queries_dict: dictionary of {query_name: query_string}
    - num_runs: number of runs per query
    """
    results = []
    
    print(f"\n{'='*70}")
    print(f"Query Set: {query_set_name}")
    print(f"{'='*70}")
    
    for query_name, query in queries_dict.items():
        times = []
        
        for i in range(num_runs):
            spark.catalog.clearCache()
            start = time.time()
            count = spark.sql(query).count()
            times.append(time.time() - start)
        
        avg_time = statistics.mean(times)
        results.append({'name': query_name, 'avg': avg_time, 'count': count})
    
    # Print results
    print(f"{'Query':<40} {'Avg Time':>12} {'Count':>15}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<40} {r['avg']:>11.2f}s {r['count']:>14,}")
    
    return results
```

---

## Cell 2: Warm-up Function (Optional)

```python
def warm_up_with_view(warm_up_view, iterations=2):
    """
    Warm up cluster by querying a different view
    
    Parameters:
    - warm_up_view: name of the view to use for warm-up
    - iterations: number of warm-up runs (default: 2)
    """
    print(f"Warming up cluster using view: {warm_up_view}")
    for i in range(iterations):
        spark.sql(f"SELECT * FROM {warm_up_view}").count()
        print(f"  Warm-up iteration {i+1} complete")
    print("Warm-up done\n")

# Run warm-up (replace with your actual warm-up view)
warm_up_with_view("your_warmup_view", iterations=2)
```

**Alternative: Simple warm-up without a view**

```python
# Simple warm-up using dummy data
print("Warming up cluster...")
spark.range(10000000).count()
spark.range(10000000).count()
print("Warm-up done\n")
```

---

## Cell 3: Define Queries for Client View

```python
# Update the table name to match your actual client view
client_queries = {
    "SELECT *": """
        SELECT * 
        FROM 19519_ctg_dev.refdata_denorm_materialized.instrument_alternate_identifiers_test
    """,
    
    "COUNT(*)": """
        SELECT COUNT(*) 
        FROM 19519_ctg_dev.refdata_denorm_materialized.instrument_alternate_identifiers_test
    """,
    
    "GROUP BY": """
        SELECT instrument_type, COUNT(*) as count
        FROM 19519_ctg_dev.refdata_denorm_materialized.instrument_alternate_identifiers_test 
        GROUP BY instrument_type
    """,
    
    "COUNT DISTINCT": """
        SELECT COUNT(DISTINCT identifier) 
        FROM 19519_ctg_dev.refdata_denorm_materialized.instrument_alternate_identifiers_test
    """,
    
    "Multiple Aggregations": """
        SELECT 
            instrument_type,
            COUNT(*) as count,
            COUNT(DISTINCT identifier) as unique_ids
        FROM 19519_ctg_dev.refdata_denorm_materialized.instrument_alternate_identifiers_test
        GROUP BY instrument_type
    """
}
```

---

## Cell 4: Run Client Tests

```python
results_client = test_queries("Client", client_queries, num_runs=3)
```

**Expected Output:**
```
======================================================================
Query Set: Client
======================================================================
Query                                        Avg Time           Count
----------------------------------------------------------------------
SELECT *                                         5.23s         123,456
COUNT(*)                                         2.15s               1
GROUP BY                                         3.45s              15
COUNT DISTINCT                                   4.12s               1
Multiple Aggregations                            4.67s              15
```

---

## Cell 5: Define Queries for Product View

```python
# Update the table name to match your actual product view
product_queries = {
    "SELECT *": """
        SELECT * 
        FROM your_catalog.your_schema.product_view
    """,
    
    "COUNT(*)": """
        SELECT COUNT(*) 
        FROM your_catalog.your_schema.product_view
    """,
    
    "GROUP BY": """
        SELECT category, COUNT(*) as count
        FROM your_catalog.your_schema.product_view
        GROUP BY category
    """,
    
    "COUNT DISTINCT": """
        SELECT COUNT(DISTINCT product_id) 
        FROM your_catalog.your_schema.product_view
    """,
    
    "Complex Aggregation": """
        SELECT 
            category,
            COUNT(*) as total_products,
            SUM(price) as total_value,
            AVG(price) as avg_price
        FROM your_catalog.your_schema.product_view
        GROUP BY category
        ORDER BY total_value DESC
    """
}
```

---

## Cell 6: Run Product Tests

```python
results_product = test_queries("Product", product_queries, num_runs=3)
```

---

## Cell 7: Compare Standard vs Materialized View

```python
# Define queries for standard view
standard_view_queries = {
    "COUNT(*)": "SELECT COUNT(*) FROM your_catalog.your_schema.standard_view",
    
    "GROUP BY": """
        SELECT category, COUNT(*) 
        FROM your_catalog.your_schema.standard_view 
        GROUP BY category
    """,
    
    "COUNT DISTINCT": """
        SELECT COUNT(DISTINCT id) 
        FROM your_catalog.your_schema.standard_view
    """
}

# Define queries for materialized view
materialized_view_queries = {
    "COUNT(*)": "SELECT COUNT(*) FROM your_catalog.your_schema.materialized_view",
    
    "GROUP BY": """
        SELECT category, COUNT(*) 
        FROM your_catalog.your_schema.materialized_view 
        GROUP BY category
    """,
    
    "COUNT DISTINCT": """
        SELECT COUNT(DISTINCT id) 
        FROM your_catalog.your_schema.materialized_view
    """
}

# Run tests
results_standard = test_queries("Standard View", standard_view_queries, num_runs=3)
results_materialized = test_queries("Materialized View", materialized_view_queries, num_runs=3)
```

---

## Cell 8: Side-by-Side Comparison

```python
# Compare Standard vs Materialized
print("\n" + "="*80)
print("STANDARD vs MATERIALIZED VIEW COMPARISON")
print("="*80)
print(f"{'Query':<30} {'Standard':>15} {'Materialized':>15} {'Speedup':>12}")
print("-"*80)

for i, std_result in enumerate(results_standard):
    mat_result = results_materialized[i]
    speedup = std_result['avg'] / mat_result['avg']
    print(f"{std_result['name']:<30} {std_result['avg']:>14.2f}s {mat_result['avg']:>14.2f}s {speedup:>11.2f}x")

# Calculate average speedup
avg_speedup = statistics.mean([
    results_standard[i]['avg'] / results_materialized[i]['avg'] 
    for i in range(len(results_standard))
])

print("-"*80)
print(f"{'Average Speedup:':<30} {avg_speedup:>57.2f}x")
```

---

## Additional Helper Functions

### Cell 9: Analyze Execution Plan

```python
def analyze_view_plan(view_name):
    """
    Analyze the execution plan to identify performance issues
    """
    df = spark.sql(f"SELECT * FROM {view_name}")
    
    print("=" * 70)
    print(f"EXECUTION PLAN: {view_name}")
    print("=" * 70)
    df.explain(mode="formatted")

# Usage
analyze_view_plan("your_catalog.your_schema.your_view")
```

### Cell 10: Check View Statistics

```python
def check_view_statistics(view_name):
    """
    Check data size and partitioning
    """
    df = spark.sql(f"SELECT * FROM {view_name}")
    
    print("=" * 70)
    print(f"VIEW STATISTICS: {view_name}")
    print("=" * 70)
    
    # Record count
    count = df.count()
    print(f"Total records: {count:,}")
    
    # Number of partitions
    num_partitions = df.rdd.getNumPartitions()
    print(f"Number of partitions: {num_partitions}")
    print(f"Records per partition: {count / num_partitions:,.0f}")
    
    # Partition size distribution
    print("\nPartition size distribution:")
    partition_counts = df.rdd.glom().map(len).collect()
    print(f"  Min partition size: {min(partition_counts):,}")
    print(f"  Max partition size: {max(partition_counts):,}")
    print(f"  Avg partition size: {sum(partition_counts)/len(partition_counts):,.0f}")
    
    # Check for skew
    skew_ratio = max(partition_counts) / (sum(partition_counts)/len(partition_counts))
    print(f"\nSkew ratio: {skew_ratio:.2f}x")
    if skew_ratio > 3:
        print("  ⚠️  WARNING: Significant data skew detected!")
    
    return {
        'count': count,
        'partitions': num_partitions,
        'skew_ratio': skew_ratio
    }

# Usage
stats = check_view_statistics("your_catalog.your_schema.your_view")
```

---

## Performance Benchmarks

### What Makes a View Performant?

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| **Records/sec** | >1M | 100K-1M | <100K |
| **Skew ratio** | <2x | 2-3x | >3x |
| **Partitions** | 100-1000 | 10-100 or 1000-2000 | <10 or >2000 |
| **Query time** | <10s | 10-60s | >60s |

### Expected Speedup (Materialized vs Standard)

| Query Type | Expected Speedup |
|------------|-----------------|
| COUNT(*) | 10-100x faster |
| Simple GROUP BY | 5-50x faster |
| Complex aggregations | 10-100x faster |
| DISTINCT operations | 10-100x faster |
| Window functions | 10-50x faster |

---

## Tips for Best Results

1. **Always warm up the cluster first** before running performance tests
2. **Clear cache between runs** to measure actual I/O performance
3. **Run multiple iterations** (3-5) to get consistent averages
4. **Test different query patterns** - aggregations show the biggest differences
5. **Check execution plans** to identify bottlenecks
6. **Monitor data skew** - can cause significant performance issues

---

## Common Issues and Solutions

### Issue: First run is always slow
**Solution:** Use the warm-up function before running tests

### Issue: Results are inconsistent
**Solution:** Increase `num_runs` parameter and clear cache between runs

### Issue: All queries are slow
**Solution:** Check partition count and data skew using `check_view_statistics()`

### Issue: Materialized view not faster
**Solution:** Ensure you're testing the right views and clearing cache properly

---

## Example Full Workflow

```python
# 1. Warm up
warm_up_with_view("warmup_view")

# 2. Define queries
my_queries = {
    "COUNT(*)": "SELECT COUNT(*) FROM my_view",
    "GROUP BY": "SELECT category, COUNT(*) FROM my_view GROUP BY category"
}

# 3. Run tests
results = test_queries("My View", my_queries, num_runs=5)

# 4. Analyze if needed
check_view_statistics("my_view")
analyze_view_plan("my_view")
```

---

## Notes

- Replace all table/view names with your actual catalog.schema.table names
- Adjust `num_runs` based on how consistent you need the results (3-5 is typical)
- The warm-up step is optional but recommended for accurate results
- Clear cache between tests to measure true performance without caching effects

---

**Created:** February 2026  
**For:** Databricks Performance Testing
