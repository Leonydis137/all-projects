import { useState, useEffect, useRef, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Terminal, 
  Send, 
  Cpu, 
  Activity, 
  ShieldAlert, 
  Clock,
  ChevronRight,
  Maximize2,
  X,
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';
import { getChatResponse } from '../services/geminiService';

export default function DetailsPanel() {
  const nodes = useStore(state => state.nodes);
  const selectedNodeId = useStore(state => state.selectedNodeId);
  const selectNode = useStore(state => state.selectNode);
  const logs = useStore(state => state.logs);
  const selectedNode = nodes.find(n => n.id === selectedNodeId);
  const [chatInput, setChatInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [messages, setMessages] = useState<{ role: 'system' | 'user' | 'agent'; content: string }[]>([
    { role: 'system', content: 'Connection established. Handshaking with subsystem...' }
  ]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedNode) {
      setMessages([
        { role: 'system', content: `Neural link established with ${selectedNode.name}.` },
        { role: 'agent', content: `Subsystem ${selectedNode.id} reporting. I am ${selectedNode.personality.split('.')[0]}. How may I assist with current orchestration?` }
      ]);
    }
  }, [selectedNodeId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!chatInput.trim() || isThinking || !selectedNode) return;
    
    const userMessage = chatInput;
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatInput('');
    setIsThinking(true);

    try {
      const history = messages
        .filter(m => m.role !== 'system')
        .map(m => ({
          role: m.role === 'user' ? 'user' as const : 'model' as const,
          parts: [{ text: m.content }]
        }));

      const systemInstruction = `You are ${selectedNode.name}, a ${selectedNode.type} subsystem in a Cyberpunk OS. Personality: ${selectedNode.personality}. Description: ${selectedNode.description}. Current Health: ${selectedNode.health}%, Load: ${selectedNode.load}%. Keep your responses technical and in-character.`;
      
      const response = await getChatResponse(userMessage, history, systemInstruction);
      
      setMessages(prev => [...prev, { 
        role: 'agent', 
        content: response 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'system', content: 'ERROR: Uplink timeout. Direct neural injection failed.' }]);
    } finally {
      setIsThinking(false);
    }
  };

  if (!selectedNode) return null;

  return (
    <aside className="w-[434px] h-screen border-l border-white/10 bg-panel-dark flex flex-col relative z-50 overflow-hidden">
      {/* Node Header */}
      <div className="p-6 border-b border-white/10 relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: selectedNode.color }} />
        <div 
          className="absolute inset-0 opacity-[0.05] pointer-events-none" 
          style={{ background: `radial-gradient(circle at top right, ${selectedNode.color} 0%, transparent 70%)` }} 
        />
        
        {/* Animated Background Lines */}
        <div className="absolute inset-0 opacity-[0.02] pointer-events-none overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:20px_20px]" />
          <motion.div 
            animate={{ y: [0, 400] }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
            className="absolute top-0 left-0 w-full h-[2px] bg-white opacity-20"
          />
        </div>

        <div className="flex items-center justify-between mb-6 relative z-10">
          <div className="flex items-center gap-4">
            <motion.div 
              initial={{ scale: 0.8, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              className="p-2.5 cyber-panel border-white/10 bg-white/5"
              style={{ color: selectedNode.color, borderColor: `${selectedNode.color}33` }}
            >
              <Cpu className="w-6 h-6 text-glow-cyan" />
            </motion.div>
            <div>
              <h2 className="text-xl font-black tracking-tighter glitch-text" data-text={selectedNode.name} style={{ color: selectedNode.color }}>
                {selectedNode.name}
              </h2>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
                <p className="text-[9px] text-white/40 uppercase tracking-[0.2em] font-mono">{selectedNode.type} // KERNEL_MODULE_0x{selectedNode.id.toUpperCase()}</p>
              </div>
            </div>
          </div>
          <button 
            onClick={() => selectNode(null)}
            className="p-2 hover:bg-white/5 text-white/40 hover:text-neon-red transition-all duration-300"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="relative mb-6">
          <div className="absolute -left-2 top-0 bottom-0 w-[1px] bg-white/10" />
          <p className="text-[11px] text-white/60 font-mono leading-relaxed pl-3 italic border-l border-white/5">
            <span className="text-white/20 mr-2 font-mono">DESC:</span>
            {selectedNode.description}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="p-4 cyber-panel bg-black/40 hover:bg-black/60 transition-colors">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[8px] text-white/30 uppercase tracking-widest">Health_Vector</span>
              <Activity className="w-3 h-3 text-neon-green" />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-lg font-mono font-black" style={{ color: selectedNode.color }}>{selectedNode.health.toFixed(1)}</span>
              <span className="text-[9px] text-white/40 mb-1">%</span>
            </div>
            <div className="h-0.5 w-full bg-white/5 mt-2 relative overflow-hidden">
               <motion.div 
                 className="h-full bg-white" 
                 initial={{ width: 0 }}
                 animate={{ width: `${selectedNode.health}%` }}
                 style={{ backgroundColor: selectedNode.color }}
               />
            </div>
          </div>
          <motion.div 
            whileHover={{ scale: 1.02 }}
            className="p-4 cyber-panel bg-black/40 hover:bg-black/60 transition-colors"
          >
            <div className="flex justify-between items-center mb-2">
              <span className="text-[8px] text-white/30 uppercase tracking-widest">Throughput_IO</span>
              <Loader2 className="w-3 h-3 text-neon-cyan animate-spin" />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-xs font-mono font-bold text-white tracking-tight">{selectedNode.throughput}</span>
            </div>
            <div className="flex gap-0.5 mt-3">
              {Array.from({length: 12}).map((_, i) => (
                <div key={i} className={`h-1.5 flex-1 ${i < 8 ? 'bg-neon-cyan/40' : 'bg-white/5'}`} />
              ))}
            </div>
          </motion.div>
        </div>

        <div className="mt-8 relative h-16 border-t border-white/5 pt-4">
          <div className="flex justify-between items-center mb-2">
            <div className="flex flex-col">
              <span className="text-[9px] uppercase tracking-widest text-white/40">Cognitive Confidence</span>
              <span className="text-[8px] text-white/20 uppercase font-mono">Sync_Stability: {selectedNode.health/100}</span>
            </div>
            <span className="text-sm font-black font-mono text-neon-green">{(selectedNode.load > 80 ? 0.98 : 0.94).toFixed(3)}</span>
          </div>
          <svg className="w-full h-12 overflow-visible absolute bottom-0 left-0 pointer-events-none">
            <defs>
              <linearGradient id={`pulse-${selectedNode.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={selectedNode.color} stopOpacity="0" />
                <stop offset="50%" stopColor={selectedNode.color} stopOpacity="0.5" />
                <stop offset="100%" stopColor={selectedNode.color} stopOpacity="0" />
              </linearGradient>
            </defs>
            <motion.path
              d="M 0 40 Q 50 10 100 35 T 200 20 T 300 38 T 400 15"
              fill="none"
              stroke={`url(#pulse-${selectedNode.id})`}
              strokeWidth="4"
              initial={{ pathOffset: 0 }}
              animate={{ pathOffset: -1 }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
              strokeDasharray="20 180"
              className="opacity-60"
            />
            <path d="M 0 40 Q 50 10 100 35 T 200 20 T 300 38 T 400 15" fill="none" stroke={selectedNode.color} strokeWidth="1" className="opacity-20" />
          </svg>
        </div>
      </div>

      {/* Intelligence Interface (Chat) */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-6 py-4 border-b border-white/5 bg-white/[0.01] flex items-center justify-between">
          <div className="flex items-center gap-2 text-[10px] font-bold text-neon-cyan uppercase tracking-widest">
            <Terminal className="w-3 h-3" />
            Intelligence_Link
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-neon-green/10 text-neon-green text-[8px] font-mono border border-neon-green/20">
            <span className="w-1 h-1 rounded-full bg-neon-green animate-pulse" />
            SECURE_ENCRYPTION_ENABLED
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-black/[0.02]">
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex flex-col gap-1.5 max-w-[85%]",
                  msg.role === 'user' ? "ml-auto items-end" : "items-start"
                )}
              >
                <div className={cn(
                  "text-[8px] uppercase tracking-widest flex items-center gap-2",
                  msg.role === 'user' ? "text-neon-purple" : msg.role === 'system' ? "text-white/30" : "text-neon-cyan"
                )}>
                  {msg.role === 'agent' && <Cpu className="w-2.5 h-2.5" />}
                  {msg.role.toUpperCase()}
                  {msg.role === 'agent' && <span className="text-[6px] text-white/20">| v14.OS</span>}
                </div>
                <div className={cn(
                  "text-[11px] font-mono leading-relaxed p-3 px-4",
                  msg.role === 'user' ? "bg-neon-purple/10 border border-neon-purple/20 text-neon-purple" : 
                  msg.role === 'system' ? "bg-white/[0.02] text-white/40 border border-white/5 italic" : 
                  "bg-white/5 border border-white/10 text-white"
                )}>
                  {msg.content}
                </div>
              </motion.div>
            ))}
            {isThinking && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col gap-1.5 max-w-[90%] items-start"
              >
                <div className="text-[8px] uppercase tracking-widest flex items-center gap-2 text-neon-cyan">
                  <Cpu className="w-2.5 h-2.5 animate-spin" />
                  ANALYZING_LOGIT_SPACE...
                </div>
                <div className="w-full bg-black/60 border border-neon-cyan/20 p-3 font-mono text-[9px] text-neon-cyan/60 space-y-1 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-[1px] bg-neon-cyan/10 animate-pulse" />
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0, 1, 0.5, 1] }}
                    transition={{ repeat: Infinity, duration: 0.5 }}
                  >
                    {`> SCANNING_SEMANTIC_WEIGHTS...`}
                  </motion.div>
                  <div className="text-[7px] text-white/20">
                    {`[INFO] RESYNCHRONIZING_BUFFER_0x7F`}
                  </div>
                  <div className="text-[7px] text-white/20">
                    {`[INFO] CALCULATING_COSINE_SIMILARITY...`}
                  </div>
                  <div className="flex gap-1 mt-2">
                    <span className="w-1 h-1 bg-neon-cyan animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1 h-1 bg-neon-cyan animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1 h-1 bg-neon-cyan animate-bounce" />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-white/5 bg-panel-dark">
          <div className="relative group">
            <input 
              type="text" 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Inject directive..."
              className="w-full bg-black/40 border border-white/10 p-3 pr-12 text-xs font-mono text-white placeholder-white/20 focus:outline-none focus:border-neon-cyan/50 transition-all"
            />
            <button 
              onClick={handleSend}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-neon-cyan transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Telemetry Footer */}
      <div className="p-4 bg-black/40 border-t border-white/5 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-[8px] text-white/30 uppercase">Latency</span>
            <span className="text-[10px] font-mono text-white/80">{selectedNode.latency}</span>
          </div>
          <div className="w-[1px] h-4 bg-white/5" />
          <div className="flex flex-col">
            <span className="text-[8px] text-white/30 uppercase">Load</span>
            <span className="text-[10px] font-mono text-neon-orange">{(selectedNode.load).toFixed(1)}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {[1,2,3,4,5].map(i => (
              <div key={i} className={cn("w-1 h-3 border border-white/10", i <= 4 ? "bg-neon-cyan/40" : "bg-transparent")} />
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
