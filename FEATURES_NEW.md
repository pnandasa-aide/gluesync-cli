# GlueSync CLI - New Features Summary

## Overview

This document summarizes the new features added to GlueSync CLI to handle AS400 metadata fields, composite primary keys, and entity lifecycle management.

---

## 1. AS400 _RRN Metadata Field Handling

### What is _RRN?

The `_RRN` (Relative Record Number) is a **system-generated metadata field** provided by AS400/DB2:
- NOT a physical column in the AS400 table schema
- Automatically tracked by DB2 for every row
- Exposed by GlueSync UI as an available source field in field mapping
- Used as a **pseudo-primary-key** when the source table has no defined PK

### Problem

When creating entities via CLI:
- `_RRN` appears in source columns but should NOT be mapped to target
- Target MSSQL tables don't have `_RRN` field
- Incomplete mapping causes UI warnings

### Solution

Added `--skip-rrn` flag to entity creation:

```bash
# Default behavior: Skip _RRN (recommended)
python3 gluesync_cli_v2.py create entity \
  --pipeline 32c1dc34 \
  --source-library GSLIBTST \
  --source-table CUSTOMERS \
  --target-schema dbo \
  --target-table customers \
  --skip-rrn  # This is the default

# Include _RRN (rare cases)
python3 gluesync_cli_v2.py create entity \
  --pipeline 32c1dc34 \
  --source-library GSLIBTST \
  --source-table CUSTOMERS \
  --target-schema dbo \
  --target-table customers \
  --include-rrn  # Override default
```

### Implementation

- **File**: `gluesync_cli_v2.py`
- **Method**: `create_entity(..., skip_rrn: bool = True, ...)`
- **Default**: `True` (skip _RRN by default)
- **CLI Flags**:
  - `--skip-rrn` (default, explicit)
  - `--include-rrn` (override to include)

---

## 2. IDENTITY/AUTO_INCREMENT PK Warning

### Problem

When creating target tables with IDENTITY/AUTO_INCREMENT columns as primary keys:
- In replication, PK values come from the **source system**
- Target should NOT auto-generate PK values
- IDENTITY property causes conflicts during replication

### Solution

Added interactive warning when creating tables with IDENTITY PK:

```python
# In create_target_table()
if warn_identity_pk and is_identity and is_pk:
    print("⚠️  WARNING: Column is IDENTITY and is used as PRIMARY KEY")
    print("   In replication, PK values come from the source system.")
    print("   The target should NOT auto-generate PK values!")
    user_input = input("   Continue anyway? (yes/no): ")
    if user_input.lower() != 'yes':
        raise Exception("Aborted: Remove IDENTITY from PK column")
```

### Usage

```bash
# Warning enabled by default
python3 gluesync_cli_v2.py create target-table \
  --pipeline 32c1dc34 \
  --schema dbo \
  --table mytable \
  --columns '[{"name": "ID", "type": "int", "is_identity": true}]' \
  --primary-key "ID"
  # Will warn and ask for confirmation

# Disable warning (for special cases)
# Set warn_identity_pk=False in API call
```

### Implementation

- **File**: `gluesync_cli_v2.py`
- **Method**: `create_target_table(..., warn_identity_pk: bool = True)`
- **Default**: `True` (warn by default)
- **Behavior**: Interactive prompt requires user confirmation

---

## 3. Entity Deletion

### Problem

Previous implementation had `delete_entity()` as `NotImplementedError`.

### Solution

Implemented entity deletion via GlueSync API:

```python
def delete_entity(self, pipeline_id: str, entity_id: str):
    """Delete an entity from the pipeline"""
    resp = self.request("DELETE", f"/pipelines/{pipeline_id}/entities/{entity_id}")
    return resp.status_code in [200, 202, 204]
```

### Usage

```bash
# Delete an entity
python3 gluesync_cli_v2.py delete entity <entity_id> --pipeline <pipeline_id>

# Example
python3 gluesync_cli_v2.py delete entity a53b7c28 --pipeline 32c1dc34
```

### Implementation

- **File**: `gluesync_cli_v2.py`
- **Method**: `delete_entity(pipeline_id, entity_id)`
- **API Endpoint**: `DELETE /pipelines/{id}/entities/{entity_id}`
- **Success Codes**: 200, 202, 204

---

## 4. Composite Primary Key Support

### Problem

Need to test tables with multiple primary key columns to verify:
- qadmcli can create tables with composite PKs
- GlueSync CLI handles multi-column keys correctly
- Field mapping works for composite keys

### Solution

Created ORDERS table schema with composite PK:

**Schema File**: `qadmcli/schemas/orders.yaml`

```yaml
primary_key:
  columns:
    - "ORDER_ID"
    - "CUST_ID"
  constraint_name: "PK_ORDERS"
```

**SQL Structure**:
```sql
CREATE TABLE [dbo].[orders] (
   [ORDER_ID] int NOT NULL,
   [CUST_ID] int NOT NULL,
   [PRODUCT_ID] int NOT NULL,  -- NOT NULL but NOT part of PK
   ...
   CONSTRAINT [PK_ORDERS] PRIMARY KEY ([ORDER_ID], [CUST_ID])
);
```

### Key Features Tested

1. **Composite PK**: ORDER_ID + CUST_ID
2. **Non-null non-PK column**: PRODUCT_ID (NOT NULL but not in PK)
3. **Nullable columns**: TOTAL_AMOUNT, SHIP_DATE, NOTES
4. **Secondary indexes**: IDX_ORDERS_PRODUCT, IDX_ORDERS_DATE

### Test Script

**File**: `gluesync-cli/test_multi_pk.sh`

Runs complete test workflow:
1. Create ORDERS table on MSSQL via qadmcli
2. Verify table structure and PK
3. Delete CUSTOMERS2 entity
4. Create ORDERS entity with _RRN skip
5. Verify entity configuration

### Usage

```bash
# Run the test suite
cd ~/gluesync-cli
./test_multi_pk.sh
```

---

## 5. CLI Command Reference

### Create Entity

```bash
python3 gluesync_cli_v2.py create entity \
  --pipeline <pipeline_id> \
  --source-library <AS400_library> \
  --source-table <source_table> \
  --target-schema <target_schema> \
  --target-table <target_table> \
  [--polling-interval 500] \
  [--batch-size 1000] \
  [--skip-rrn] \              # Default: skip _RRN
  [--include-rrn]             # Override: include _RRN
```

### Delete Entity

```bash
python3 gluesync_cli_v2.py delete entity <entity_id> \
  --pipeline <pipeline_id>
```

### Get Entity Details

```bash
# Summary
python3 gluesync_cli_v2.py get entity <entity_id> --pipeline <pipeline_id>

# Full details (includes columns and mappings)
python3 gluesync_cli_v2.py get entity <entity_id> --pipeline <pipeline_id> --full
```

---

## Files Modified

### gluesync-cli Project

1. **gluesync_cli_v2.py**
   - `create_entity()` - Added `skip_rrn` parameter
   - `create_target_table()` - Added `warn_identity_pk` parameter
   - `delete_entity()` - Implemented (was NotImplementedError)
   - CLI parsers - Added `--skip-rrn` and `--include-rrn` flags

2. **test_multi_pk.sh** (NEW)
   - Complete test suite for new features
   - Creates ORDERS table, deletes CUSTOMERS2, adds ORDERS entity

3. **README.md**
   - Updated with new commands

### qadmcli Project

1. **schemas/orders.yaml** (NEW)
   - ORDERS table schema with composite PK
   - Column definitions and indexes
   - Complete CREATE TABLE statement

---

## Testing Checklist

- [x] _RRN skip option added to CLI
- [x] IDENTITY PK warning implemented
- [x] Entity deletion method implemented
- [x] ORDERS schema file created with composite PK
- [x] Test script created
- [ ] Run test script to create ORDERS table
- [ ] Run test script to delete CUSTOMERS2 entity
- [ ] Run test script to add ORDERS entity
- [ ] Verify _RRN is excluded in UI field mapping
- [ ] Verify composite PK appears correctly in entity details
- [ ] Test entity start/stop with composite PK table

---

## Next Steps

1. **Run Test Suite**: Execute `test_multi_pk.sh` to validate all features
2. **Verify in UI**: Check field mapping for _RRN exclusion
3. **Test Replication**: Start ORDERS entity and verify data flow
4. **Capture Group APIs**: Proceed with entity group/chain capture
5. **Document Findings**: Update WORKFLOW_GUIDE.md with composite PK workflow

---

## Known Limitations

1. **_RRN Handling**: Currently just skips the field; future enhancement could map it to a custom tracking column if needed
2. **Composite PK Discovery**: Schema discovery API should return multiple keys - needs verification
3. **Delete Validation**: No confirmation prompt (consider adding `--force` flag for safety)
4. **IDENTITY Warning**: Only works in `create_target_table()`, not in entity creation (GlueSync auto-creates tables)

---

## Related Documentation

- [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) - Complete CLI workflow examples
- [MITM_PROXY.md](proxy/MITM_PROXY.md) - API capture workflows
- [qadmcli/schemas/orders.yaml](../qadmcli/schemas/orders.yaml) - Composite PK schema example
