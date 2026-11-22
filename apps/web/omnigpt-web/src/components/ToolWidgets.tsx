// src/components/ToolWidgets.tsx

import React from 'react';
import { ROLES } from '../config/constants';

interface ToolWidgetsProps {
  role: string;
}

const widgetsByRole: Record<string, React.ReactNode[]> = {};
// Initialize empty arrays for each role with placeholders
ROLES.forEach(r => { 
  widgetsByRole[r] = [<div key={r + "-default"}>{r} widget placeholder</div>];
});

const ToolWidgets: React.FC<ToolWidgetsProps> = ({ role }) => {
  const widgets = widgetsByRole[role] || [];

  return (
    <div className="p-4 w-1/3 bg-gray-800 overflow-y-auto">
      {widgets.length > 0 ? widgets : <div>No widgets for {role}</div>}
    </div>
  );
};

export default ToolWidgets;
