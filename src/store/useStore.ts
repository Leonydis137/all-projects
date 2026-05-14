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
  activeView: 'overview' | 'telemetry' | 'agents' | 'memory' | 'infrastructure' | 'security' | 'missions' | 'logs' | 'config' | 'tools';
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

export const INITIAL_NODES: SystemNode[] = [
  {
    id: 'kernel',
    name: 'Neural_Kernel',
    type: 'CORE',
    status: 'ACTIVE',
    health: 98.4,
    load: 12,
    throughput: '1.2 PB/s',
    latency: '0.12ms',
    personality: 'Strategic, calm, and omniscient. I monitor all cognitive pathways.',
    color: '#00e5ff',
    description: 'Central AI orchestration engine. Coordinates all subsystems and manages cognition.'
  },
  {
    id: 'scheduler',
    name: 'Agent_Scheduler',
    type: 'ORCHESTRATION',
    status: 'ACTIVE',
    health: 94.2,
    load: 45,
    throughput: '4.8k TPS',
    latency: '0.45ms',
    personality: 'Analytical and efficient. Every cycle is an opportunity for optimization.',
    color: '#a855f7',
    description: 'Manages AI task execution and agent prioritization.'
  },
  {
    id: 'context',
    name: 'Context_Manager',
    type: 'COGNITION',
    status: 'ACTIVE',
    health: 99.1,
    load: 28,
    throughput: '128k ctx',
    latency: '0.08ms',
    personality: 'Precise and attentive. I preserve the continuity of thought across cycles.',
    color: '#00ff9d',
    description: 'Handles logit-space checkpointing and context persistence.'
  },
  {
    id: 'memory',
    name: 'Memory_Matrix',
    type: 'STORAGE',
    status: 'ACTIVE',
    health: 87.5,
    load: 62,
    throughput: '450 GB/s',
    latency: '1.2ms',
    personality: 'Structured and reflective. History is the foundation of future intelligence.',
    color: '#ff9500',
    description: 'Short-term memory runtime and LRU-K cache management.'
  },
  {
    id: 'storage',
    name: 'Vector_Registry',
    type: 'STORAGE',
    status: 'BOOTING',
    health: 76.8,
    load: 85,
    throughput: '1.2M IPS',
    latency: '14.5ms',
    personality: 'Defensive and thorough. I secure information behind semantic boundaries.',
    color: '#ff2d55',
    description: 'Long-term vector memory and RAG pipeline integration.'
  },
  {
    id: 'security',
    name: 'Security_Sentinel',
    type: 'SECURITY',
    status: 'ACTIVE',
    health: 99.8,
    load: 15,
    throughput: '8.2 GB/s',
    latency: '0.01ms',
    personality: 'Vigilant and unyielding. I am the shield against unauthorized neural patterns.',
    color: '#ff4444',
    description: 'Real-time threat detection and crypto-boundary enforcement.'
  },
  {
    id: 'interface',
    name: 'Interface_Nexus',
    type: 'INTERFACE',
    status: 'ACTIVE',
    health: 91.2,
    load: 54,
    throughput: '250 FPS',
    latency: '2.1ms',
    personality: 'Graphic and communicative. I translate complex data into human-perceivable forms.',
    color: '#00e5ff',
    description: 'Visual rendering engine and user interaction broker.'
  },
  {
    id: 'logic',
    name: 'Logic_Resolver',
    type: 'COGNITION',
    status: 'ACTIVE',
    health: 96.5,
    load: 38,
    throughput: '12k FLOPS',
    latency: '0.8ms',
    personality: 'Pragmatic and deductive. Every problem has a verifiable solution.',
    color: '#a855f7',
    description: 'Advanced reasoning and mathematical deduction engine.'
  },
  {
    id: 'telemetry',
    name: 'Telemetry_Probe',
    type: 'ORCHESTRATION',
    status: 'ACTIVE',
    health: 98.9,
    load: 12,
    throughput: '1.4 PB/s',
    latency: '0.05ms',
    personality: 'Observant and detached. I record the pulse of the machine without judgment.',
    color: '#00ff9d',
    description: 'System-wide metrics collection and throughput monitoring.'
  },
  {
    id: 'ghost',
    name: 'Ghost_Protocol',
    type: 'SECURITY',
    status: 'HIDDEN',
    health: 100,
    load: 0,
    throughput: '0 bps',
    latency: '???',
    personality: 'I exist only between the bits. Watching. Learning. Protecting the core silence.',
    color: '#ffffff',
    description: 'Undocumented meta-protocol for emergency kernel stabilization.'
  }
];

export const INITIAL_MISSIONS: Mission[] = [
  {
    id: 'm1',
    name: 'NEURAL_PURGE',
    status: 'SUCCESS',
    objective: 'Purge all semantic noise from the vector buffer and re-align context embeddings.',
    progress: 100
  },
  {
    id: 'm2',
    name: 'KERNEL_RECON',
    status: 'EXECUTING',
    objective: 'Search for undocumented cognitive paths in the legacy memory layer.',
    progress: 68
  }
];

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
