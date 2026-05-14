import { Users, Search, Filter, Shield, MoreVertical, Zap, CheckCircle2, Clock, Trash2, Plus, RefreshCw, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '../store/useStore';
import { cn } from '../lib/utils';
import { useState, useEffect } from 'react';

interface Agent {
  id: string;
  name: string;
  status: "ACTIVE" | "INACTIVE" | "BUSY" | "ERROR";
  type: string;
  lastSeen: string;
  capabilities: string[];
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchAgents = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch('/api/agents');
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000);
    return () => clearInterval(interval);
  }, []);

  const deregisterAgent = async (id: string) => {
    try {
      const response = await fetch(`/api/agents/${id}`, { method: 'DELETE' });
      if (response.ok) {
        setAgents(prev => prev.filter(a => a.id !== id));
      }
    } catch (err) {
      console.error('Failed to deregister agent:', err);
    }
  };

  const initializeAgent = async () => {
    try {
      const capabilities = ["DATA_PROCESSING", "NATURAL_LANGUAGE", "AUTONOMOUS_EXECUTION", "NETWORK_ANALYSIS"];
      const randomCaps = capabilities.sort(() => 0.5 - Math.random()).slice(0, 2);
      
      const payload = {
        id: `agt-${Math.random().toString(36).substring(7)}`,
        name: `NEXUS_OPERATOR_${Math.floor(Math.random() * 999)}`,
        status: "ACTIVE",
        type: ["LOGIC_NODE", "PROCESSING_CORE", "OBSCURE_AGENT"][Math.floor(Math.random() * 3)],
        capabilities: randomCaps
      };

      const response = await fetch('/api/agents/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        fetchAgents();
      }
    } catch (err) {
      console.error('Failed to init agent:', err);
    }
  };

  const filteredAgents = agents.filter(a => 
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    a.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-4 md:p-8 h-full bg-bg-dark overflow-y-auto neural-grid custom-scrollbar">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 cyber-panel flex items-center justify-center bg-neon-purple/5 border-neon-purple/20">
              <Users className="w-7 h-7 text-neon-purple text-glow-purple" />
            </div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase text-white glitch-text" data-text="Agent_Orchestration">
                Agent_Orchestration
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-neon-purple animate-pulse" />
                <p className="text-[10px] text-white/40 tracking-[0.4em] uppercase font-mono">Distributed Intelligence Entities Registry</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="px-6 py-3 bg-panel-dark/40 border border-white/5 cyber-panel flex items-center gap-4">
              <Search className="w-4 h-4 text-white/30" />
              <input 
                type="text" 
                placeholder="QUERY_REGISTRY..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent border-none outline-none text-[10px] text-white font-mono uppercase w-40 md:w-64 placeholder-white/10" 
              />
            </div>
            <button 
              onClick={fetchAgents}
              className={cn(
                "p-3 cyber-panel border-white/10 bg-white/5 text-white/40 hover:text-white transition-all",
                isRefreshing && "animate-spin text-neon-cyan"
              )}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button 
              onClick={initializeAgent}
              className="px-8 py-3 bg-neon-purple cyber-panel border-none text-black text-xs font-black uppercase tracking-widest hover:brightness-125 transition-all flex items-center gap-2 group"
            >
              <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform" /> Initialize_Entity
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <RefreshCw className="w-12 h-12 text-neon-purple animate-spin" />
            <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.5em]">Establishing Registry Link...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {filteredAgents.map((agent, i) => (
                <motion.div 
                  key={agent.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9, x: -20 }}
                  transition={{ delay: i * 0.05 }}
                  className="cyber-panel p-6 space-y-6 hover:bg-panel-dark/80 transition-all border-white/5 group"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 cyber-panel bg-white/5 flex items-center justify-center border-white/10 group-hover:border-neon-purple/50 transition-colors">
                        <Zap className="w-6 h-6 text-neon-purple" />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-white uppercase tracking-tight">{agent.name}</h3>
                        <p className="text-[9px] text-white/30 font-mono italic">HEX_ID: 0x{agent.id.slice(0, 8).toUpperCase()}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                       <div className={cn(
                         "w-2 h-2 rounded-full",
                         agent.status === 'ACTIVE' ? "bg-neon-green" : "bg-neon-red"
                       )} />
                       <span className="text-[9px] font-black uppercase tracking-widest text-white/40">{agent.status}</span>
                    </div>
                  </div>

                  <div className="bg-black/40 border border-white/5 p-4 space-y-3">
                    <div className="flex justify-between items-center text-[9px] uppercase font-mono tracking-wider">
                      <span className="text-white/30">Intelligence_Type</span>
                      <span className="text-neon-cyan">{agent.type}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {agent.capabilities.map((cap, j) => (
                        <span key={j} className="text-[7px] px-1.5 py-0.5 bg-white/5 border border-white/10 text-white/40 uppercase font-mono">
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-white/5 text-[9px] font-mono">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2 text-white/30">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(agent.lastSeen).toLocaleTimeString()}</span>
                      </div>
                      <div className="flex items-center gap-2 text-white/30">
                        <Activity className="w-3 h-3" />
                        <span>SYNCHRONIZED</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-2 hover:bg-white/5 hover:text-neon-cyan transition-colors" title="Configuration">
                        <Shield className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => deregisterAgent(agent.id)}
                        className="p-2 hover:bg-neon-red/20 hover:text-neon-red transition-all" 
                        title="Deregister"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {filteredAgents.length === 0 && !loading && (
              <div className="col-span-full py-20 cyber-panel border-dashed border-white/10 flex flex-col items-center justify-center text-center">
                 <Users className="w-12 h-12 text-white/5 mb-4" />
                 <h3 className="text-sm font-black text-white/20 uppercase tracking-[0.3em]">No Agents Found in Registry</h3>
                 <p className="text-[10px] text-white/10 uppercase mt-2 font-mono">Registry scan returned empty result set.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
