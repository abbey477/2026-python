# Test DML — INSERT / UPDATE / DELETE

**Table:** `your_catalog.your_schema.your_table` ← update this  
**Primary Key:** `__txn_id_long`  
**Test PK value used throughout:** `999999999999999999` — unique, will not collide with real data

---

## INSERT

```sql
INSERT INTO your_catalog.your_schema.your_table
  (__cob_date, _slice, __txn_id_long, __START_AT, __END_AT, alternateIdentifiers)
VALUES (
  CAST('2024-04-30' AS DATE),
  'COMMON',
  999999999999999999,                                          -- test PK value
  CAST('2024-05-30T02:21:19.203+00:00' AS TIMESTAMP),
  CAST('2024-08-20T15:54:47.933+00:00' AS TIMESTAMP),
  ARRAY(
    NAMED_STRUCT(
      'luminIdentifier',       '-1',
      'ymflIdentifier',        '-1',
      'rdrDerivedKey',         '9999999999',
      'replacedInstrumentId',  CAST(NULL AS STRING),
      'sourceSystemName',      'CERDCORPORATE',
      'emboldIdentifier',      '-1',
      'cerdCorpIdentifier',    '99999999.0000000000',
      'coreSecurityIdentifier','-1',
      'assetId',               '99999999',
      'hpsplIdentifier',       '-1',
      'gaveaIdentifier',       '-1',
      'isAssetExpired',        'N',
      'assetIdType',           'CERD',
      'iliteIdentifier',       '-1',
      'instrumentId',          '9999999999',
      'toppsIdentifier',       '-1',
      'gmrdIdentifier',        '-1.0000000000',
      'olympicIdentifier',     '-1',
      'omniIdentifier',        '-1',
      'statusCode',            'ACTIVE',
      'sourceId',              'TEST',
      'hbdwIdentifier',        '-1'
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

Updates `statusCode` and `sourceId` on the test record using the primary key.

```sql
UPDATE your_catalog.your_schema.your_table
SET alternateIdentifiers = ARRAY(
    NAMED_STRUCT(
      'luminIdentifier',       '-1',
      'ymflIdentifier',        '-1',
      'rdrDerivedKey',         '9999999999',
      'replacedInstrumentId',  CAST(NULL AS STRING),
      'sourceSystemName',      'CERDCORPORATE',
      'emboldIdentifier',      '-1',
      'cerdCorpIdentifier',    '99999999.0000000000',
      'coreSecurityIdentifier','-1',
      'assetId',               '99999999',
      'hpsplIdentifier',       '-1',
      'gaveaIdentifier',       '-1',
      'isAssetExpired',        'Y',                -- ← changed
      'assetIdType',           'CERD',
      'iliteIdentifier',       '-1',
      'instrumentId',          '9999999999',
      'toppsIdentifier',       '-1',
      'gmrdIdentifier',        '-1.0000000000',
      'olympicIdentifier',     '-1',
      'omniIdentifier',        '-1',
      'statusCode',            'INACTIVE',         -- ← changed
      'sourceId',              'TEST_UPDATED',     -- ← changed
      'hbdwIdentifier',        '-1'
    )
  )
WHERE __txn_id_long = 999999999999999999;
```

**Verify — expected: `statusCode = INACTIVE`, `isAssetExpired = Y`, `sourceId = TEST_UPDATED`**

```sql
SELECT __txn_id_long, alt.statusCode, alt.isAssetExpired, alt.sourceId
FROM your_catalog.your_schema.your_table
LATERAL VIEW EXPLODE(alternateIdentifiers) t AS alt
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
