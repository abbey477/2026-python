# Databricks Nested Arrays and Structs - Complete Guide

## Table of Contents
1. [Struct vs Array Overview](#struct-vs-array-overview)
2. [Pure Struct Examples](#pure-struct-examples)
3. [Array Examples](#array-examples)
4. [Deep Nesting Example](#deep-nesting-example)
5. [Key Concepts](#key-concepts)

---

## Struct vs Array Overview

| Feature | STRUCT | ARRAY |
|---------|--------|-------|
| What it is | Single object with named fields | Collection of multiple items |
| Like in Java | POJO (one object) | List/ArrayList (multiple objects) |
| Access method | Dot notation: `address.street` | Must explode first, then access |
| Creates new rows? | No | Yes (when exploded) |
| Example | `{street: "Main", city: "NYC"}` | `["apple", "banana", "orange"]` |

---

## Pure Struct Examples

### Example 1: Simple Struct (No Arrays)

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "address": {                    // This is a STRUCT
    "street": "123 Main St",
    "city": "New York",
    "zip": "10001"
  }
}
```

**Schema:**
```
root
 |-- customer_id: integer
 |-- name: string
 |-- address: struct              // STRUCT (like a POJO)
 |    |-- street: string
 |    |-- city: string
 |    |-- zip: string
```

**Query (No explode needed!):**
```sql
SELECT 
  customer_id,
  name,
  address.street,      -- Access struct fields with dot notation
  address.city,
  address.zip
FROM my_table
```

**Result:**
```
+-------------+-------+--------------+----------+-------+
| customer_id | name  | street       | city     | zip   |
+-------------+-------+--------------+----------+-------+
| 1           | Alice | 123 Main St  | New York | 10001 |
+-------------+-------+--------------+----------+-------+
```

**Key Point:** Struct doesn't need `explode()` - just use dot notation!

---

### Example 2: Nested Structs (No Arrays)

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "address": {                    // STRUCT level 1
    "street": "123 Main St",
    "location": {                 // STRUCT level 2 (nested inside address)
      "lat": 40.7128,
      "lng": -74.0060
    }
  }
}
```

**Schema:**
```
root
 |-- customer_id: integer
 |-- name: string
 |-- address: struct
 |    |-- street: string
 |    |-- location: struct        // Nested STRUCT
 |    |    |-- lat: double
 |    |    |-- lng: double
```

**Query:**
```sql
SELECT 
  customer_id,
  name,
  address.street,
  address.location.lat,      -- Access nested struct with multiple dots
  address.location.lng
FROM my_table
```

**Result:**
```
+-------------+-------+--------------+----------+-----------+
| customer_id | name  | street       | lat      | lng       |
+-------------+-------+--------------+----------+-----------+
| 1           | Alice | 123 Main St  | 40.7128  | -74.0060  |
+-------------+-------+--------------+----------+-----------+
```

---

### Example 3: Mix of Struct and Array

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "contact": {                    // STRUCT
    "email": "alice@example.com",
    "phones": ["555-1234", "555-5678"]  // ARRAY inside STRUCT
  }
}
```

**Schema:**
```
root
 |-- customer_id: integer
 |-- name: string
 |-- contact: struct              // STRUCT
 |    |-- email: string
 |    |-- phones: array           // ARRAY inside the struct
 |    |    |-- element: string
```

**Query:**
```sql
SELECT 
  customer_id,
  name,
  contact.email,          -- Access struct field (no explode)
  phone                   -- Access exploded array
FROM my_table
LATERAL VIEW explode(contact.phones) AS phone  -- Only explode the array
```

**Result:**
```
+-------------+-------+--------------------+----------+
| customer_id | name  | email              | phone    |
+-------------+-------+--------------------+----------+
| 1           | Alice | alice@example.com  | 555-1234 |
| 1           | Alice | alice@example.com  | 555-5678 |
+-------------+-------+--------------------+----------+
```

---

## Array Examples

### Example 4: Simple Array

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "favorite_colors": ["blue", "green", "red"]  // Simple ARRAY
}
```

**Schema:**
```
root
 |-- customer_id: integer
 |-- name: string
 |-- favorite_colors: array
 |    |-- element: string
```

**Query:**
```sql
SELECT 
  customer_id,
  name,
  color
FROM my_table
LATERAL VIEW explode(favorite_colors) AS color
```

**Result:**
```
+-------------+-------+-------+
| customer_id | name  | color |
+-------------+-------+-------+
| 1           | Alice | blue  |
| 1           | Alice | green |
| 1           | Alice | red   |
+-------------+-------+-------+
```

---

### Example 5: Array of Structs

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "orders": [                     // ARRAY of STRUCT
    {
      "order_id": "A1",
      "amount": 100.50
    },
    {
      "order_id": "A2",
      "amount": 250.75
    }
  ]
}
```

**Schema:**
```
root
 |-- customer_id: integer
 |-- name: string
 |-- orders: array                // ARRAY
 |    |-- element: struct         // Each element is a STRUCT
 |    |    |-- order_id: string
 |    |    |-- amount: double
```

**Query:**
```sql
SELECT 
  customer_id,
  name,
  order.order_id,        -- Access struct fields after exploding
  order.amount
FROM my_table
LATERAL VIEW explode(orders) AS order
```

**Result:**
```
+-------------+-------+----------+--------+
| customer_id | name  | order_id | amount |
+-------------+-------+----------+--------+
| 1           | Alice | A1       | 100.50 |
| 1           | Alice | A2       | 250.75 |
+-------------+-------+----------+--------+
```

---

## Deep Nesting Example

### Example 6: Complex Nested Structure (5 Levels)

**Sample Data:**
```json
{
  "customer_id": 1,
  "name": "Alice",
  "accounts": [                              // Level 2: ARRAY
    {
      "account_id": "ACC001",                // STRUCT
      "transactions": [                      // Level 3: ARRAY
        {
          "transaction_id": "TXN001",        // STRUCT
          "line_items": [                    // Level 4: ARRAY
            {
              "product": "Laptop",           // STRUCT
              "tags": ["electronics", "computer"]  // Level 5: ARRAY
            },
            {
              "product": "Mouse",
              "tags": ["electronics", "accessory"]
            }
          ]
        },
        {
          "transaction_id": "TXN002",
          "line_items": [
            {
              "product": "Keyboard",
              "tags": ["electronics"]
            }
          ]
        }
      ]
    }
  ]
}
```

**Schema:**
```
root
 |-- customer_id: integer                     // Level 1: Root level
 |-- name: string                             // Level 1: Root level
 |-- accounts: array                          // Level 2: Array of account objects
 |    |-- element: struct                     // Each account is a struct
 |    |    |-- account_id: string
 |    |    |-- transactions: array            // Level 3: Array of transactions
 |    |    |    |-- element: struct           // Each transaction is a struct
 |    |    |    |    |-- transaction_id: string
 |    |    |    |    |-- line_items: array    // Level 4: Array of line items
 |    |    |    |    |    |-- element: struct // Each line item is a struct
 |    |    |    |    |    |    |-- product: string
 |    |    |    |    |    |    |-- tags: array // Level 5: Array of tags (strings)
 |    |    |    |    |    |    |    |-- element: string
```

**Flattening Query (SQL):**
```sql
-- This query explodes all nested arrays to create a flat result
SELECT 
  customer_id,                    -- From root level (STRUCT field)
  name,                           -- From root level (STRUCT field)
  account.account_id,             -- From exploded accounts array (STRUCT field)
  txn.transaction_id,             -- From exploded transactions array (STRUCT field)
  item.product,                   -- From exploded line_items array (STRUCT field)
  tag                             -- From exploded tags array (simple string)
FROM my_table
LATERAL VIEW explode(accounts) AS account           -- Explode Level 2: ARRAY
LATERAL VIEW explode(account.transactions) AS txn   -- Explode Level 3: ARRAY
LATERAL VIEW explode(txn.line_items) AS item        -- Explode Level 4: ARRAY
LATERAL VIEW explode(item.tags) AS tag              -- Explode Level 5: ARRAY
```

**Expected Flattened Result:**
```
+-------------+-------+------------+----------------+---------+-------------+
| customer_id | name  | account_id | transaction_id | product | tag         |
+-------------+-------+------------+----------------+---------+-------------+
| 1           | Alice | ACC001     | TXN001         | Laptop  | electronics |
| 1           | Alice | ACC001     | TXN001         | Laptop  | computer    |
| 1           | Alice | ACC001     | TXN001         | Mouse   | electronics |
| 1           | Alice | ACC001     | TXN001         | Mouse   | accessory   |
| 1           | Alice | ACC001     | TXN002         | Keyboard| electronics |
+-------------+-------+------------+----------------+---------+-------------+
```

**Analysis:**
- **Original rows**: 1 customer record
- **Final rows**: 5 flattened records
- **Row explosion**: Each `explode()` multiplies the number of rows
  - 1 customer → 1 account → 2 transactions → 3 line items → 5 tags total

---

## Key Concepts

### When to Use STRUCT vs ARRAY

**Use STRUCT when:**
- You have a single object with multiple named fields
- Example: address, contact info, coordinates
- No need to explode - just use dot notation

**Use ARRAY when:**
- You have multiple items of the same type
- Example: list of phone numbers, list of orders, list of tags
- Need to explode to access individual items

**Common pattern: Array of Structs**
- Most real-world nested data uses this pattern
- Example: orders (array) where each order (struct) has order_id, amount, date

### Performance Considerations

- **Row explosion**: Each `explode()` multiplies the number of rows
- **Deep nesting**: Can cause significant data explosion (avoid if possible)
- **Best practice**: Flatten only the levels you actually need for your analysis
- **Memory**: Watch out for exploding large arrays - can exhaust memory

### Alternative: PySpark DataFrame Syntax

```python
# Same deep nesting query using PySpark DataFrame API
from pyspark.sql.functions import explode

df.select("customer_id", "name", explode("accounts").alias("account")) \
  .select("customer_id", "name", "account.account_id", 
          explode("account.transactions").alias("txn")) \
  .select("customer_id", "name", "account_id", "txn.transaction_id",
          explode("txn.line_items").alias("item")) \
  .select("customer_id", "name", "account_id", "transaction_id", "item.product",
          explode("item.tags").alias("tag"))
```

### Viewing Schema in Databricks

```python
# Best way to see nested structure
spark.table("my_table").printSchema()

# Or in SQL
DESCRIBE my_table

# To see specific nested column
DESCRIBE my_table accounts
```

### Summary Table

| Type | Access Method | Explode Needed? | Creates Rows? | Example |
|------|---------------|-----------------|---------------|---------|
| STRUCT | Dot notation | No | No | `address.street` |
| ARRAY | explode() | Yes | Yes | `explode(phones)` |
| Array of Structs | explode() + dot | Yes | Yes | `explode(orders)` then `order.order_id` |
| Nested Structs | Multiple dots | No | No | `address.location.lat` |

---

## Additional Resources

- **LATERAL VIEW vs explode()**: Use LATERAL VIEW in SQL, use .explode() in DataFrame API
- **struct vs POJO**: A struct is like a simplified Java POJO - just data fields without methods
- **Nesting depth**: No hard limit, but practical limit is 3-4 levels for performance and readability
- **NULL handling**: Use `explode_outer()` to preserve rows with null/empty arrays

---

*Document created: 2026-02-05 03:28:48*
