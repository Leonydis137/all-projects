import { useState, useEffect } from 'react';
import { Wrench, Shield, Zap, Search, Hammer, Boxes, Activity, ExternalLink, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';

export default function ToolManager() {
  const { tools, setTools } = useStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch('/api/tools');
        if (response.ok) {
          const systemTools = await response.json();
          setTools(systemTools);
        }
      } catch (err) {
        console.error('Failed to fetch tools:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTools();
  }, [setTools]);

  return (
    <div className="p-8 h-full bg-bg-dark overflow-y-auto neural-grid">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 border border-neon-cyan/20 bg-neon-cyan/5 cyber-panel flex items-center justify-center">
              <Wrench className="w-7 h-7 text-neon-cyan shadow-[0_0_10px_#00e5ff]" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="Tool_Orchestration">Tool_Orchestration</h1>
              <div className="flex items-center gap-2 mt-1">
                 <span className="w-2 h-2 bg-neon-cyan animate-pulse rounded-full" />
                 <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">External Primitive Execution Interface</p>
              </div>
            </div>
          </div>
          
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
            <input placeholder="SEARCH_TOOL_PRIMITIVES..." className="w-64 bg-black/40 border border-white/10 p-3 pl-10 text-[10px] font-mono text-white placeholder-white/10 focus:border-neon-cyan/50 outline-none transition-colors" />
          </div>
        </div>

        {loading ? (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
              <RefreshCw className="w-12 h-12 text-neon-cyan animate-spin" />
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.5em]">Scanning Engine Plugins...</div>
            </div>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-8 mb-12">
          {tools.map((tool, i) => (
            <motion.div 
              key={tool.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="p-8 border border-white/5 cyber-panel bg-panel-dark/60 relative group hover:bg-panel-dark/80 transition-all"
            >
              <div className="flex justify-between items-start mb-6">
                 <div className="flex items-center gap-4">
                    <div className="p-3 border border-white/10 cyber-panel bg-black/40 group-hover:border-neon-cyan/50 transition-colors">
                       <Boxes className="w-6 h-6 text-white/40 group-hover:text-neon-cyan" />
                    </div>
                    <div>
                       <h3 className="text-lg font-black text-white uppercase tracking-tighter">{tool.name}</h3>
                       <div className="flex items-center gap-2">
                          <span className="text-[9px] font-mono text-white/20 uppercase tracking-widest">{tool.type}</span>
                          <div className={cn(
                            "px-2 py-0.5 text-[8px] font-black uppercase text-center min-w-[70px]",
                            tool.status === 'READY' ? "bg-neon-green/10 text-neon-green border border-neon-green/20" : 
                            tool.status === 'EXECUTING' ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 animate-pulse" : "bg-white/5 text-white/30 border border-white/10"
                          )}>
                             {tool.status}
                          </div>
                       </div>
                    </div>
                 </div>
                 <button className="text-white/20 hover:text-white transition-colors">
                    <ExternalLink className="w-4 h-4" />
                 </button>
              </div>

              <p className="text-xs text-white/60 font-display leading-relaxed mb-8 h-12 overflow-hidden">
                {tool.description}
              </p>

              <div className="flex items-center justify-between border-t border-white/5 pt-6">
                 <div className="flex flex-col gap-1">
                    <span className="text-[8px] text-white/20 uppercase font-mono tracking-widest">Last_Execution</span>
                    <span className="text-[10px] text-white/60 font-mono uppercase">{tool.lastUsed}</span>
                 </div>
                 <div className="flex items-center gap-4">
                    <div className="flex flex-col items-end gap-1">
                       <span className="text-[8px] text-white/20 uppercase font-mono tracking-widest">Permissions</span>
                       <div className="flex gap-1">
                          <Shield className="w-2.5 h-2.5 text-neon-green opacity-50" />
                          <Activity className="w-2.5 h-2.5 text-neon-cyan opacity-50" />
                       </div>
                    </div>
                    <button className={cn(
                      "px-6 py-2 text-[10px] font-black uppercase tracking-widest transition-all",
                      tool.status === 'READY' ? "bg-white/5 border border-white/10 text-white hover:bg-neon-cyan hover:text-black hover:border-neon-cyan" : "bg-white/2"
                    )}>
                      Execute
                    </button>
                 </div>
              </div>

              {/* Decorative side accent */}
              <div className="absolute top-0 right-0 h-full w-[1px] bg-gradient-to-b from-transparent via-white/5 to-transparent shadow-[0_0_10px_white/5]" />
            </motion.div>
          ))}
        </div>
        )}

        <div className="p-12 border border-white/5 border-dashed bg-white/[0.01] text-center">
           <div className="max-w-md mx-auto">
              <Hammer className="w-12 h-12 text-white/5 mx-auto mb-6" />
              <h3 className="text-sm font-bold text-white/40 uppercase mb-4">Integrate_Neural_Tool</h3>
              <p className="text-[10px] text-white/20 uppercase leading-relaxed mb-8">
                Connect external specialized intelligence primitives via the Multi-Agent Computation Protocol (MCP).
              </p>
              <button className="px-12 py-3 bg-white/5 border border-white/10 text-white/60 text-[10px] font-black uppercase tracking-widest hover:bg-white hover:text-black transition-all">
                Connect_MCP_Relay
              </button>
           </div>
        </div>
      </div>
    </div>
  );
}
