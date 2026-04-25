import React from 'react';
import { Database, ArrowRight } from 'lucide-react';
import type { PipelineInfo } from '../types';

interface HeaderProps {
  pipeline: PipelineInfo;
}

const Header: React.FC<HeaderProps> = ({ pipeline }) => {
  return (
    <header className="bg-slate-800 text-white p-4 shadow-md flex items-center justify-between border-b border-slate-700">
      <div className="flex items-center space-x-3">
        <div className="bg-blue-600 p-2 rounded-lg">
          <Database size={24} />
        </div>
        <div>
          <h1 className="text-xl font-bold">{pipeline.name}</h1>
          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">GlueSync Dashboard</p>
        </div>
      </div>

      <div className="flex items-center space-x-6 bg-slate-900 px-6 py-2 rounded-full border border-slate-700">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-sm font-medium">{pipeline.sourceAgent.type}</span>
          <span className="text-xs text-slate-500">({pipeline.sourceAgent.db})</span>
        </div>

        <ArrowRight className="text-slate-600" size={16} />

        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">{pipeline.targetAgent.type}</span>
          <span className="text-xs text-slate-500">({pipeline.targetAgent.db})</span>
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right">
          <div className="text-xs text-slate-400">Environment</div>
          <div className="text-sm font-semibold">Production</div>
        </div>
      </div>
    </header>
  );
};

export default Header;
