import { Lock, Shield, Key, Eye, EyeOff, Globe, Database, UserCheck, AlertTriangle } from 'lucide-react';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';
import { signOutUser } from '../lib/firebase';
import { cn } from '../lib/utils';
import { format } from 'date-fns';

export default function Security() {
  const [policies, setPolicies] = useState([
    { name: 'JWT_ENFORCEMENT', status: 'ACTIVE', level: 'MAX', desc: 'Cryptographic identity verification required for all primitives.' },
    { name: 'TENANT_ISOLATION', status: 'STABLE', level: 'HIGH', desc: 'Secure logical boundaries between autonomous agent memory spaces.' },
    { name: 'MCP_SANDBOXING', status: 'ACTIVE', level: 'MAX', desc: 'Restricted execution environment for external tool orchestration.' },
    { name: 'PII_REDACTION', status: 'ACTIVE', level: 'MED', desc: 'Automated filtering of sensitive neural patterns.' },
  ]);

  const [simulatedAlert, setSimulatedAlert] = useState(false);
  const [incidents, setIncidents] = useState<{ time: string, event: string, id: string }[]>([]);

  useEffect(() => {
    fetch('/api/security/incidents')
      .then(res => res.json())
      .then(data => setIncidents(data))
      .catch(console.error);
  }, []);

  const togglePolicy = (index: number) => {
    setPolicies(prev => {
      const newPolicies = [...prev];
      newPolicies[index].status = newPolicies[index].status === 'ACTIVE' ? 'PAUSED' : 
                                  newPolicies[index].status === 'STABLE' ? 'MAINTENANCE' : 
                                  newPolicies[index].status === 'PAUSED' ? 'ACTIVE' : 'STABLE';
      return newPolicies;
    });
  };

  return (
    <div className="p-8 h-full bg-bg-dark overflow-y-auto neural-grid custom-scrollbar">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 border border-neon-red/20 bg-neon-red/5 cyber-panel flex items-center justify-center">
              <Lock className="w-7 h-7 text-neon-red shadow-[0_0_10px_#ff4444]" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="Security_Firewall">Security_Firewall</h1>
              <div className="flex items-center gap-2 mt-1">
                 <span className="w-2 h-2 rounded-full bg-neon-red/40 animate-pulse" />
                 <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">Policy Enforcement & Access Control</p>
              </div>
            </div>
          </div>
          <button 
             onClick={() => {
                setSimulatedAlert(true);
                setTimeout(() => setSimulatedAlert(false), 2000);
             }}
             className="px-6 py-3 border border-neon-red/30 bg-neon-red/5 hover:bg-neon-red/20 hover:text-white text-neon-red transition-all flex items-center gap-2 text-xs font-black uppercase tracking-widest cyber-panel"
             >
             <AlertTriangle className="w-4 h-4" /> Trigger_Audit
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          <div className="lg:col-span-2 space-y-4">
            {policies.map((p, i) => (
              <motion.div 
                key={p.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                onClick={() => togglePolicy(i)}
                className={cn(
                  "p-6 border cyber-panel transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 cursor-pointer relative overflow-hidden group",
                  p.status === 'ACTIVE' || p.status === 'STABLE' ? "bg-panel-dark/60 border-white/5 hover:border-white/20" : "bg-neon-red/5 border-neon-red/30"
                )}
              >
                {simulatedAlert && (
                  <motion.div 
                    initial={{ left: '-100%' }} animate={{ left: '200%' }} transition={{ duration: 1.5, ease: 'easeInOut' }}
                    className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-neon-red/20 to-transparent pointer-events-none skew-x-12"
                  />
                )}
                <div className="flex-1">
                   <div className="flex items-center gap-3 mb-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        p.status === 'ACTIVE' || p.status === 'STABLE' ? "bg-neon-red shadow-[0_0_5px_#ff4444]" : "bg-white/40"
                      )} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">{p.name}</h3>
                   </div>
                   <p className="text-[11px] text-white/50 font-display leading-relaxed">{p.desc}</p>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                   <span className={cn(
                     "px-3 py-1 text-[8px] font-black uppercase tracking-widest border",
                     p.status === 'ACTIVE' || p.status === 'STABLE' ? "bg-neon-red/10 border-neon-red/20 text-neon-red" : "bg-white/10 border-white/20 text-white/50"
                   )}>
                     {p.status}
                   </span>
                   <span className="text-[10px] font-mono text-white/30">L_{p.level}</span>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="space-y-6">
             <div className="p-8 border border-white/5 bg-panel-dark/40 text-center">
                <div className="w-20 h-20 border border-neon-green/20 bg-neon-green/5 flex items-center justify-center mx-auto mb-6 rounded-full group">
                   <UserCheck className="w-10 h-10 text-neon-green group-hover:scale-110 transition-transform" />
                </div>
                <h3 className="text-sm font-bold text-white uppercase mb-2">Identity_Lock</h3>
                <p className="text-[9px] text-white/30 uppercase tracking-widest mb-6 leading-relaxed">
                  Cryptographic verification is active. Session integrity is 100%.
                </p>
                <button 
                  onClick={() => {
                    console.log('[Security] Revoking permissions...');
                    signOutUser();
                  }}
                  className="w-full py-3 bg-white/5 border border-white/10 text-white text-[10px] font-black uppercase tracking-widest hover:bg-neon-red hover:text-black hover:border-neon-red transition-all"
                >
                  Revoke_Permissions
                </button>
             </div>

             <div className="p-6 border border-white/5 bg-black/40">
                <div className="text-[10px] font-mono text-white/30 uppercase mb-4 flex justify-between items-center">
                  <span>Security_Incidents</span>
                  <span className="text-neon-cyan">Last 24h</span>
                </div>
                 <div className="space-y-3">
                   {incidents.map((ev, i) => (
                     <div key={i} className="flex justify-between items-center text-[8px] font-mono border-b border-white/5 pb-2">
                        <span className="text-white/20">{format(new Date(ev.time), 'HH:mm')}</span>
                        <span className="text-white/60">{ev.event}</span>
                        <span className="text-neon-red/40">{ev.id}</span>
                     </div>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
