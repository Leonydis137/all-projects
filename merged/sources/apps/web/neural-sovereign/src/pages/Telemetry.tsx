import { useState, useEffect } from 'react';
import { Activity, Zap, Cpu, Network, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { motion } from 'motion/react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';

export default function Telemetry() {
  const [history, setHistory] = useState<number[]>([]);
  const { systemMetrics, nodes } = useStore();

  useEffect(() => {
    if (systemMetrics) {
      setHistory(prev => {
        const next = [...prev, parseFloat(systemMetrics.cpu)];
        return next.length > 40 ? next.slice(-40) : next;
      });
    }
  }, [systemMetrics]);

  const metrics = [
    { label: 'Compute_Load', value: `${systemMetrics?.cpu || '0.00'}%`, trend: 'up', color: 'text-neon-cyan' },
    { label: 'Memory_Usage', value: `${systemMetrics?.memory || '0.00'}%`, trend: 'down', color: 'text-neon-green' },
    { label: 'Uptime', value: `${((systemMetrics?.uptime || 0) / 3600).toFixed(1)}h`, trend: 'up', color: 'text-neon-purple' },
    { label: 'OS_Platform', value: systemMetrics?.platform || 'linux', trend: 'down', color: 'text-neon-pink' },
  ];

  const paddedHistory = Array.from({ length: 40 }, (_, i) => history[i] || 0);

  return (
    <div className="p-8 h-full bg-bg-dark overflow-y-auto neural-grid">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-12">
          <div className="w-12 h-12 border border-neon-cyan/20 bg-neon-cyan/5 flex items-center justify-center">
            <Activity className="w-6 h-6 text-neon-cyan shadow-[0_0_10px_#00e5ff]" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tighter uppercase text-white">Kernel_Telemetry</h1>
            <p className="text-[10px] text-white/30 tracking-[0.4em] uppercase font-mono">Real-time Cognitive Performance Index</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {metrics.map((m, i) => (
            <motion.div 
              key={m.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className="p-6 border border-white/5 bg-panel-dark/60 relative overflow-hidden"
            >
              <div className="text-[8px] text-white/30 uppercase tracking-widest mb-2 font-mono">{m.label}</div>
              <div className={cn("text-2xl font-black tracking-tighter mb-4", m.color)}>{m.value}</div>
              <div className="flex items-center gap-2">
                {m.trend === 'up' ? <ArrowUpRight className="w-3 h-3 text-neon-green" /> : <ArrowDownRight className="w-3 h-3 text-neon-red" />}
                <span className="text-[9px] text-white/20 uppercase font-mono">VS_PREVIOUS_CYCLE</span>
              </div>
              <div className="absolute top-0 right-0 p-1">
                <div className="w-1 h-1 rounded-full bg-white/10" />
              </div>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          <div className="p-8 border border-white/5 bg-panel-dark/40 relative">
             <h3 className="text-sm font-bold text-white uppercase mb-8 flex items-center gap-2">
               <Zap className="w-4 h-4 text-neon-cyan" />
               Neural_Throughput_Delta
             </h3>
             <div className="h-64 flex items-end justify-between gap-[2px]">
               {paddedHistory.map((val, i) => (
                 <motion.div 
                   key={i}
                   initial={{ height: 20 }}
                   animate={{ height: `${Math.max(20, val)}%` }}
                   transition={{ duration: 0.5 }}
                   className="flex-1 bg-neon-cyan/20 border-t border-neon-cyan/40"
                 />
               ))}
             </div>
             <div className="absolute top-1/2 left-0 w-full h-[1px] bg-white/[0.02] border-t border-dashed border-white/5" />
          </div>

          <div className="p-8 border border-white/5 bg-panel-dark/40">
             <h3 className="text-sm font-bold text-white uppercase mb-8 flex items-center gap-2">
               <Network className="w-4 h-4 text-neon-purple" />
               Subsystem_Health
             </h3>
             <div className="space-y-6">
                {nodes.slice(0, 4).map((sys) => (
                  <div key={sys.id} className="space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-mono">
                      <span className="text-white/40 uppercase">{sys.name}</span>
                      <span className="text-neon-green">{sys.health.toFixed(2)}%</span>
                    </div>
                    <div className="h-1 bg-white/5 w-full relative">
                       <motion.div 
                         initial={{ width: 0 }}
                         animate={{ width: `${sys.health}%` }}
                         className="absolute inset-y-0 left-0 bg-neon-purple/50 shadow-[0_0_10px_#a855f7]"
                       />
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </div>

        <div className="p-8 border border-white/5 bg-panel-dark/40">
           <div className="flex items-center justify-between mb-8">
              <h3 className="text-sm font-bold text-white uppercase flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-neon-cyan" />
                Resource_Distribution
              </h3>
              <div className="text-[10px] text-white/30 font-mono">SNAPSHOT_ID: 0x4421A</div>
           </div>
           <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {[
                { label: 'CPU_POWER', value: systemMetrics?.cpu || '0.00', color: 'text-neon-cyan' },
                { label: 'MEM_BUFFER', value: systemMetrics?.memory || '0.00', color: 'text-neon-purple' },
                { label: 'DISK_IO', value: (parseFloat(systemMetrics?.cpu || '0') * 0.4).toFixed(1), color: 'text-neon-pink' },
                { label: 'NET_STACK', value: (parseFloat(systemMetrics?.memory || '0') * 0.1).toFixed(1), color: 'text-neon-green' },
              ].map(stat => (
                <div key={stat.label} className="text-center">
                  <div className={cn("text-3xl font-black tracking-tighter", stat.color)}>{stat.value}%</div>
                  <div className="text-[9px] text-white/20 uppercase tracking-[0.2em] font-mono mt-2">{stat.label}</div>
                </div>
              ))}
           </div>
        </div>
      </div>
    </div>
  );
}
