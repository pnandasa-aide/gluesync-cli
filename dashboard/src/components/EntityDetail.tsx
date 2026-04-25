import React, { useState } from 'react';
import { Settings, Table, ChevronLeft, Info, Key, Terminal } from 'lucide-react';
import type { Entity } from '../types';

interface EntityDetailProps {
  entity: Entity | null;
}

const EntityDetail: React.FC<EntityDetailProps> = ({ entity }) => {
  const [showMapping, setShowMapping] = useState(false);

  if (!entity) {
    return (
      <div className="w-80 bg-white border-l border-slate-200 flex flex-col items-center justify-center p-6 text-center text-slate-400">
        <div className="bg-slate-50 p-6 rounded-full mb-4">
          <Info size={48} className="opacity-20" />
        </div>
        <p className="text-sm">Select an entity to view its configuration and mapping details.</p>
      </div>
    );
  }

  return (
    <div className="w-80 bg-white border-l border-slate-200 flex flex-col h-full relative overflow-hidden transition-all">
      {/* Mapping Slide-over */}
      <div
        className={`absolute inset-0 bg-white z-20 transition-transform duration-300 transform flex flex-col ${
          showMapping ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-slate-200 flex items-center bg-slate-900 text-white">
          <button
            onClick={() => setShowMapping(false)}
            className="p-1 hover:bg-slate-800 rounded-full mr-2"
          >
            <ChevronLeft size={20} />
          </button>
          <h2 className="font-bold text-sm">Column Mappings</h2>
        </div>

        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 sticky top-0 text-slate-500 uppercase font-bold text-[9px] tracking-widest border-b border-slate-200">
              <tr>
                <th className="p-3 text-left">Source</th>
                <th className="p-3 text-left">Target</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entity.mappings.map((m, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="p-3">
                    <div className="flex items-center space-x-1">
                      {m.isPrimaryKey && <Key size={10} className="text-amber-500" />}
                      <span className="font-semibold text-slate-700">{m.sourceColumn}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">{m.sourceType}</div>
                  </td>
                  <td className="p-3">
                    <span className="font-semibold text-slate-700">{m.targetColumn}</span>
                    <div className="text-[10px] text-slate-400 font-mono">{m.targetType}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Settings size={18} className="text-slate-400" />
          <h2 className="font-bold text-slate-800">Entity Properties</h2>
        </div>
        <button
          onClick={() => setShowMapping(true)}
          className="text-[10px] bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded font-bold transition-colors flex items-center"
        >
          <Table size={12} className="mr-1" />
          VIEW MAPPING
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <section>
          <h3 className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-3 flex items-center">
            <Info size={12} className="mr-1.5" /> General Info
          </h3>
          <div className="bg-slate-50 rounded-lg p-3 space-y-3">
            <div>
              <div className="text-[10px] text-slate-500 mb-0.5">Entity ID</div>
              <div className="text-xs font-mono font-semibold break-all text-slate-700">{entity.id}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 mb-0.5">Last Full Sync</div>
              <div className="text-xs font-semibold text-slate-700">{entity.lastSync}</div>
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-3 flex items-center">
            <Settings size={12} className="mr-1.5" /> Replication Config
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center p-2 border-b border-slate-100">
              <span className="text-xs text-slate-500">Polling Interval</span>
              <span className="text-xs font-bold text-slate-700">{entity.properties.pollingInterval}ms</span>
            </div>
            <div className="flex justify-between items-center p-2 border-b border-slate-100">
              <span className="text-xs text-slate-500">Batch Size</span>
              <span className="text-xs font-bold text-slate-700">{entity.properties.batchSize} rows</span>
            </div>
            <div className="flex justify-between items-center p-2 border-b border-slate-100">
              <span className="text-xs text-slate-500">Write Method</span>
              <span className="text-xs font-bold px-1.5 py-0.5 bg-slate-200 rounded text-slate-700">{entity.properties.writeMethod}</span>
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-3 flex items-center">
            <Terminal size={12} className="mr-1.5" /> Recent Logs
          </h3>
          <div className="font-mono text-[9px] bg-slate-900 text-slate-300 p-3 rounded-lg overflow-x-auto">
            <div className="text-blue-400 mb-1">INFO [14:30:05] Starting batch fetch...</div>
            <div className="text-green-400 mb-1">SUCCESS [14:30:12] Processed 1,000 records.</div>
            <div className="text-slate-500 italic">Waiting for next iteration...</div>
          </div>
        </section>
      </div>

      <div className="p-4 border-t border-slate-100 bg-slate-50 mt-auto">
        <button className="w-full bg-slate-800 hover:bg-slate-700 text-white text-xs py-2.5 rounded-lg font-bold transition-all shadow-sm">
          EDIT CONFIGURATION
        </button>
      </div>
    </div>
  );
};

export default EntityDetail;
