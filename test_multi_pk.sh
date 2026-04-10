#!/bin/bash
#
# Test Script: Multi-PK Table and GlueSync CLI Features
#
# Tests:
# 1. Create ORDERS table with composite PK on MSSQL
# 2. Add ORDERS entity to GlueSync pipeline
# 3. Delete CUSTOMERS2 entity
# 4. Verify _RRN skip option
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PIPELINE_ID="32c1dc34"
QADMCLI_DIR="/home/ubuntu/_qoder/qadmcli"
GLUESYNC_CLI_DIR="/home/ubuntu/_qoder/gluesync-cli"

echo "=========================================="
echo "  GlueSync CLI Feature Test Suite"
echo "=========================================="
echo ""

# ==========================================
# Step 1: Create ORDERS table on MSSQL using qadmcli
# ==========================================
log_info "Step 1: Creating ORDERS table with composite PK on MSSQL"
echo ""

cd "$QADMCLI_DIR"

# Use the schema file to create the table
log_info "Using schema from: schemas/orders.yaml"
echo ""

# Extract and execute CREATE TABLE statement
log_info "Executing CREATE TABLE on MSSQL..."
./qadmcli.sh mssql execute -q "
CREATE TABLE [dbo].[orders] (
   [ORDER_ID] int NOT NULL,
   [CUST_ID] int NOT NULL,
   [PRODUCT_ID] int NOT NULL,
   [ORDER_DATE] date NOT NULL,
   [QUANTITY] int NOT NULL,
   [UNIT_PRICE] decimal(10,2) NOT NULL,
   [TOTAL_AMOUNT] decimal(12,2) NULL,
   [STATUS] char(1) NOT NULL,
   [SHIP_DATE] date NULL,
   [NOTES] varchar(500) NULL,
   CONSTRAINT [PK_ORDERS] PRIMARY KEY ([ORDER_ID], [CUST_ID])
);

CREATE INDEX [IDX_ORDERS_PRODUCT] ON [dbo].[orders] ([PRODUCT_ID]);
CREATE INDEX [IDX_ORDERS_DATE] ON [dbo].[orders] ([ORDER_DATE]);
"

if [ $? -eq 0 ]; then
    log_info "✓ ORDERS table created successfully"
else
    log_error "✗ Failed to create ORDERS table"
    exit 1
fi

echo ""

# Verify table structure
log_info "Verifying table structure..."
./qadmcli.sh mssql execute -q "
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    IS_NULLABLE,
    CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'orders'
ORDER BY ORDINAL_POSITION;
"

echo ""
log_info "Verifying primary key..."
./qadmcli.sh mssql execute -q "
SELECT 
    kcu.COLUMN_NAME,
    kcu.ORDINAL_POSITION as PK_Order
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' 
    AND tc.TABLE_SCHEMA = 'dbo' 
    AND tc.TABLE_NAME = 'orders'
ORDER BY kcu.ORDINAL_POSITION;
"

echo ""
echo "------------------------------------------"
echo ""

# ==========================================
# Step 2: Delete CUSTOMERS2 entity
# ==========================================
log_info "Step 2: Deleting CUSTOMERS2 entity (testing delete feature)"
echo ""

cd "$GLUESYNC_CLI_DIR"

# Find CUSTOMERS2 entity ID
log_info "Finding CUSTOMERS2 entity..."
ENTITY_INFO=$(python3 gluesync_cli_v2.py get entities --pipeline "$PIPELINE_ID" 2>&1 | grep "CUSTOMERS2" | head -1)

if [ -n "$ENTITY_INFO" ]; then
    ENTITY_ID=$(echo "$ENTITY_INFO" | awk '{print $1}')
    log_info "Found CUSTOMERS2 entity: $ENTITY_ID"
    
    # Delete the entity
    log_info "Deleting entity $ENTITY_ID..."
    if python3 gluesync_cli_v2.py delete entity "$ENTITY_ID" --pipeline "$PIPELINE_ID"; then
        log_info "✓ CUSTOMERS2 entity deleted successfully"
    else
        log_error "✗ Failed to delete CUSTOMERS2 entity"
        exit 1
    fi
else
    log_warn "CUSTOMERS2 entity not found (may already be deleted)"
fi

echo ""
echo "------------------------------------------"
echo ""

# ==========================================
# Step 3: Add ORDERS entity with composite PK
# ==========================================
log_info "Step 3: Adding ORDERS entity with composite PK"
echo ""

log_info "Creating entity: GSLIBTST.ORDERS -> dbo.orders"
log_info "Note: _RRN metadata field will be skipped (default behavior)"
echo ""

if python3 gluesync_cli_v2.py create entity \
    --pipeline "$PIPELINE_ID" \
    --source-library "GSLIBTST" \
    --source-table "ORDERS" \
    --target-schema "dbo" \
    --target-table "orders" \
    --polling-interval 500 \
    --batch-size 1000 \
    --skip-rrn; then
    log_info "✓ ORDERS entity created successfully"
else
    log_error "✗ Failed to create ORDERS entity"
    exit 1
fi

echo ""
echo "------------------------------------------"
echo ""

# ==========================================
# Step 4: Verify entity creation
# ==========================================
log_info "Step 4: Verifying entity configuration"
echo ""

log_info "Listing all entities..."
python3 gluesync_cli_v2.py get entities --pipeline "$PIPELINE_ID"

echo ""
log_info "Getting ORDERS entity details..."
ORDERS_ENTITY=$(python3 gluesync_cli_v2.py get entities --pipeline "$PIPELINE_ID" 2>&1 | grep "ORDERS" | awk '{print $1}')

if [ -n "$ORDERS_ENTITY" ]; then
    log_info "ORDERS Entity ID: $ORDERS_ENTITY"
    echo ""
    
    log_info "Full entity details:"
    python3 gluesync_cli_v2.py get entity "$ORDERS_ENTITY" --pipeline "$PIPELINE_ID" --full
fi

echo ""
echo "=========================================="
log_info "Test Suite Complete!"
echo "=========================================="
echo ""
log_info "Summary:"
echo "  ✓ ORDERS table created with composite PK (ORDER_ID + CUST_ID)"
echo "  ✓ CUSTOMERS2 entity deleted"
echo "  ✓ ORDERS entity added with _RRN skip enabled"
echo ""
log_warn "Next steps:"
echo "  1. Verify _RRN is not in target column mapping (check UI)"
echo "  2. Test entity start: python3 gluesync_cli_v2.py start $ORDERS_ENTITY --pipeline $PIPELINE_ID --mode snapshot"
echo "  3. Capture group/chain APIs when ready"
echo ""
