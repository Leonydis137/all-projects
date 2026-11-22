import { useStore, TelemetryEvent } from '../store/useStore';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Terminal as TerminalIcon, 
  Search, 
  Trash2, 
  Download, 
  Play, 
  Pause,
  AlertTriangle,
  Info,
  ShieldAlert,
  ChevronRight
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useState, useEffect, useRef } from 'react';

export default function LogExplorer() {
  const logs = useStore(state => state.logs);
  const [filter, setFilter] = useState('');
  const [isLive, setIsLive] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter(log => 
    log.message.toLowerCase().includes(filter.toLowerCase()) ||
    log.source.toLowerCase().includes(filter.toLowerCase())
  );

  useEffect(() => {
    if (isLive) {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isLive]);

  return (
    <div className="flex-1 flex flex-col bg-bg-dark h-full neural-grid">
      {/* Control Bar */}
      <div className="px-8 py-6 border-b border-white/5 bg-panel-dark/40 flex flex-col md:flex-row justify-between items-center gap-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-cyan/20 to-transparent" />
        
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="p-2 border border-neon-cyan/20 bg-neon-cyan/5">
               <TerminalIcon className="w-5 h-5 text-neon-cyan shadow-[0_0_8px_#00e5ff]" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tighter text-white uppercase">Neural_Telemetry</h1>
              <p className="text-[9px] text-white/30 uppercase tracking-[0.2em] font-mono">Kernel Event Stream</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10">
            <motion.div 
              animate={isLive ? { opacity: [1, 0.4, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
              className={cn(
                "w-2 h-2 rounded-full",
                isLive ? "bg-neon-green shadow-[0_0_8px_#00ff9d]" : "bg-white/20"
              )} 
            />
            <span className="text-[10px] uppercase font-bold font-mono text-white/60 tracking-widest">{isLive ? 'Live_Feed' : 'Static_Buffer'}</span>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto">
          <div className="relative flex-1 md:w-80 group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20 group-hover:text-neon-cyan transition-colors" />
            <input 
              type="text" 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="SEARCH_KERNEL_LOGS..."
              className="w-full bg-black/60 border border-white/10 p-3 pl-10 text-[11px] font-mono text-white focus:outline-none focus:border-neon-cyan transition-all placeholder-white/10"
            />
          </div>
          <div className="flex items-center">
            <button 
              onClick={() => setIsLive(!isLive)}
              className="p-3 bg-white/5 border border-white/10 text-white/40 hover:text-white hover:border-white transition-all flex items-center justify-center"
              title={isLive ? "Pause Stream" : "Resume Stream"}
            >
              {isLive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button className="p-3 bg-white/5 border border-white/10 border-l-0 text-white/40 hover:text-white hover:border-white transition-all flex items-center justify-center">
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Log Feed */}
      <div className="flex-1 overflow-y-auto p-8 font-mono text-[11px] selection:bg-neon-cyan selection:text-black custom-scrollbar bg-black/20">
        <div className="max-w-7xl mx-auto space-y-1">
          <div className="flex items-center gap-4 px-6 py-3 text-white/20 border-b border-white/5 mb-6 text-[9px] uppercase tracking-[0.3em] font-black">
            <span className="w-20">Source</span>
            <span className="w-32">Timestamp</span>
            <span className="flex-1">Event_Manifest</span>
            <span className="w-24 text-right">PRIMITIVE_ID</span>
          </div>

          <AnimatePresence initial={false}>
            {filteredLogs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={cn(
                  "flex items-start gap-4 px-6 py-2.5 transition-all group border-l-2 relative overflow-hidden",
                  log.level === 'error' ? "border-neon-red bg-neon-red/5" : 
                  log.level === 'warn' ? "border-neon-orange bg-neon-orange/5" : "border-transparent hover:bg-white/[0.02]"
                )}
              >
                <div className={cn(
                  "w-20 font-black tracking-tighter truncate text-[10px]",
                  log.level === 'error' ? "text-neon-red" : 
                  log.level === 'warn' ? "text-neon-orange" : "text-neon-cyan"
                )}>
                  {log.source}
                </div>
                <div className="w-32 text-white/20 font-light">{new Date(log.timestamp).toLocaleTimeString()}</div>
                <div className="flex-1 flex items-center gap-3 text-white/70 group-hover:text-white transition-colors">
                  {log.level === 'error' && <ShieldAlert className="w-3.5 h-3.5 text-neon-red shadow-[0_0_8px_#ff4444]" />}
                  {log.level === 'warn' && <AlertTriangle className="w-3.5 h-3.5 text-neon-orange" />}
                  {log.message}
                </div>
                <div className="w-24 text-right text-white/10 group-hover:text-white/30 transition-colors uppercase font-mono text-[9px] tracking-widest">
                  [0x{log.id.slice(0, 6).toUpperCase()}]
                </div>
                
                {/* Subtle scanline effect on log hover */}
                <div className="absolute inset-0 bg-gradient-to-r from-neon-cyan/0 via-neon-cyan/[0.02] to-neon-cyan/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={scrollRef} />
        </div>
      </div>

      {/* Footer Info */}
      <div className="px-8 py-4 border-t border-white/5 bg-black/60 flex justify-between items-center text-[10px] uppercase tracking-[0.2em] text-white/30 font-mono">
        <div className="flex gap-8">
          <div className="flex gap-2">
            <span className="text-white/10">AGGREGATORS:</span>
            <span className="text-neon-cyan">08_ACTIVE</span>
          </div>
          <div className="flex gap-2">
            <span className="text-white/10">EVENT_BUFFER:</span>
            <span className="text-white/30">{logs.length} TRACES</span>
          </div>
        </div>
        <div className="flex gap-6 items-center">
          <div className="flex items-center gap-2">
             <div className="w-1.5 h-1.5 rounded-full bg-neon-green/60" />
             <span>NEURAL_LINK_{isLive ? 'STABLE' : 'PAUSED'}</span>
          </div>
          <span className="text-white/10">|</span>
          <span className="text-neon-purple tracking-widest font-black">NEURAL_OS_V14::SECURE_STREAM</span>
        </div>
      </div>
    </div>
  );
}
