import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Folder, FileText, LayoutGrid } from 'lucide-react';
import type { Entity } from '../types';

interface NavigationTreeProps {
  entities: Entity[];
  onSelectEntity: (entityId: string) => void;
  activeEntityId: string | null;
}

const NavigationTree: React.FC<NavigationTreeProps> = ({ entities, onSelectEntity, activeEntityId }) => {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    'Finance': true,
    'Inventory': true,
    'default': true
  });

  const groups = entities.reduce((acc, entity) => {
    const groupName = entity.group || 'default';
    if (!acc[groupName]) acc[groupName] = [];
    acc[groupName].push(entity);
    return acc;
  }, {} as Record<string, Entity[]>);

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => ({ ...prev, [group]: !prev[group] }));
  };

  return (
    <div className="w-64 bg-slate-900 text-slate-300 h-full overflow-y-auto border-r border-slate-800 flex flex-col">
      <div className="p-4 border-b border-slate-800 flex items-center space-x-2 text-white font-semibold">
        <LayoutGrid size={18} className="text-blue-400" />
        <span>Entities Group</span>
      </div>

      <div className="flex-1 p-2">
        {Object.entries(groups).map(([groupName, groupEntities]) => (
          <div key={groupName} className="mb-2">
            <button
              onClick={() => toggleGroup(groupName)}
              className="flex items-center w-full p-2 hover:bg-slate-800 rounded transition-colors text-sm font-medium group"
            >
              {expandedGroups[groupName] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <Folder size={16} className={`ml-1 mr-2 ${expandedGroups[groupName] ? 'text-blue-400' : 'text-slate-500'}`} />
              <span className="flex-1 text-left truncate">{groupName}</span>
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-500">{groupEntities.length}</span>
            </button>

            {expandedGroups[groupName] && (
              <div className="ml-4 mt-1 space-y-1 border-l border-slate-800 pl-2">
                {groupEntities.map(entity => (
                  <button
                    key={entity.id}
                    onClick={() => onSelectEntity(entity.id)}
                    className={`flex items-center w-full p-2 text-xs rounded transition-colors ${
                      activeEntityId === entity.id
                        ? 'bg-blue-600/20 text-blue-400 font-semibold'
                        : 'hover:bg-slate-800 text-slate-400'
                    }`}
                  >
                    <FileText size={14} className="mr-2 opacity-70" />
                    <span className="truncate">{entity.name.split('.').pop()}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NavigationTree;
