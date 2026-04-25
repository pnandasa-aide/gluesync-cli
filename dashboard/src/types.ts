export interface ColumnMapping {
  sourceColumn: string;
  sourceType: string;
  targetColumn: string;
  targetType: string;
  isPrimaryKey: boolean;
}

export interface Entity {
  id: string;
  name: string;
  sourceTable: string;
  targetTable: string;
  status: 'active' | 'syncing' | 'stopped' | 'error';
  progress: number;
  timeLag: string;
  recordsProcessed: number;
  recordsRemaining: number;
  lastSync: string;
  group: string;
  mappings: ColumnMapping[];
  properties: {
    pollingInterval: number;
    batchSize: number;
    writeMethod: string;
  };
}

export interface EntityGroup {
  name: string;
  entities: Entity[];
}

export interface PipelineInfo {
  name: string;
  sourceAgent: {
    type: string;
    host: string;
    db: string;
  };
  targetAgent: {
    type: string;
    host: string;
    db: string;
  };
}
