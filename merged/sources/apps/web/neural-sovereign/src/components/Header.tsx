import { useStore } from '../store/useStore';
import { formatUptime, cn } from '../lib/utils';
import { Activity, ShieldCheck, Zap, Server, LogOut } from 'lucide-react';
import { motion } from 'motion/react';
import { signOutUser } from '../lib/firebase';

export default function Header() {
  const { uptime, systemMetrics, user, selectedNodeId } = useStore();

  return (
    <header className={cn(
      "h-16 border-b border-white/5 bg-bg-dark/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30 transition-all duration-300 w-full"
    )}>
      <div className="flex items-center gap-8 pointer-events-auto">
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.3em] font-black text-white/30 mb-0.5">
            <Server className="w-3 h-3" />
            System_Metric :: {systemMetrics?.platform || 'NEURAL_CORE'}
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-white/60 uppercase font-display">CPU:</span>
              <span className="text-xs font-mono font-bold text-neon-cyan tracking-widest">{systemMetrics?.cpu || '0.00'}%</span>
            </div>
            <div className="w-[1px] h-3 bg-white/10" />
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-white/60 uppercase font-display">MEM:</span>
              <span className="text-xs font-mono font-bold text-neon-purple tracking-widest">{systemMetrics?.memory || '0.00'}%</span>
            </div>
            <div className="w-[1px] h-3 bg-white/10" />
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-white/60 uppercase font-display">Uptime:</span>
              <span className="text-xs font-mono font-bold text-white tracking-widest">{formatUptime(systemMetrics?.uptime || uptime)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 justify-center px-12 pointer-events-none">
        
      </div>

      <div className="flex items-center gap-6 pointer-events-auto">
        <div className="flex items-center gap-4 border-l border-white/5 pl-6">
          <div className="flex flex-col items-end">
            <span className="text-[8px] text-white/30 uppercase tracking-[0.2em] mb-1">IdentityVerified</span>
            <span className="text-[10px] font-mono text-neon-green tracking-widest uppercase truncate max-w-[120px]">
              {user?.email || 'OFFLINE'}
            </span>
          </div>
          <button 
            onClick={() => signOutUser()}
            className="w-10 h-10 border border-white/10 flex items-center justify-center relative group cursor-pointer hover:border-neon-red transition-all ml-2"
            title="Terminate Session"
          >
            <LogOut className="w-4 h-4 text-white/40 group-hover:text-neon-red group-hover:animate-pulse transition-colors" />
          </button>
          <div className="w-10 h-10 border border-white/10 p-0.5 relative group cursor-pointer hover:border-neon-cyan transition-all">
            {user?.photoURL ? (
              <img src={user.photoURL} alt={user.displayName || 'User'} className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all" referrerPolicy="no-referrer" />
            ) : (
              <ShieldCheck className="w-full h-full p-2 text-white/40 group-hover:text-neon-cyan transition-colors" />
            )}
            <div className="absolute top-0 right-0 w-1.5 h-1.5 bg-neon-green rounded-full shadow-[0_0_5px_#00ff9d]" />
          </div>
        </div>
      </div>
    </header>
  );
}
