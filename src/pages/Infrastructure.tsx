import { Zap, Cpu, Server, Network, BarChart3, Database, Globe, ArrowUpRight, ShieldAlert } from 'lucide-react';
import { motion } from 'motion/react';
import { Sparkline } from '../components/Sparkline';
import { useState, useEffect } from 'react';

export default function Infrastructure() {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [nodeHistory, setNodeHistory] = useState<Record<string, number[]>>({});

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/v1/status');
        if (res.ok) {
          const data = await res.json();
          setTelemetry(data);
          setNodeHistory(prev => {
             const next: Record<string, number[]> = { ...prev };
             data.engine.nodes.forEach((node: any) => {
                const arr = next[node.id] || [];
                next[node.id] = [...arr.slice(-19), node.load * 100];
             });
             return next;
          });
        }
      } catch (err) {
        console.error("Failed to fetch infra telemetry:", err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const systems = telemetry ? telemetry.engine.nodes.slice(0, 4).map((node: any, i: number) => ({
    name: node.id,
    status: node.status,
    load: node.load * 100,
    health: 100 - (node.load * 10),
    icon: Cpu,
    color: i % 2 === 0 ? 'var(--color-neon-cyan)' : 'var(--color-neon-purple)',
    data: (nodeHistory[node.id] || []).length > 0 ? nodeHistory[node.id] : [0]
  })) : [];

  return (
    <div className="p-4 md:p-8 h-full bg-bg-dark overflow-y-auto neural-grid custom-scrollbar">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 cyber-panel flex items-center justify-center bg-neon-cyan/5 border-neon-cyan/20">
              <Zap className="w-7 h-7 text-neon-cyan text-glow-cyan" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="Infra_Architecture">
                Infra_Architecture
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">
                  Kernel: {telemetry?.engine.kernel || 'Loding...'} // {telemetry?.engine.hostname} // {telemetry?.engine.platform}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-8 px-6 py-3 bg-panel-dark/40 border border-white/5 cyber-panel">
            <div className="text-right">
              <div className="text-[9px] text-white/30 uppercase font-mono tracking-widest mb-1">CPU Load</div>
              <div className="text-xl font-black text-white font-mono">
                {((telemetry?.engine.metrics.cpuLoad || 0) * 100).toFixed(1)} <span className="text-neon-cyan text-xs">%</span>
              </div>
            </div>
            <div className="w-[1px] h-10 bg-white/10" />
            <div className="text-right">
              <div className="text-[9px] text-white/30 uppercase font-mono tracking-widest mb-1">Memory Usage</div>
              <div className="text-xl font-black text-neon-green font-mono">
                {((telemetry?.engine.metrics.memoryUsage || 0) * 100).toFixed(1)} <span className="text-xs">%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-4">
          {/* Main Monitor */}
          <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            {systems.map((system, i) => (
              <motion.div 
                key={system.name}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className="group cyber-panel p-5 space-y-4 hover:border-white/20 transition-all cursor-default"
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/5 border border-white/10 group-hover:border-neon-cyan/50 transition-colors">
                      <system.icon className="w-4 h-4 text-white/60 group-hover:text-neon-cyan transition-colors" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">{system.name}</h3>
                      <p className="text-[9px] text-white/30 font-mono italic">UID: {system.name.slice(0, 4).toUpperCase()}_0x{i}F</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-[8px] uppercase tracking-widest text-white/30 mb-1">Status</span>
                    <span className="text-[9px] px-1.5 py-0.5 border border-white/10 bg-white/5 font-black uppercase tracking-tighter" style={{ color: system.color }}>
                      {system.status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-[9px] uppercase text-white/40">
                      <span>Node_Load</span>
                      <span>{system.load.toFixed(1)}%</span>
                    </div>
                    <div className="h-1 bg-white/5 relative overflow-hidden">
                      <motion.div 
                        className="h-full bg-white transition-all duration-1000"
                        style={{ width: `${system.load}%`, backgroundColor: system.color }}
                      />
                    </div>
                  </div>
                  <div className="flex items-end justify-end">
                    <Sparkline data={system.data} color={system.color} width={80} height={25} />
                  </div>
                </div>

                <div className="flex justify-between items-center pt-2 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: system.color }} />
                    <span className="text-[8px] text-white/40 uppercase">Resilience: {system.health}%</span>
                  </div>
                  <ArrowUpRight className="w-3 h-3 text-white/20" />
                </div>
              </motion.div>
            ))}
          </div>

          {/* Right Statistics Panel */}
          <div className="lg:col-span-4 space-y-4">
            <div className="cyber-panel p-6 bg-neon-cyan/5 border-neon-cyan/20 h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-6">
                  <Globe className="w-4 h-4 text-neon-cyan" />
                  <h3 className="text-xs font-black uppercase tracking-widest">Global_State_Probe</h3>
                </div>
                
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] text-white/40 uppercase">Neural_Link</span>
                      <span className="text-xs font-mono text-neon-cyan">OK</span>
                    </div>
                    <div className="h-px bg-gradient-to-r from-neon-cyan via-white/20 to-transparent" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] text-white/40 uppercase">Encryption_Mesh</span>
                      <span className="text-xs font-mono text-white">AES-4096</span>
                    </div>
                    <div className="h-px bg-gradient-to-r from-neon-purple via-white/20 to-transparent" />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] text-white/40 uppercase">Uptime_Pulse</span>
                      <span className="text-xs font-mono text-white tracking-widest">124:43:12</span>
                    </div>
                    <div className="h-px bg-gradient-to-r from-neon-green via-white/20 to-transparent" />
                  </div>
                </div>
              </div>

              <div className="mt-8 p-4 bg-black/40 border border-white/5 text-[9px] font-mono text-white/50 leading-relaxed uppercase italic">
                &gt; System entropy is within acceptable parameters. No anomalies detected in the quantum buffer.
              </div>
            </div>
          </div>

          {/* Bottom Large Visualization */}
          <div className="lg:col-span-12 cyber-panel p-6 bg-panel-dark/40 overflow-hidden relative">
            <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
              <Network className="w-48 h-48" />
            </div>
            
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-4 h-4 text-neon-purple" />
                <h3 className="text-xs font-black uppercase tracking-widest text-white">Cluster_Pulse_Visualization</h3>
              </div>
              <div className="flex items-center gap-4 text-[9px] uppercase font-mono">
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-neon-cyan" /> Master</span>
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-neon-purple" /> Worker</span>
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-white/20" /> Idle</span>
              </div>
            </div>

            <div className="h-32 flex items-end gap-1 px-2">
              {Array.from({length: 80}).map((_, i) => (
                <motion.div 
                   key={i}
                   initial={{ height: 10 }}
                   animate={{ height: [`${20 + Math.random() * 60}%`, `${10 + Math.random() * 40}%`, `${40 + Math.random() * 50}%`] }}
                   transition={{ repeat: Infinity, duration: 2 + Math.random() * 2, ease: 'easeInOut' }}
                   className={`flex-1 ${i % 3 === 0 ? 'bg-neon-cyan/40' : i % 7 === 0 ? 'bg-neon-purple/40' : 'bg-white/5'} hover:brightness-150 transition-all`}
                />
              ))}
            </div>
          </div>
        </div>
        
        {/* Footer Alerts */}
        <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
          {[
            { msg: 'Security firewall update deployed to all edges', icon: ShieldAlert, color: 'text-neon-cyan' },
            { msg: 'Vector registry resync complete (0.12ms drift)', icon: Database, color: 'text-neon-green' },
            { msg: 'Anomalous traffic detected in Ghost_Protocol (Suppressed)', icon: Zap, color: 'text-neon-pink' },
          ].map((alert, i) => (
            <div key={i} className="flex-shrink-0 flex items-center gap-3 px-4 py-2 border border-white/5 bg-panel-dark/40 cyber-panel">
              <alert.icon className={`w-3 h-3 ${alert.color}`} />
              <span className="text-[10px] text-white/50 uppercase font-mono whitespace-nowrap tracking-wider">{alert.msg}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
