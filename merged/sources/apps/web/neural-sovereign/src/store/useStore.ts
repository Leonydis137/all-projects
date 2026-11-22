import { create } from 'zustand';

export interface User {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
}

export interface SystemNode {
  id: string;
  name: string;
  type: string;
  status: 'ACTIVE' | 'IDLE' | 'SUSPENDED' | 'BOOTING' | 'HIDDEN' | 'MAINTENANCE';
  health: number;
  load: number;
  throughput: string;
  latency: string;
  personality: string;
  color: string;
  description: string;
}

export interface TelemetryEvent {
  id: string;
  source: string;
  message: string;
  level: 'info' | 'warn' | 'error';
  timestamp: string;
}

export interface Mission {
  id: string;
  name: string;
  status: 'EXECUTING' | 'PENDING' | 'SUCCESS' | 'FAILED';
  objective: string;
  progress: number;
}

export interface Tool {
  id: string;
  name: string;
  status: 'READY' | 'EXECUTING' | 'LOCKED';
  type: 'CORE' | 'UTILITY' | 'EXTERNAL';
  description: string;
  lastUsed: string;
}

interface SystemState {
  user: User | null;
  nodes: SystemNode[];
  selectedNodeId: string | null;
  logs: TelemetryEvent[];
  missions: Mission[];
  tools: Tool[];
  activeView: 'overview' | 'terminal' | 'telemetry' | 'agents' | 'memory' | 'infrastructure' | 'security' | 'missions' | 'logs' | 'config' | 'tools';
  uptime: number;
  isKernelActive: boolean;
  isHydrated: boolean;
  systemMetrics: {
    cpu: string;
    memory: string;
    uptime: number;
    platform: string;
  } | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setSystemMetrics: (metrics: SystemState['systemMetrics']) => void;
  setHydrated: (val: boolean) => void;
  setNodes: (nodes: SystemNode[]) => void;
  updateNode: (id: string, updates: Partial<SystemNode>) => void;
  selectNode: (id: string | null) => void;
  setLogs: (logs: TelemetryEvent[]) => void;
  addLog: (log: TelemetryEvent) => void;
  tickUptime: () => void;
  setMissions: (missions: Mission[]) => void;
  addMission: (mission: Mission) => void;
  updateMission: (id: string, updates: Partial<Mission>) => void;
  setView: (view: SystemState['activeView']) => void;
  setTools: (tools: Tool[]) => void;
  updateTool: (id: string, updates: Partial<Tool>) => void;
}

export const INITIAL_NODES: SystemNode[] = [];

export const INITIAL_MISSIONS: Mission[] = [];

export const useStore = create<SystemState>((set) => ({
  user: null,
  nodes: INITIAL_NODES,
  selectedNodeId: null,
  logs: [],
  missions: INITIAL_MISSIONS,
  tools: [],
  activeView: 'overview',
  uptime: 12444312,
  isKernelActive: true,
  isHydrated: false,
  systemMetrics: null,

  setUser: (user) => set({ user }),
  setSystemMetrics: (systemMetrics) => set({ systemMetrics }),
  setHydrated: (isHydrated) => set({ isHydrated }),
  setNodes: (nodes) => set({ nodes }),
  updateNode: (id, updates) => set((state) => ({
    nodes: state.nodes.map(n => n.id === id ? { ...n, ...updates } : n)
  })),
  selectNode: (id) => set({ selectedNodeId: id }),
  setLogs: (logs) => set({ logs }),
  addLog: (log) => set((state) => ({ logs: [...state.logs.slice(-49), log] })),
  tickUptime: () => set((state) => ({ uptime: state.uptime + 1 })),
  setMissions: (missions) => set({ missions }),
  addMission: (mission) => set((state) => ({ missions: [...state.missions, mission] })),
  updateMission: (id, updates) => set((state) => ({
    missions: state.missions.map(m => m.id === id ? { ...m, ...updates } : m)
  })),
  setView: (view) => {
    console.log('[Store] Changing view to:', view);
    set({ activeView: view });
  },
  setTools: (tools) => set({ tools }),
  updateTool: (id, updates) => set((state) => ({
    tools: state.tools.map(t => t.id === id ? { ...t, ...updates } : t)
  }))
}));
