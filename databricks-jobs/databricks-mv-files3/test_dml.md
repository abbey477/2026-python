# Test DML — INSERT / UPDATE / DELETE

**Table:** `your_catalog.your_schema.your_table` ← update this  
**Primary Key:** `__txn_id_long`  
**Test PK value used throughout:** `999999999999999999` — unique, will not collide with real data

---

## INSERT

```sql
INSERT INTO your_catalog.your_schema.your_table
  (__cob_date, _slice, __txn_id_long, __START_AT, __END_AT, _abexID, _runtimeID, addresses, alternateIdentifiers)
VALUES (
  CAST('2023-03-31' AS DATE),
  'COMMON',
  999999999999999999,
  CAST('2024-06-27T11:46:45.418+00:00' AS TIMESTAMP),
  NULL,
  '8',
  'PartyRule',
  ARRAY(
    NAMED_STRUCT(
      'eci',          '0250058075',
      'purposeCode',  'LEGAL',
      'addressLine1', '2331 WISTERIA ST',
      'addressLine2', CAST(NULL AS STRING),
      'addressLine3', CAST(NULL AS STRING),
      'addressLine4', CAST(NULL AS STRING)
    )
  ),
  ARRAY(
    NAMED_STRUCT(
      'branchCode',               '01',
      'eci',                      '0250058075',
      'alternateIdEffectiveDate', '2022-06-21T16:39:10.000Z',
      'identifierType',           'ECI',
      'status',                   'ACT',
      'rdDerivedKey',             'TEST_VALUE'
    )
  )
);
```

**Verify — expected: 1 row returned**

```sql
SELECT *
FROM your_catalog.your_schema.your_table
WHERE __txn_id_long = 999999999999999999;
```

---

## UPDATE

Updates `addressLine1` on the test record using the primary key.

```sql
UPDATE your_catalog.your_schema.your_table
SET addresses = ARRAY(
    NAMED_STRUCT(
      'eci',          '0250058075',
      'purposeCode',  'LEGAL',
      'addressLine1', '999 UPDATED TEST ST',
      'addressLine2', CAST(NULL AS STRING),
      'addressLine3', CAST(NULL AS STRING),
      'addressLine4', CAST(NULL AS STRING)
    )
  )
WHERE __txn_id_long = 999999999999999999;
```

**Verify — expected: `addressLine1 = '999 UPDATED TEST ST'`**

```sql
SELECT __txn_id_long, addr.addressLine1
FROM your_catalog.your_schema.your_table
LATERAL VIEW EXPLODE(addresses) t AS addr
WHERE __txn_id_long = 999999999999999999;
```

---

## DELETE

Targeted deletion by primary key — precise, no risk of accidentally deleting other rows.

```sql
DELETE FROM your_catalog.your_schema.your_table
WHERE __txn_id_long = 999999999999999999;
```

**Verify — expected: `should_be_zero = 0`**

```sql
SELECT COUNT(*) AS should_be_zero
FROM your_catalog.your_schema.your_table
WHERE __txn_id_long = 999999999999999999;
```
