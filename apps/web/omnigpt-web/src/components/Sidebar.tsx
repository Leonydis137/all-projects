// src/components/Sidebar.tsx

import React from 'react';
import { ROLES } from '../config/constants';

interface SidebarProps {
  role: string;
  setRole: React.Dispatch<React.SetStateAction<string>>;
}

const Sidebar: React.FC<SidebarProps> = ({ role, setRole }) => (
  <div className="w-1/4 bg-gray-900 p-4 text-white overflow-y-auto">
    <h2 className="text-xl font-bold mb-4">Select Role</h2>
    <ul>
      {ROLES.map(r => (
        <li
          key={r}
          onClick={() => setRole(r)}
          className={`p-2 mb-1 rounded cursor-pointer ${role === r ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
        >
          {r}
        </li>
      ))}
    </ul>
  </div>
);

export default Sidebar;
