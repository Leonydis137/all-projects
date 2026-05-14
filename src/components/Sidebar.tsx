import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';
import { signOutUser } from '../lib/firebase';
import { 
  ShieldCheck, 
  Settings, 
  Users, 
  Database, 
  Lock, 
  Play, 
  Terminal as TerminalIcon, 
  Activity,
  Zap,
  Globe,
  Wrench,
  LogOut
} from 'lucide-react';
import { motion } from 'motion/react';

export default function Sidebar() {
  const nodes = useStore(state => state.nodes);
  const isKernelActive = useStore(state => state.isKernelActive);
  const missions = useStore(state => state.missions);
  const activeView = useStore(state => state.activeView);
  const setView = useStore(state => state.setView);
  const user = useStore(state => state.user);
  
  const menuItems = [
    { id: 'overview', icon: Globe, label: 'Overview' },
    { id: 'terminal', icon: TerminalIcon, label: 'Terminal' },
    { id: 'telemetry', icon: Activity, label: 'Telemetry' },
    { id: 'agents', icon: Users, label: 'Agents' },
    { id: 'memory', icon: Database, label: 'Memory' },
    { id: 'infrastructure', icon: Zap, label: 'Infrastructure' },
    { id: 'tools', icon: Wrench, label: 'Tools' },
    { id: 'security', icon: Lock, label: 'Security' },
    { id: 'missions', icon: Play, label: 'Missions' },
    { id: 'logs', icon: TerminalIcon, label: 'Logs' },
    { id: 'config', icon: Settings, label: 'Config' },
  ] as const;

  return (
    <aside className="w-[198px] h-screen flex flex-col border-r border-white/5 bg-panel-dark relative z-[70] transition-all duration-500 shadow-[20px_0_50px_rgba(0,0,0,0.5)]">
      {/* Animated Gradient Pulse Border */}
      <div className="absolute right-0 top-0 w-[1px] h-full bg-gradient-to-b from-transparent via-neon-cyan/20 to-transparent animate-pulse" />

      {/* Logo Area */}
      <div className="p-6 border-b border-white/5 flex flex-col gap-1 cursor-pointer group hover:bg-white/[0.02] transition-colors" onClick={() => setView('overview')}>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-neon-cyan animate-pulse shadow-[0_0_10px_#00e5ff]" />
          <h1 className="text-sm font-black tracking-tighter text-white group-hover:text-neon-cyan transition-colors">NEURAL_OS</h1>
        </div>
        <span className="text-[9px] text-white/30 font-mono uppercase tracking-[0.2em] group-hover:text-white/50 transition-colors">V14.Sovereign</span>
      </div>

      {/* Kernel Status */}
      <div className="p-4 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] uppercase tracking-wider text-white/60">Kernel State</span>
          <span className={cn(
            "text-[9px] uppercase font-bold px-1.5 py-0.5 rounded-sm",
            isKernelActive ? "bg-neon-green/10 text-neon-green" : "bg-neon-red/10 text-neon-red"
          )}>
            {isKernelActive ? 'Active' : 'Offline'}
          </span>
        </div>
        <div className="h-1 bg-white/5 w-full relative overflow-hidden">
          {isKernelActive && (
            <motion.div 
              initial={{ x: '-100%' }}
              animate={{ x: '100%' }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-0 bg-gradient-to-r from-transparent via-neon-cyan to-transparent w-1/2"
            />
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 custom-scrollbar">
        <div className="px-4 mb-2 text-[9px] uppercase tracking-widest text-white/30">Navigation</div>
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => {
              console.log('[Sidebar] Navigation triggered:', item.id);
              setView(item.id);
            }}
            className={cn(
              "w-full flex items-center gap-3 px-6 py-3 transition-all group relative overflow-hidden z-10",
              activeView === item.id ? "text-neon-cyan bg-white/[0.1] border-r-2 border-neon-cyan" : "text-white/40 hover:text-white hover:bg-white/[0.05]"
            )}
          >
            <item.icon className={cn(
              "w-4 h-4 transition-transform",
              activeView === item.id ? "scale-110" : "group-hover:scale-110"
            )} />
            <span className="text-[11px] font-display uppercase tracking-wider font-medium">{item.label}</span>
            <div className={cn(
              "absolute left-0 top-1/2 -translate-y-1/2 w-0.5 bg-neon-cyan transition-all duration-300",
              activeView === item.id ? "h-6" : "h-0 group-hover:h-3"
            )} />
          </button>
        ))}

        <div className="px-4 mt-6 mb-2 text-[9px] uppercase tracking-widest text-white/30">Active Agents</div>
        <div className="px-6 space-y-2 mb-6">
          {nodes.filter(n => n.type === 'CORE' || n.type === 'ORCHESTRATION').map(node => (
            <div key={node.id} className="flex items-center justify-between group cursor-pointer">
              <span className="text-[10px] font-mono text-white/40 group-hover:text-white/80 transition-colors uppercase">{node.id}</span>
              <div className="w-1 h-1 rounded-full bg-neon-green animate-pulse shadow-[0_0_5px_#00ff9d]" />
            </div>
          ))}
        </div>

        <div className="px-4 mt-6 mb-2 text-[9px] uppercase tracking-widest text-white/30">Mission Control</div>
        <div className="px-6 space-y-4">
          {missions.map(mission => (
            <div key={mission.id} className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-[10px] uppercase font-bold text-white/80">
                <span>{mission.name}</span>
                <span className={cn(
                  "text-[8px] px-1 bg-white/5",
                  mission.status === 'EXECUTING' ? "text-neon-cyan" : "text-white/40"
                )}>{mission.status}</span>
              </div>
              <div className="h-1 bg-white/5 w-full relative">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${mission.progress}%` }}
                  className="absolute inset-y-0 left-0 bg-neon-cyan"
                />
              </div>
              <span className="text-[8px] text-white/30 truncate">{mission.objective}</span>
            </div>
          ))}
        </div>
      </nav>

      {/* System Quick Stats */}
      <div className="p-4 border-t border-white/5 bg-black/40">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-[9px] uppercase tracking-wider text-white/40">
              <span>Memory</span>
              <span className="text-neon-green">68%</span>
            </div>
            <div className="h-0.5 bg-white/5 w-full">
              <div className="h-full bg-neon-green w-[68%]" />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-[9px] uppercase tracking-wider text-white/40">
              <span>Entropy</span>
              <span className="text-neon-pink">0.0004</span>
            </div>
            <div className="h-0.5 bg-white/5 w-full">
              <div className="h-full bg-neon-pink w-[12%]" />
            </div>
          </div>
        </div>
      </div>

      {user && (
        <div className="p-4 border-t border-white/5">
          <button 
            onClick={() => {
              console.log('[Sidebar] Terminating session...');
              signOutUser();
            }}
            className="w-full flex items-center gap-3 px-4 py-3 text-white/40 hover:text-neon-red hover:bg-neon-red/5 transition-all group border border-transparent hover:border-neon-red/20"
          >
            <LogOut className="w-4 h-4 group-hover:animate-pulse" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em]">Terminate_Session</span>
          </button>
        </div>
      )}
    </aside>
  );
}
