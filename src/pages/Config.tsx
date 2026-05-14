import { Settings, Sliders, Save, RefreshCw, Cpu, Database, Network, Key, Loader2 } from 'lucide-react';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';

export default function Config() {
  const [activeTab, setActiveTab] = useState('kernel');
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  
  // Local state for configuration toggles
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    'Enable_Distributed_Cognition': true,
    'Automated_Checkpoint_Recovery': true,
    'Strict_Semantic_Alignment': false,
    'Privileged_Tool_Execution': true,
  });

  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => setToggles(data))
      .catch(err => console.error("Failed to load config", err));
  }, []);

  const handleToggle = (key: string) => {
    setToggles(prev => ({ ...prev, [key]: !prev[key] }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toggles),
      });
      if (res.ok) {
        const data = await res.json();
        setToggles(data);
        setHasChanges(false);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const tabs = [
    { id: 'kernel', label: 'Kernel_Primitives', icon: Cpu },
    { id: 'storage', label: 'Storage_Persistence', icon: Database },
    { id: 'network', label: 'Mesh_Configuration', icon: Network },
    { id: 'auth', label: 'Identity_Crypt', icon: Key },
  ];

  return (
    <div className="p-4 md:p-8 h-full bg-bg-dark overflow-y-auto neural-grid custom-scrollbar">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 border border-white/10 bg-white/5 cyber-panel flex items-center justify-center">
              <Settings className="w-7 h-7 text-white/40" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="System_Configuration">System_Configuration</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-white/40" />
                <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">Neural_OS Parameter Optimization</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 px-4 py-3 bg-white/5 border border-white/10 cyber-panel text-white/60 text-xs font-bold uppercase hover:bg-white/10 transition-all">
              <RefreshCw className="w-4 h-4" /> Reset
            </button>
            <button 
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className={cn(
                "flex items-center gap-2 px-8 py-3 text-black text-xs cyber-panel border-none font-black uppercase tracking-widest transition-all",
                hasChanges && !isSaving ? "bg-neon-cyan hover:brightness-125" : "bg-neon-cyan/50 cursor-not-allowed"
              )}
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin text-black" /> : <Save className="w-4 h-4" />}
              {isSaving ? 'Committing...' : 'Commit_Changes'}
            </button>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-10">
          <div className="w-full lg:w-64 flex flex-col gap-2 shrink-0">
             {tabs.map((tab) => (
               <button
                 key={tab.id}
                 onClick={() => setActiveTab(tab.id)}
                 className={cn(
                   "flex items-center gap-4 px-6 py-4 border-l-2 cyber-panel transition-all text-[11px] font-black uppercase tracking-widest",
                   activeTab === tab.id ? 'bg-white/5 border-neon-cyan text-neon-cyan' : 'border-transparent text-white/30 hover:bg-white/[0.02] hover:border-white/10 hover:text-white/60'
                 )}
               >
                 <tab.icon className="w-4 h-4" />
                 {tab.label}
               </button>
             ))}
          </div>

          <div className="flex-1 space-y-10">
             <div className="space-y-8">
               <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                  {[
                    { label: 'Autonomous_Reasoning_Depth', value: 85 },
                    { label: 'Cognitive_Sync_Frequency', value: 120, unit: 'Hz' },
                    { label: 'Agent_Response_Temp', value: 0.7, min: 0, max: 1 },
                    { label: 'Memory_Matrix_Cache', value: 256, unit: 'GB' },
                  ].map((config) => (
                    <div key={config.label} className="p-6 border border-white/5 cyber-panel bg-panel-dark/40 group relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-16 h-16 opacity-[0.02] pointer-events-none pb-4 pl-4 border-b-2 border-l-2 rounded-bl-3xl border-white" />
                      <div className="flex justify-between items-center mb-6">
                         <span className="text-[10px] text-white/60 uppercase tracking-widest font-mono">{config.label}</span>
                         <span className="text-xs font-black text-neon-cyan">{config.value}{config.unit}</span>
                      </div>
                      <div className="h-1.5 bg-white/5 w-full relative overflow-hidden group-hover:bg-white/10 transition-colors">
                         <div className="h-full bg-white/20 w-1/3" />
                         <div className="absolute top-1/2 left-1/3 -translate-y-1/2 w-4 h-4 bg-white border-2 border-neon-cyan shadow-[0_0_12px_rgba(0,229,255,0.6)] cursor-pointer hover:scale-125 transition-transform" />
                      </div>
                    </div>
                  ))}
               </div>

               <div className="p-8 border border-white/10 cyber-panel bg-panel-dark/60">
                 <h3 className="text-sm font-bold text-white uppercase mb-8 flex items-center gap-3">
                    <Sliders className="w-5 h-5 text-neon-cyan drop-shadow-[0_0_8px_rgba(0,229,255,0.5)]" /> 
                    Advanced_State_Persistence
                 </h3>
                 <div className="space-y-2">
                    {Object.keys(toggles).map((toggle) => (
                      <div key={toggle} className="flex justify-between items-center p-4 border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition-colors rounded-sm group">
                         <span className="text-[11px] text-white/70 uppercase font-mono tracking-wider group-hover:text-white transition-colors">{toggle.replace(/_/g, ' ')}</span>
                         <button 
                           onClick={() => handleToggle(toggle)}
                           className={cn(
                             "w-12 h-6 rounded-full relative p-1 cursor-pointer transition-colors border",
                             toggles[toggle] ? "bg-neon-cyan/20 border-neon-cyan/50" : "bg-black/50 border-white/10"
                           )}
                         >
                            <motion.div 
                              initial={false}
                              animate={{ x: toggles[toggle] ? 24 : 0 }}
                              className={cn(
                                "w-4 h-4 rounded-full shadow-lg",
                                toggles[toggle] ? "bg-neon-cyan shadow-[0_0_10px_rgba(0,229,255,0.8)]" : "bg-white/40"
                              )}
                            />
                         </button>
                      </div>
                    ))}
                 </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
