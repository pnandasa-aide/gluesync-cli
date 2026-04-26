import React, { useRef, useEffect } from 'react';
import { Search, Activity, Clock, Layers, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';
import type { Entity } from '../types';

interface MainPanelProps {
  entities: Entity[];
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  activeEntityId: string | null;
  onSelectEntity: (entityId: string) => void;
}

const MainPanel: React.FC<MainPanelProps> = ({ entities, searchQuery, setSearchQuery, activeEntityId, onSelectEntity }) => {
  const filteredEntities = entities.filter(e =>
    e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.sourceTable.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.targetTable.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const entityRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (activeEntityId && entityRefs.current[activeEntityId]) {
      entityRefs.current[activeEntityId]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeEntityId]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'syncing': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      case 'active': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'error': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'syncing': return <Activity size={14} className="animate-spin" />;
      case 'active': return <CheckCircle2 size={14} />;
      case 'error': return <AlertCircle size={14} />;
      default: return <Clock size={14} />;
    }
  };

  return (
    <div className="flex-1 bg-slate-50 flex flex-col h-full overflow-hidden">
      <div className="p-4 bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search entities, tables..."
            className="w-full pl-10 pr-4 py-2 bg-slate-100 border-none rounded-lg focus:ring-2 focus:ring-blue-500 transition-all text-sm"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {filteredEntities.map((entity) => (
          <div
            key={entity.id}
            ref={(el) => { entityRefs.current[entity.id] = el; }}
            onClick={() => onSelectEntity(entity.id)}
            className={`bg-white rounded-xl border-2 transition-all cursor-pointer p-5 hover:shadow-md ${
              activeEntityId === entity.id ? 'border-blue-500 ring-4 ring-blue-500/5' : 'border-slate-100'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${getStatusColor(entity.status)}`}>
                  <Layers size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">{entity.name}</h3>
                  <div className="flex items-center text-xs text-slate-500 space-x-2">
                    <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded">{entity.sourceTable}</span>
                    <ArrowRight size={10} />
                    <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded">{entity.targetTable}</span>
                  </div>
                </div>
              </div>

              <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-xs font-bold uppercase tracking-wider ${getStatusColor(entity.status)}`}>
                {getStatusIcon(entity.status)}
                <span>{entity.status}</span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">Sync Progress</div>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ${entity.status === 'error' ? 'bg-red-500' : 'bg-blue-500'}`}
                      style={{ width: `${entity.progress}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-slate-700">{entity.progress}%</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">Time Lag</div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Clock size={14} className="text-slate-400" />
                  <span className="text-sm font-semibold">{entity.timeLag}</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">Processed</div>
                <div className="text-sm font-semibold text-slate-700">
                  {entity.recordsProcessed.toLocaleString()} <span className="text-[10px] font-normal text-slate-400">records</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">Remaining</div>
                <div className="text-sm font-semibold text-slate-700">
                  {entity.recordsRemaining.toLocaleString()} <span className="text-[10px] font-normal text-slate-400">records</span>
                </div>
              </div>
            </div>
          </div>
        ))}

        {filteredEntities.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Search size={48} className="mb-4 opacity-20" />
            <p>No entities found matching "{searchQuery}"</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default MainPanel;
