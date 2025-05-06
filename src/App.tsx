// src/App.tsx
import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import ChatWindow from './components/ChatWindow';
import ToolWidgets from './components/ToolWidgets';
import { DEFAULT_ROLE } from './config/constants';

export default function App() {
  const [role, setRole] = useState(DEFAULT_ROLE);

  return (
    <div className="flex h-screen w-screen">
      <Sidebar role={role} setRole={setRole} />
      <div className="flex flex-col flex-1">
        <Topbar currentRole={role} />
        <div className="flex flex-1 overflow-hidden">
          <ChatWindow role={role} />
          <ToolWidgets role={role} key={role} />
        </div>
      </div>
    </div>
  );
}
