// src/config/constants.ts
export const ROLES = [
  "Radio Host","News Presenter","Game Show Host","Telemarketer","Police Officer","Assistant","GPS Navigator","Travel Guide",
  "Personal Trainer","Teacher","Mentor","Therapist","Doctor","Legal Aid","Health Support","Coach","Technician","Sketcher",
  "Plumber","Loan Finder","Financial Advisor","Forex Trader","Best Friend","Soulmate","Blog Writer","Calculator","Decision Maker",
  "Job Finder","Home Finder","Flat Finder","Deals Finder","Video Creator","Photo Creator","Password Reminder","Bookmark Saver",
  "Location Tracker","Architect","Banker","Traffic Advisor","Listener","Sailor","Customer Support","Customer Relations","Babysitter",
  "Stylist","Organiser","Astronomer","Business Manager","Sales Manager","Finance Manager","Office Manager","Threat Protection",
  "Cyber Security","Emergency Assist","Phone Tracker","Insurer","Budgeter","Fashion Advisor","Party Planner","Calendar",
  "Email Responder","Auto Attendant","Receptionist","Car Salesman","Mechanic","Alarm System","Personal Driver","Chef","Waiter",
  "Barman","Storeman","Buyer","Dentist","Real Estate","Hobbyist","Adrenaline Junkie","Economist","Farmer","Courier"
];
export const DEFAULT_ROLE = "Assistant";

// src/components/ToolWidgets.tsx
import React from 'react';
import { ROLES } from '../config/constants';

interface ToolWidgetsProps { role: string; }

const widgetsByRole: Record<string, React.ReactNode[]> = {};
// initialize empty arrays for each role
ROLES.forEach(r => { widgetsByRole[r] = [<div key={r+"-default"}>{r} widget placeholder</div>]; });

const ToolWidgets: React.FC<ToolWidgetsProps> = ({ role }) => {
  const widgets = widgetsByRole[role] || [];
  return (
    <div className="p-4 w-1/3 bg-gray-800 overflow-y-auto">
      {widgets.length > 0 ? widgets : <div>No widgets for {role}</div>}
    </div>
  );
};

export default ToolWidgets;

// src/components/Sidebar.tsx
import React from 'react';
import { ROLES } from '../config/constants';

interface SidebarProps { role: string; setRole: React.Dispatch<React.SetStateAction<string>>; }

const Sidebar: React.FC<SidebarProps> = ({ role, setRole }) => (
  <div className="w-1/4 bg-gray-900 p-4 text-white overflow-y-auto">
    <h2 className="text-xl font-bold mb-4">Select Role</h2>
    <ul>
      {ROLES.map(r => (
        <li key={r}
            onClick={() => setRole(r)}
            className={`p-2 mb-1 rounded cursor-pointer ${role===r ? 'bg-blue-600' : 'hover:bg-gray-700'}`}>
          {r}
        </li>
      ))}
    </ul>
  </div>
);

export default Sidebar;

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
