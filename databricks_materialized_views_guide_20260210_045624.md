# Databricks Materialized Views - Ready to Run Notebook Guide

---
**📅 Created:** February 10, 2026 at 04:56:24 UTC  
**📝 Version:** 1.0  
**👤 For:** Java Developers New to Databricks  
**🏷️ Topics:** Materialized Views, ASYNC/SYNC Refresh, Explode Function  

---

## How to Use This Guide
Copy and paste each code block into a **new cell** in your Databricks notebook. Run cells in order (top to bottom).

---

## 📚 PART 1: SETUP - Create Test Data

Run these cells first to create sample tables.

### Cell 1: Create Sample Sales Table

```python
# Create a sample sales table for testing
# No imports needed - spark is already available in Databricks

spark.sql("""
    CREATE OR REPLACE TABLE sales AS
    SELECT 
        cast(rand() * 10 as int) as product_id,
        rand() * 100 as amount,
        current_timestamp() as sale_date
    FROM range(1000)
""")

print("✓ Sales table created with 1000 rows")
spark.sql("SELECT * FROM sales LIMIT 5").show()
```

### Cell 2: Create Materialized View

```python
# Create a materialized view that aggregates sales data

spark.sql("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS sales_summary AS
    SELECT 
        product_id,
        COUNT(*) as total_orders,
        SUM(amount) as total_sales,
        AVG(amount) as avg_sale
    FROM sales
    GROUP BY product_id
""")

print("✓ Materialized view 'sales_summary' created")
```

---

## 🔵 PART 2: ASYNC REFRESH (Fire and Forget)

### Cell 3: Simple ASYNC Refresh - Python

```python
# ASYNC: Refresh starts and returns immediately
# Your code continues while refresh runs in background

spark.sql("REFRESH MATERIALIZED VIEW sales_summary")
print("✓ Refresh started in background")
print("I can continue doing other work!")

# Note: If you try to query now, it might fail if refresh is still running
```

### Cell 4: Simple ASYNC Refresh - Scala

```scala
// Switch to Scala by adding %scala at the top of the cell
%scala

// ASYNC: Refresh starts and returns immediately
spark.sql("REFRESH MATERIALIZED VIEW sales_summary")
println("✓ Refresh started in background")
println("I can continue doing other work!")
```

---

## 🟢 PART 3: SYNC REFRESH (Wait Until Done)

### Cell 5: Simple SYNC Refresh - Python

```python
# Import time module for sleep function
import time

# SYNC: Wait for refresh to complete before continuing
view_name = "sales_summary"

# Start the refresh
spark.sql(f"REFRESH MATERIALIZED VIEW {view_name}")
print("⏳ Refresh started, waiting for completion...")

# Keep checking until refresh is done
completed = False
attempts = 0

while not completed:
    try:
        # Try to query the view - if it works, refresh is done
        spark.sql(f"SELECT 1 FROM {view_name} LIMIT 1").collect()
        completed = True
        print("✓ Refresh completed!")
    except Exception as e:
        # Still refreshing, wait and try again
        attempts += 1
        print(f"  Attempt {attempts}: Still refreshing...")
        time.sleep(3)  # Wait 3 seconds before trying again

print("Now I can safely query the view!")
```

### Cell 6: Simple SYNC Refresh - Scala

```scala
%scala

// Import Thread for sleep function
import Thread.sleep

// SYNC: Wait for refresh to complete before continuing
val viewName = "sales_summary"

// Start the refresh
spark.sql(s"REFRESH MATERIALIZED VIEW $viewName")
println("⏳ Refresh started, waiting for completion...")

// Keep checking until refresh is done
var completed = false
var attempts = 0

while (!completed) {
  try {
    // Try to query the view - if it works, refresh is done
    spark.sql(s"SELECT 1 FROM $viewName LIMIT 1").collect()
    completed = true
    println("✓ Refresh completed!")
  } catch {
    case e: Exception =>
      // Still refreshing, wait and try again
      attempts += 1
      println(s"  Attempt $attempts: Still refreshing...")
      sleep(3000)  // Wait 3 seconds
  }
}

println("Now I can safely query the view!")
```

---

## 🎯 PART 4: PRODUCTION-READY FUNCTIONS

### Cell 7: Reusable SYNC Function - Python

```python
# Import required module
import time

def refresh_and_wait(view_name, timeout_seconds=300):
    """
    Refresh a materialized view and wait until it's done.
    
    Args:
        view_name: Name of the view to refresh
        timeout_seconds: Max time to wait (default 300 = 5 minutes)
    """
    # Start refresh
    spark.sql(f"REFRESH MATERIALIZED VIEW {view_name}")
    print(f"⏳ Refreshing {view_name}...")
    
    start_time = time.time()
    attempts = 0
    
    # Keep trying until it works or we timeout
    while time.time() - start_time < timeout_seconds:
        try:
            spark.sql(f"SELECT 1 FROM {view_name} LIMIT 1").collect()
            elapsed = time.time() - start_time
            print(f"✓ Refresh completed in {elapsed:.1f} seconds (after {attempts} attempts)")
            return True
        except Exception:
            attempts += 1
            if attempts % 10 == 0:  # Print every 10 attempts
                print(f"  Still waiting... ({attempts} attempts)")
            time.sleep(3)
    
    print(f"❌ Timeout after {timeout_seconds} seconds")
    return False

# HOW TO USE THIS FUNCTION:
# refresh_and_wait("sales_summary")
# refresh_and_wait("sales_summary", timeout_seconds=600)
```

### Cell 8: Test the Function - Python

```python
# Use the function we just created
result = refresh_and_wait("sales_summary", timeout_seconds=60)

if result:
    print("\nQuerying the refreshed view:")
    spark.sql("SELECT * FROM sales_summary ORDER BY total_sales DESC").show(5)
```

### Cell 9: Reusable SYNC Function - Scala

```scala
%scala

// Import required classes
import Thread.sleep
import scala.util.{Try, Success, Failure}

/**
 * Refresh a materialized view and wait until it's done.
 */
def refreshAndWait(viewName: String, timeoutSeconds: Int = 300): Boolean = {
  // Start refresh
  spark.sql(s"REFRESH MATERIALIZED VIEW $viewName")
  println(s"⏳ Refreshing $viewName...")
  
  val startTime = System.currentTimeMillis()
  var attempts = 0
  
  // Keep trying until it works or we timeout
  while (System.currentTimeMillis() - startTime < timeoutSeconds * 1000) {
    Try {
      spark.sql(s"SELECT 1 FROM $viewName LIMIT 1").collect()
    } match {
      case Success(_) =>
        val elapsed = (System.currentTimeMillis() - startTime) / 1000.0
        println(f"✓ Refresh completed in $elapsed%.1f seconds (after $attempts attempts)")
        return true
      case Failure(_) =>
        attempts += 1
        if (attempts % 10 == 0) {  // Print every 10 attempts
          println(s"  Still waiting... ($attempts attempts)")
        }
        sleep(3000)
    }
  }
  
  println(s"❌ Timeout after $timeoutSeconds seconds")
  false
}

// HOW TO USE THIS FUNCTION:
// refreshAndWait("sales_summary")
// refreshAndWait("sales_summary", 600)
```

### Cell 10: Test the Function - Scala

```scala
%scala

// Use the function we just created
val result = refreshAndWait("sales_summary", 60)

if (result) {
  println("\nQuerying the refreshed view:")
  spark.sql("SELECT * FROM sales_summary ORDER BY total_sales DESC").show(5)
}
```





---

## 💥 PART 5: EXPLODE - Flatten Array Data

### Cell 11: Understanding Explode - Simple Example (Python)

```python
# No imports needed - all Spark functions are available

# Create sample data with arrays
data = [
    (123, ["red", "blue", "green"]),
    (456, ["black", "white"])
]

# Convert to DataFrame
df = spark.createDataFrame(data, ["productId", "colors"])

print("BEFORE EXPLODE:")
df.show(truncate=False)

print("\nAFTER EXPLODE:")
# Import explode function
from pyspark.sql.functions import explode, col

# Explode the array column
exploded_df = df.select(
    col("productId"),
    explode(col("colors")).alias("color")
)

exploded_df.show()
```

### Cell 12: Understanding Explode - Simple Example (Scala)

```scala
%scala

// No special imports needed - all Spark functions are available
import org.apache.spark.sql.functions.{explode, col}

// Create sample data with arrays
val data = Seq(
  (123, Array("red", "blue", "green")),
  (456, Array("black", "white"))
)

// Convert to DataFrame
val df = data.toDF("productId", "colors")

println("BEFORE EXPLODE:")
df.show(truncate = false)

println("\nAFTER EXPLODE:")
// Explode the array column
val explodedDf = df.select(
  col("productId"),
  explode(col("colors")).as("color")
)

explodedDf.show()
```

---

## 💥 PART 6: EXPLODE - Real World Example

### Cell 13: Create Test Data with Nested Arrays (Python)

```python
# Create a table similar to your real data structure

spark.sql("""
    CREATE OR REPLACE TABLE instrument AS
    SELECT
        '2024-01-01' as __cob_date,
        '2024-01-01T00:00:00' as __START_AT,
        '9999-12-31T23:59:59' as __END_AT,
        12345 as __txn_id_long,
        'partition_1' as __slice,
        array(
            struct('ABC' as instrumentId, false as isAssetExpired, 'A' as statusCode, '123' as assetId),
            struct('DEF' as instrumentId, true as isAssetExpired, 'I' as statusCode, '456' as assetId),
            struct('GHI' as instrumentId, false as isAssetExpired, 'A' as statusCode, '789' as assetId)
        ) as alternateIdentifiers
""")

print("✓ Test instrument table created")
spark.sql("SELECT * FROM instrument").show(truncate=False)
```

### Cell 14: Explode Query with Comments (Python)

```python
# Import explode function
from pyspark.sql.functions import explode

# Query to flatten the alternateIdentifiers array
result = spark.sql("""
    -- ========================================
    -- OUTER SELECT: Extract individual fields from exploded array
    -- ========================================
    SELECT
        -- Extract fields from the exploded alternateIdentifiers struct
        alternateIdentifiers.instrumentId AS instrumentId,
        alternateIdentifiers.isAssetExpired AS isAssetExpired,
        alternateIdentifiers.statusCode AS statusCode,
        alternateIdentifiers.assetId AS assetId,
        
        -- Metadata columns from the parent instrument table
        __cob_date,        -- Close of Business date
        __START_AT,        -- Valid from timestamp
        __END_AT,          -- Valid to timestamp
        __txn_id_long,     -- Transaction ID
        __slice            -- Partition identifier
        
    FROM
        (
            -- ========================================
            -- INNER SELECT: Explode the array into multiple rows
            -- ========================================
            SELECT
                __cob_date,
                __START_AT,
                __END_AT,
                __txn_id_long,
                __slice,
                
                -- EXPLODE: Convert array of 3 elements into 3 rows
                -- Before: 1 row with array of 3 items
                -- After: 3 rows, one for each array item
                explode(alternateIdentifiers) AS alternateIdentifiers
                
            FROM instrument
        )
""")

print("RESULT - Each array element is now a separate row:")
result.show(truncate=False)

print(f"\nOriginal table had 1 row")
print(f"After explode we have {result.count()} rows")
```

### Cell 15: Explode Query with Comments (Scala)

```scala
%scala

// Import explode function
import org.apache.spark.sql.functions.explode

// Query to flatten the alternateIdentifiers array
val result = spark.sql("""
    -- ========================================
    -- OUTER SELECT: Extract individual fields from exploded array
    -- ========================================
    SELECT
        -- Extract fields from the exploded alternateIdentifiers struct
        alternateIdentifiers.instrumentId AS instrumentId,
        alternateIdentifiers.isAssetExpired AS isAssetExpired,
        alternateIdentifiers.statusCode AS statusCode,
        alternateIdentifiers.assetId AS assetId,
        
        -- Metadata columns from the parent instrument table
        __cob_date,        -- Close of Business date
        __START_AT,        -- Valid from timestamp
        __END_AT,          -- Valid to timestamp
        __txn_id_long,     -- Transaction ID
        __slice            -- Partition identifier
        
    FROM
        (
            -- ========================================
            -- INNER SELECT: Explode the array into multiple rows
            -- ========================================
            SELECT
                __cob_date,
                __START_AT,
                __END_AT,
                __txn_id_long,
                __slice,
                
                -- EXPLODE: Convert array of 3 elements into 3 rows
                -- Before: 1 row with array of 3 items
                -- After: 3 rows, one for each array item
                explode(alternateIdentifiers) AS alternateIdentifiers
                
            FROM instrument
        )
""")

println("RESULT - Each array element is now a separate row:")
result.show(truncate = false)

println(s"\nOriginal table had 1 row")
println(s"After explode we have ${result.count()} rows")
```

### Cell 16: Alternative - Using DataFrame API (Python)

```python
# Same explode operation using DataFrame API instead of SQL
from pyspark.sql.functions import explode, col

# Read the instrument table
df = spark.table("instrument")

# Explode and select in one go
result_df = df.select(
    # Select metadata columns
    col("__cob_date"),
    col("__START_AT"),
    col("__END_AT"),
    col("__txn_id_long"),
    col("__slice"),
    # Explode the array
    explode(col("alternateIdentifiers")).alias("alternateIdentifiers")
).select(
    # Extract fields from the exploded struct
    col("alternateIdentifiers.instrumentId").alias("instrumentId"),
    col("alternateIdentifiers.isAssetExpired").alias("isAssetExpired"),
    col("alternateIdentifiers.statusCode").alias("statusCode"),
    col("alternateIdentifiers.assetId").alias("assetId"),
    col("__cob_date"),
    col("__START_AT"),
    col("__END_AT"),
    col("__txn_id_long"),
    col("__slice")
)

print("Using DataFrame API:")
result_df.show(truncate=False)
```

### Cell 17: Alternative - Using DataFrame API (Scala)

```scala
%scala

// Same explode operation using DataFrame API instead of SQL
import org.apache.spark.sql.functions.{explode, col}

// Read the instrument table
val df = spark.table("instrument")

// Explode and select in one go
val resultDf = df.select(
    // Select metadata columns
    col("__cob_date"),
    col("__START_AT"),
    col("__END_AT"),
    col("__txn_id_long"),
    col("__slice"),
    // Explode the array
    explode(col("alternateIdentifiers")).as("alternateIdentifiers")
  ).select(
    // Extract fields from the exploded struct
    col("alternateIdentifiers.instrumentId").as("instrumentId"),
    col("alternateIdentifiers.isAssetExpired").as("isAssetExpired"),
    col("alternateIdentifiers.statusCode").as("statusCode"),
    col("alternateIdentifiers.assetId").as("assetId"),
    col("__cob_date"),
    col("__START_AT"),
    col("__END_AT"),
    col("__txn_id_long"),
    col("__slice")
  )

println("Using DataFrame API:")
resultDf.show(truncate = false)
```

---

## 💥 PART 7: EXPLODE - Your Original Query Explained

### Cell 18: Your Original Query - Fully Commented

```sql
-- This is your original query from the image
-- Copy this into a SQL cell or run with spark.sql()

-- ========================================
-- WHAT THIS QUERY DOES:
-- Takes a table with nested array data and "flattens" it
-- Each element in the alternateIdentifiers array becomes its own row
-- ========================================

SELECT
    -- ========================================
    -- EXTRACT FIELDS from the exploded struct
    -- After explode, alternateIdentifiers is a single struct (not an array)
    -- We can access its fields using dot notation
    -- ========================================
    alternateIdentifiers.instrumentId AS instrumentId,
    alternateIdentifiers.isAssetExpired AS isAssetExpired,
    alternateIdentifiers.statusCode AS statusCode,
    alternateIdentifiers.assetId AS assetId,
    alternateIdentifiers.assetIdType AS assetIdType,
    alternateIdentifiers.sourceId AS sourceId,
    alternateIdentifiers.rdrDerivedKey AS rdrDerivedKey,
    alternateIdentifiers.cerdCorpIdentifier AS cerdCorpIdentifier,
    alternateIdentifiers.sourceSystemName AS sourceSystemName,
    
    -- ========================================
    -- METADATA COLUMNS from parent table
    -- These columns are repeated for each exploded row
    -- Typical in Delta Lake CDC or SCD Type 2 tables
    -- ========================================
    __cob_date,        -- Close of Business date (when data is effective)
    __START_AT,        -- Start of validity period (SCD Type 2)
    __END_AT,          -- End of validity period (SCD Type 2)
    __txn_id_long,     -- Transaction ID for change tracking
    __slice            -- Partition or slice identifier

FROM
    (
        -- ========================================
        -- SUBQUERY: This is where the magic happens
        -- ========================================
        SELECT
            -- Copy metadata columns from original table
            instrument.__cob_date,
            instrument.__START_AT,
            instrument.__END_AT,
            instrument.__txn_id_long,
            instrument.__slice,
            
            -- ========================================
            -- EXPLODE FUNCTION: The key transformation
            -- ========================================
            -- BEFORE explode:
            --   1 row with alternateIdentifiers = [item1, item2, item3]
            -- AFTER explode:
            --   3 rows: row1 has item1, row2 has item2, row3 has item3
            --
            -- Each item is a struct with fields like instrumentId, statusCode, etc.
            -- ========================================
            explode(instrument.alternateIdentifiers) AS alternateIdentifiers
            
        FROM
            -- Source table from Delta Lake catalog
            -- Schema: database.catalog.table
            `19519_ctg_dev`.refdata.instrument AS instrument
    )

-- ========================================
-- VISUAL EXAMPLE OF TRANSFORMATION:
-- ========================================
-- BEFORE (1 row):
-- +----------+----------------------------+
-- | __cob_date | alternateIdentifiers      |
-- +----------+----------------------------+
-- | 2024-01-01 | [{ABC,A,123}, {DEF,I,456}]|
-- +----------+----------------------------+
--
-- AFTER (2 rows):
-- +----------+-------------+------------+---------+
-- | __cob_date | instrumentId| statusCode | assetId |
-- +----------+-------------+------------+---------+
-- | 2024-01-01 | ABC         | A          | 123     |
-- | 2024-01-01 | DEF         | I          | 456     |
-- +----------+-------------+------------+---------+
```

---

## 📚 Quick Reference Guide

### When to Use What?

| Scenario | Use This | Why |
|----------|----------|-----|
| Just need to trigger a refresh | ASYNC | Fastest, don't wait |
| Need fresh data before next step | SYNC | Wait for completion |
| Have array/nested data | EXPLODE | Flatten to individual rows |
| Creating report from nested data | EXPLODE + materialized view | Best performance |

### Key Imports You Need

**Python:**
```python
import time  # For sleep function in SYNC refresh
from pyspark.sql.functions import explode, col  # For explode operations
```

**Scala:**
```scala
import Thread.sleep  # For sleep in SYNC refresh
import scala.util.{Try, Success, Failure}  # For error handling
import org.apache.spark.sql.functions.{explode, col}  # For explode operations
```

### Common Patterns

**Pattern 1: Refresh before querying**
```python
# Wrong - might fail if refresh not done
spark.sql("REFRESH MATERIALIZED VIEW my_view")
result = spark.sql("SELECT * FROM my_view")  # ❌ Might fail

# Right - wait for refresh
refresh_and_wait("my_view")
result = spark.sql("SELECT * FROM my_view")  # ✅ Always works
```

**Pattern 2: Create materialized view from exploded data**
```sql
CREATE MATERIALIZED VIEW flattened_instruments AS
SELECT
    alternateIdentifiers.instrumentId,
    alternateIdentifiers.statusCode,
    __cob_date
FROM (
    SELECT explode(alternateIdentifiers) as alternateIdentifiers, __cob_date
    FROM instrument
)
```

---

## 🎓 Learning Tips for Java Developers

Since you're coming from Java, here are some helpful comparisons:

| Java | Python | Scala |
|------|--------|-------|
| `Thread.sleep(5000)` | `time.sleep(5)` | `Thread.sleep(5000)` |
| `try/catch` | `try/except` | `try/catch` or `Try/Success/Failure` |
| `String name = "x"` | `name = "x"` | `val name = "x"` |
| `while (condition) {}` | `while condition:` | `while (condition) {}` |
| `System.out.println()` | `print()` | `println()` |

**Key Difference:** In Databricks notebooks, `spark` is already created for you. In regular Java/Scala, you'd create a SparkSession first.

---

## ❓ Common Questions

**Q: Why doesn't REFRESH wait for completion?**  
A: Databricks designed it to be async by default for better performance. You add the waiting logic yourself.

**Q: Will my query hang waiting for refresh?**  
A: No! Queries fail immediately (fail-fast) if the view is being refreshed. No blocking/hanging.

**Q: Can I use explode on non-array columns?**  
A: No, explode only works on arrays. You'll get an error if you try on a string or number.

**Q: What if the array is empty?**  
A: `explode()` will produce zero rows. Use `explode_outer()` to keep the row with null value.

**Q: Do I need to import spark?**  
A: No! In Databricks notebooks, `spark` is already available. Just use it.

---

## 🚀 Next Steps

1. **Copy Cell 1-2** to create test tables
2. **Try Cell 3-4** to understand async vs sync
3. **Run Cell 7-8** to use the reusable function
4. **Explore Cell 11-17** to learn explode
5. **Study Cell 18** to understand your real query

---

## 💡 Pro Tips

1. **Always use timeout** in sync refresh to avoid infinite loops
2. **Check view is accessible** before querying after async refresh
3. **Use explode_outer()** if you need to keep rows with empty arrays
4. **Create materialized views** from expensive explode queries
5. **Add comments** to your queries - future you will thank you!

---

**Happy Coding! 🎉**

Remember: 
- Start simple (use the basic examples)
- Run one cell at a time
- Read the comments in the code
- Experiment and learn by doing!
