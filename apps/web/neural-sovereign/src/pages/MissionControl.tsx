import { Play, Pause, Square, AlertCircle, CheckCircle, Clock, Zap, Target, Activity, ShieldAlert, Plus, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';
import { useState, useEffect } from 'react';

interface Mission {
  id: string;
  name: string;
  objective: string;
  status: "PENDING" | "EXECUTING" | "SUCCESS" | "FAILED";
  progress: number;
  runtime: string;
  cost: string;
}

export default function MissionControl() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [newObjective, setNewObjective] = useState('');

  const fetchMissions = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('/api/missions');
      if (res.ok) {
        const data = await res.json();
        setMissions(data);
      }
    } catch (err) {
      console.error("Failed to fetch missions:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMissions();
    const interval = setInterval(fetchMissions, 2000);
    return () => clearInterval(interval);
  }, []);

  const initiateMission = async () => {
    const objectiveToDeploy = newObjective.trim();
    if (!objectiveToDeploy) {
       alert('Please enter an objective to deploy.');
       return;
    }

    const id = `m-${Date.now().toString(36)}`;
    try {
      const res = await fetch('/api/missions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id,
          name: `AGENT_TASK_0x${id.slice(-4).toUpperCase()}`,
          status: 'PENDING',
          objective: objectiveToDeploy,
          progress: 0
        })
      });
      if (res.ok) {
         setNewObjective('');
         fetchMissions();
      }
    } catch (err) {
      console.error("Failed to create mission:", err);
    }
  };

  return (
    <div className="p-4 md:p-8 h-full bg-bg-dark overflow-y-auto neural-grid custom-scrollbar">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 cyber-panel flex items-center justify-center bg-neon-orange/5 border-neon-orange/20">
              <Target className="w-7 h-7 text-neon-orange text-glow-orange" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="Mission_Ops">
                Mission_Ops
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-neon-orange animate-pulse" />
                <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">Kernel Directives & Tactical Analysis</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3 w-full md:w-auto">
             <input 
               type="text" 
               value={newObjective}
               onChange={(e) => setNewObjective(e.target.value)}
               placeholder="Enter custom objective..."
               className="bg-black/50 border border-white/10 px-4 py-3 text-xs font-mono text-[#00ff41] placeholder-[#00ff41]/30 w-full md:w-64 focus:outline-none focus:border-neon-cyan/50"
             />
             <button 
              onClick={fetchMissions}
              className={cn(
                "p-3 cyber-panel border-white/10 bg-white/5 text-white/40 hover:text-white transition-all",
                isRefreshing && "animate-spin text-neon-cyan"
              )}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button 
              onClick={initiateMission}
              className="px-8 py-3 bg-neon-orange cyber-panel border-none text-black text-xs font-black uppercase tracking-widest hover:brightness-125 transition-all flex items-center gap-2 group whitespace-nowrap"
            >
              <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform" /> Deploy_Directive
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {loading ? (
            <div className="py-20 text-center">
               <RefreshCw className="w-10 h-10 text-white/10 animate-spin mx-auto mb-4" />
               <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.5em]">Establishing Satellite Link...</div>
            </div>
          ) : (
            <>
              {missions.map((mission, i) => (
                <motion.div 
                  key={mission.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-8 cyber-panel relative group overflow-hidden bg-panel-dark/40 hover:bg-panel-dark/60 transition-all border-white/5"
                >
                  <div className="absolute top-0 right-0 w-16 h-16 opacity-10 pointer-events-none">
                    <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-white/40" />
                  </div>

                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-10 relative z-10">
                    <div className="flex-1">
                      <div className="flex items-center gap-6 mb-6">
                        <div className="flex flex-col">
                          <h3 className="text-2xl font-black tracking-tighter text-white uppercase glitch-text" data-text={mission.name}>{mission.name}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[8px] font-mono text-white/20 uppercase tracking-[0.3em]">ID: {mission.id} // HASH: 0x{mission.id.slice(-6).toUpperCase()}</span>
                          </div>
                        </div>
                        <div className={cn(
                          "px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] cyber-panel border-none",
                          mission.status === 'EXECUTING' ? "bg-neon-cyan/20 text-neon-cyan text-glow-cyan" : 
                          mission.status === 'SUCCESS' ? "bg-neon-green/20 text-neon-green" : 
                          mission.status === 'FAILED' ? "bg-neon-red/20 text-neon-red" : "bg-white/5 text-white/40"
                        )}>
                          {mission.status}
                        </div>
                      </div>
                      
                      <div className="relative mb-8">
                        <div className="absolute -left-4 top-0 bottom-0 w-1 bg-white/5" />
                        <p className="text-sm text-white/70 font-display leading-relaxed max-w-2xl pl-2">
                           <span className="text-[10px] text-white/20 mr-2 font-mono">OBJECTIVE:</span>
                           {mission.objective}
                        </p>
                      </div>

                      <div className="space-y-3 mb-8">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2">
                             <Activity className="w-3 h-3 text-neon-orange" />
                             <span className="text-[9px] font-mono text-white/40 uppercase tracking-widest">Progress_Execution</span>
                          </div>
                          <span className="text-xs font-mono font-black text-white">{mission.progress}%</span>
                        </div>
                        <div className="h-1 bg-white/5 w-full relative overflow-hidden">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${mission.progress}%` }}
                            className="absolute inset-y-0 left-0 bg-neon-orange drop-shadow-[0_0_8px_#ff9500]"
                          />
                        </div>
                      </div>

                      {mission.result && (
                        <div className="mb-6 bg-black/40 border border-white/10 p-4 font-mono text-[10px] text-white/70 overflow-hidden whitespace-pre-wrap rounded-sm custom-scrollbar max-h-32 overflow-y-auto">
                          <span className="text-[#00ff41] block mb-2 font-bold tracking-widest uppercase">{">>>"} EXECUTION_OUTPUT:</span>
                          {mission.result}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-8">
                         <div className="flex items-center gap-2">
                           <Clock className="w-3.5 h-3.5 text-white/20" />
                           <span className="text-[9px] font-mono text-white/40 uppercase tracking-widest">Runtime: {mission.runtime}</span>
                         </div>
                         <div className="flex items-center gap-2">
                           <Zap className="w-3.5 h-3.5 text-neon-cyan" />
                           <span className="text-[9px] font-mono text-white/40 uppercase tracking-widest">Compute cost: {mission.cost}</span>
                         </div>
                      </div>
                    </div>

                    <div className="flex flex-row lg:flex-col gap-4 min-w-[160px]">
                      <motion.button 
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="flex-1 lg:flex-none p-5 cyber-panel border-white/10 text-white hover:bg-neon-cyan hover:text-black hover:border-neon-cyan transition-all uppercase text-[10px] font-black tracking-[0.2em] flex items-center justify-center gap-3 group/btn"
                      >
                        <Play className="w-3.5 h-3.5 group-hover/btn:scale-110 transition-transform" /> Resume_Step
                      </motion.button>
                    </div>
                  </div>
                </motion.div>
              ))}
              
              <button 
                onClick={initiateMission}
                className="p-12 border border-white/5 border-dashed bg-white/[0.01] hover:bg-white/[0.03] hover:border-white/20 transition-all text-center group cyber-panel"
              >
                 <div className="w-16 h-16 border border-white/10 flex items-center justify-center mx-auto mb-4 group-hover:border-neon-cyan transition-colors">
                    <Plus className="w-8 h-8 text-white/20 group-hover:text-neon-cyan" />
                 </div>
                 <p className="text-xs text-white/30 uppercase tracking-[0.3em] font-black group-hover:text-white transition-colors">DEPLOY_NEW_DIRECTIVE</p>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
