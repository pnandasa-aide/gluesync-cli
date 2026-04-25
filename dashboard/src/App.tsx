import { useState } from 'react';
import { pipelineInfo, entities } from './mockData';
import Header from './components/Header';
import NavigationTree from './components/NavigationTree';
import MainPanel from './components/MainPanel';
import EntityDetail from './components/EntityDetail';

function App() {
  const [activeEntityId, setActiveEntityId] = useState<string | null>(entities[0].id);
  const [searchQuery, setSearchQuery] = useState('');

  const activeEntity = entities.find(e => e.id === activeEntityId) || null;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-100 font-sans antialiased text-slate-900">
      <Header pipeline={pipelineInfo} />

      <div className="flex flex-1 overflow-hidden">
        <NavigationTree
          entities={entities}
          activeEntityId={activeEntityId}
          onSelectEntity={setActiveEntityId}
        />

        <MainPanel
          entities={entities}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          activeEntityId={activeEntityId}
          onSelectEntity={setActiveEntityId}
        />

        <EntityDetail entity={activeEntity} />
      </div>
    </div>
  );
}

export default App;
