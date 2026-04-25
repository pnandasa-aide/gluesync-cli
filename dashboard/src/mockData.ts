import type { Entity, PipelineInfo } from './types';

export const pipelineInfo: PipelineInfo = {
  name: "Production ERP Sync",
  sourceAgent: {
    type: "AS400 DB2 for i",
    host: "161.82.146.249",
    db: "GSLIBTST"
  },
  targetAgent: {
    type: "MSSQL",
    host: "192.168.13.62",
    db: "GSTargetDB"
  }
};

export const entities: Entity[] = [
  {
    id: "e1",
    name: "GSLIBTST.CUSTOMERS",
    sourceTable: "CUSTOMERS",
    targetTable: "customers",
    status: 'syncing',
    progress: 75,
    timeLag: "1.2s",
    recordsProcessed: 152340,
    recordsRemaining: 50000,
    lastSync: "2026-04-08 14:30:00",
    group: "Finance",
    properties: {
      pollingInterval: 500,
      batchSize: 1000,
      writeMethod: "UPSERT"
    },
    mappings: [
      { sourceColumn: "CUST_ID", sourceType: "INTEGER", targetColumn: "cust_id", targetType: "int", isPrimaryKey: true },
      { sourceColumn: "FIRST_NAME", sourceType: "CHARACTER", targetColumn: "first_name", targetType: "varchar(50)", isPrimaryKey: false },
      { sourceColumn: "LAST_NAME", sourceType: "CHARACTER", targetColumn: "last_name", targetType: "varchar(50)", isPrimaryKey: false },
      { sourceColumn: "EMAIL", sourceType: "VARCHAR", targetColumn: "email", targetType: "varchar(100)", isPrimaryKey: false },
      { sourceColumn: "CREATED_AT", sourceType: "TIMESTAMP", targetColumn: "created_at", targetType: "datetime", isPrimaryKey: false }
    ]
  },
  {
    id: "e2",
    name: "GSLIBTST.ORDERS",
    sourceTable: "ORDERS",
    targetTable: "orders",
    status: 'active',
    progress: 100,
    timeLag: "0.5s",
    recordsProcessed: 892100,
    recordsRemaining: 0,
    lastSync: "2026-04-08 14:31:05",
    group: "Finance",
    properties: {
      pollingInterval: 1000,
      batchSize: 2000,
      writeMethod: "INSERT"
    },
    mappings: [
      { sourceColumn: "ORDER_ID", sourceType: "INTEGER", targetColumn: "order_id", targetType: "int", isPrimaryKey: true },
      { sourceColumn: "CUST_ID", sourceType: "INTEGER", targetColumn: "cust_id", targetType: "int", isPrimaryKey: false },
      { sourceColumn: "ORDER_DATE", sourceType: "DATE", targetColumn: "order_date", targetType: "date", isPrimaryKey: false },
      { sourceColumn: "TOTAL_AMOUNT", sourceType: "DECIMAL", targetColumn: "total_amount", targetType: "decimal(18,2)", isPrimaryKey: false }
    ]
  },
  {
    id: "e3",
    name: "GSLIBTST.PRODUCTS",
    sourceTable: "PRODUCTS",
    targetTable: "products",
    status: 'stopped',
    progress: 45,
    timeLag: "N/A",
    recordsProcessed: 5000,
    recordsRemaining: 6000,
    lastSync: "2026-04-07 10:00:00",
    group: "Inventory",
    properties: {
      pollingInterval: 5000,
      batchSize: 500,
      writeMethod: "UPSERT"
    },
    mappings: [
      { sourceColumn: "PROD_ID", sourceType: "INTEGER", targetColumn: "prod_id", targetType: "int", isPrimaryKey: true },
      { sourceColumn: "PROD_NAME", sourceType: "CHARACTER", targetColumn: "name", targetType: "varchar(100)", isPrimaryKey: false },
      { sourceColumn: "PRICE", sourceType: "DECIMAL", targetColumn: "price", targetType: "decimal(12,2)", isPrimaryKey: false }
    ]
  },
  {
    id: "e4",
    name: "GSLIBTST.STOCKS",
    sourceTable: "STOCKS",
    targetTable: "stocks",
    status: 'error',
    progress: 10,
    timeLag: "ERR",
    recordsProcessed: 120,
    recordsRemaining: 15000,
    lastSync: "2026-04-08 09:15:00",
    group: "Inventory",
    properties: {
      pollingInterval: 2000,
      batchSize: 100,
      writeMethod: "UPSERT"
    },
    mappings: [
      { sourceColumn: "PROD_ID", sourceType: "INTEGER", targetColumn: "prod_id", targetType: "int", isPrimaryKey: true },
      { sourceColumn: "QTY", sourceType: "INTEGER", targetColumn: "quantity", targetType: "int", isPrimaryKey: false }
    ]
  },
  {
    id: "e5",
    name: "GSLIBTST.LOGS",
    sourceTable: "LOGS",
    targetTable: "replication_logs",
    status: 'active',
    progress: 100,
    timeLag: "5s",
    recordsProcessed: 10500,
    recordsRemaining: 0,
    lastSync: "2026-04-08 14:28:00",
    group: "default",
    properties: {
      pollingInterval: 10000,
      batchSize: 5000,
      writeMethod: "INSERT"
    },
    mappings: [
      { sourceColumn: "LOG_ID", sourceType: "BIGINT", targetColumn: "id", targetType: "bigint", isPrimaryKey: true },
      { sourceColumn: "MESSAGE", sourceType: "VARCHAR", targetColumn: "msg", targetType: "nvarchar(max)", isPrimaryKey: false }
    ]
  }
];
