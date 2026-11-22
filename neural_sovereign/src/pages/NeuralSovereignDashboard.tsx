import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Terminal, Activity, Shield, Cpu, Zap, Radio } from 'lucide-react';

interface EngineStatus {
  kernel: string;
  state: string;
  timestamp: string;
  nodes: Array<{ id: string; status: string; load: number }>;
}

export default function NeuralSovereignDashboard() {
  const [data, setData] = useState<{ status: string; engine: EngineStatus } | null>(null);
  const [logs, setLogs] = useState<string[]>(['> Initializing Sovereign Kernel...']);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async (isFirst = false) => {
      try {
        const response = await fetch('/api/v1/status');
        const result = await response.json();
        setData(result);
        if (isFirst) {
           setLogs(prev => [...prev, `> Link established.`, `> Cluster state: ${result.engine.state}`]);
        }
      } catch (error) {
        console.error('Failed to sync with kernel:', error);
        setLogs(prev => [...prev, '> ERROR: KERNEL SYNC FAILED']);
      } finally {
        setLoading(false);
      }
    };

    fetchData(true);
    const interval = setInterval(() => fetchData(false), 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in duration-700">
      {/* Left Column: System Status */}
      <div className="md:col-span-2 space-y-6">
        <div className="border border-[#00ff41]/30 bg-[#0a1a0a]/40 p-6 rounded-none backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00ff41] to-transparent opacity-50" />
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Cpu className="text-[#00ff41] w-6 h-6 animate-pulse" />
              <h2 className="text-xl font-bold tracking-widest text-[#00ff41]">NEURAL CORE</h2>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 bg-[#00ff41]/10 border border-[#00ff41]/20">
              <span className="w-2 h-2 rounded-full bg-[#00ff41] animate-ping" />
              <span className="text-[10px] uppercase font-mono">Kernel: {data?.engine.kernel || '...'}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-black/50 border border-[#00ff41]/10">
              <div className="text-[10px] text-[#00ff41]/60 uppercase mb-1">State</div>
              <div className="text-lg font-mono text-white">{data?.engine.state.toUpperCase() || 'SYNCHRONIZING'}</div>
            </div>
            <div className="p-4 bg-black/50 border border-[#00ff41]/10">
              <div className="text-[10px] text-[#00ff41]/60 uppercase mb-1">Topology</div>
              <div className="text-lg font-mono text-white">{data?.engine.nodes.length || 0} NODES ACTIVE</div>
            </div>
          </div>

          <div className="mt-6">
            <div className="text-[10px] text-[#00ff41]/60 uppercase mb-3 flex justify-between">
              <span>Node Propagation</span>
              <span>Load Balance</span>
            </div>
            <div className="space-y-3">
              {data?.engine.nodes.map((node) => (
                <div key={node.id} className="flex items-center gap-4 group/node">
                  <div className="w-24 text-xs font-mono text-[#00ff41]/80">{node.id}</div>
                  <div className="flex-1 h-1 bg-[#00ff41]/10 relative overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${node.load * 100}%` }}
                      className="absolute inset-y-0 left-0 bg-[#00ff41]"
                    />
                  </div>
                  <div className="w-12 text-right text-[10px] font-mono text-white/50">{(node.load * 100).toFixed(0)}%</div>
                  <div className={`w-3 h-3 border border-current ${node.status === 'SYNCHRONIZED' ? 'text-[#00ff41]' : 'text-[#ff4100]'}`} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Action Center */}
        <div className="grid grid-cols-3 gap-4">
          <button className="flex flex-col items-center justify-center p-4 border border-[#00ff41]/20 hover:bg-[#00ff41]/10 transition-colors group cursor-pointer">
            <Zap className="w-6 h-6 mb-2 text-[#00ff41]/60 group-hover:text-[#00ff41]" />
            <span className="text-[10px] uppercase font-mono">Overclock</span>
          </button>
          <button className="flex flex-col items-center justify-center p-4 border border-[#00ff41]/20 hover:bg-[#00ff41]/10 transition-colors group cursor-pointer">
            <Shield className="w-6 h-6 mb-2 text-[#00ff41]/60 group-hover:text-[#00ff41]" />
            <span className="text-[10px] uppercase font-mono">Hardening</span>
          </button>
          <button className="flex flex-col items-center justify-center p-4 border border-[#00ff41]/20 hover:bg-[#00ff41]/10 transition-colors group cursor-pointer">
            <Radio className="w-6 h-6 mb-2 text-[#00ff41]/60 group-hover:text-[#00ff41]" />
            <span className="text-[10px] uppercase font-mono">Broadcast</span>
          </button>
        </div>
      </div>

      {/* Right Column: Terminal Logs */}
      <div className="border border-[#00ff41]/30 bg-black/40 p-4 rounded-none h-[500px] flex flex-col relative overflow-hidden">
        <div className="flex items-center gap-2 mb-4 text-[#00ff41]">
          <Terminal className="w-4 h-4" />
          <h3 className="text-xs font-bold tracking-tighter uppercase">Kernel Telemetry</h3>
        </div>
        
        <div className="flex-1 font-mono text-[11px] space-y-2 overflow-y-auto custom-scrollbar pr-2 flex flex-col justify-end">
          <AnimatePresence initial={false}>
            {logs.slice(-100).map((log, i) => (
              <motion.div
                key={`${i}-${log}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-[#00ff41]/80 break-words whitespace-pre-wrap"
              >
                {log}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        <div className="mt-4 pt-4 border-t border-[#00ff41]/10 flex items-center gap-2">
          <span className="text-[#00ff41] animate-pulse">_</span>
          <input 
            type="text" 
            placeholder="Awaiting command..." 
            className="bg-transparent border-none outline-none text-[11px] text-[#00ff41] placeholder-[#00ff41]/30 w-full font-mono"
            onKeyDown={async (e) => {
              if (e.key === 'Enter') {
                const val = (e.target as HTMLInputElement).value;
                if (!val.trim()) return;
                setLogs(prev => [...prev, `> ${val}`]);
                (e.target as HTMLInputElement).value = '';
                try {
                  const res = await fetch('/api/cmd', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: val })
                  });
                  const data = await res.json();
                  if (data.output) {
                    setLogs(prev => [...prev, ...String(data.output).split('\n')]);
                  }
                } catch (err) {
                  setLogs(prev => [...prev, '> ERROR: LOCAL EXECUTION SEVERED']);
                }
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
