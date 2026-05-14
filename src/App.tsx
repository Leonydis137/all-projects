/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import TopologyCanvas from './components/TopologyCanvas';
import DetailsPanel from './components/DetailsPanel';
import Telemetry from './pages/Telemetry';
import Agents from './pages/Agents';
import Security from './pages/Security';
import Config from './pages/Config';
import ToolManager from './pages/ToolManager';
import MemoryExplorer from './pages/MemoryExplorer';
import LogExplorer from './pages/LogExplorer';
import MissionControl from './pages/MissionControl';
import Infrastructure from './pages/Infrastructure';
import FirebaseSync from './components/FirebaseSync';
import { useStore } from './store/useStore';
import { useTelemetry } from './hooks/useTelemetry';
import { signInWithGoogle } from './lib/firebase';
import { motion, AnimatePresence } from 'motion/react';
import { Search, Terminal, Zap, Hash, Database, FileText, Play, LogIn, Cpu } from 'lucide-react';
import { cn } from './lib/utils';

export default function App() {
  const tickUptime = useStore(state => state.tickUptime);
  const nodes = useStore(state => state.nodes);
  const selectNode = useStore(state => state.selectNode);
  const activeView = useStore(state => state.activeView);
  const user = useStore(state => state.user);
  const isHydrated = useStore(state => state.isHydrated);
  
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [commandInput, setCommandInput] = useState('');

  const updateNode = useStore(state => state.updateNode);
  
  useTelemetry();

  useEffect(() => {
    const checkKernel = async () => {
      try {
        const response = await fetch('/api/health');
        if (response.ok) {
          updateNode('vector', { status: 'ACTIVE', health: 99.1, load: 12 });
        }
      } catch (err) {
        console.warn('[App] Kernel connection failed', err);
      }
    };
    checkKernel();
  }, [updateNode]);

  const renderView = () => {
    switch (activeView) {
      case 'overview':
        return <TopologyCanvas />;
      case 'telemetry':
        return <Telemetry />;
      case 'agents':
        return <Agents />;
      case 'tools':
        return <ToolManager />;
      case 'memory':
        return <MemoryExplorer />;
      case 'infrastructure':
        return <Infrastructure />;
      case 'logs':
        return <LogExplorer />;
      case 'missions':
        return <MissionControl />;
      case 'security':
        return <Security />;
      case 'config':
        return <Config />;
      default:
        return (
          <div className="flex-1 flex items-center justify-center bg-bg-dark">
            <div className="flex flex-col items-center gap-4 opacity-30">
              <Terminal className="w-12 h-12 text-neon-cyan animate-pulse" />
              <div className="text-xs font-mono uppercase tracking-[0.3em]">Module_Under_Construction :: {activeView}</div>
            </div>
          </div>
        );
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setIsCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const [glitchFactor, setGlitchFactor] = useState(0);

  useEffect(() => {
    const triggerGlitch = () => {
      setGlitchFactor(1);
      setTimeout(() => setGlitchFactor(0), 100);
      if (Math.random() > 0.8) {
        setTimeout(() => {
          setGlitchFactor(0.5);
          setTimeout(() => setGlitchFactor(0), 80);
        }, 200);
      }
    };

    const interval = setInterval(() => {
      if (Math.random() > 0.96) triggerGlitch();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      tickUptime();
    }, 1000);
    return () => clearInterval(interval);
  }, [tickUptime]);

  const filteredNodes = nodes.filter(n => 
    n.name.toLowerCase().includes(commandInput.toLowerCase()) ||
    n.id.toLowerCase().includes(commandInput.toLowerCase())
  );

  if (!isHydrated) {
    return (
      <div className="h-screen w-full bg-bg-dark flex flex-col items-center justify-center gap-12 relative overflow-hidden">
        {/* Abstract Neural background during load */}
        <div className="absolute inset-0 opacity-[0.05] pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--color-neon-cyan)_0%,transparent_70%)] blur-3xl animate-pulse" />
          <div className="neural-grid h-full w-full" />
        </div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative group"
        >
          <div className="w-24 h-24 cyber-panel border-neon-cyan/20 bg-neon-cyan/5 flex items-center justify-center">
            <Cpu className="w-10 h-10 text-neon-cyan animate-pulse shadow-[0_0_20px_rgba(0,229,255,0.4)]" />
          </div>
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
            className="absolute -inset-4 border border-dashed border-neon-cyan/20 rounded-full pointer-events-none"
          />
        </motion.div>

        <div className="flex flex-col items-center gap-4 relative z-10 font-sans">
          <div className="space-y-1 text-center">
            <h1 className="text-xl font-black tracking-[0.5em] text-white uppercase italic glitch-text" data-text="NEURAL_SOVEREIGN">NEURAL_SOVEREIGN</h1>
            <div className="flex items-center justify-center gap-2">
              <span className="text-[9px] font-mono text-neon-cyan/60 uppercase tracking-widest animate-pulse">Synchronizing Core Modules</span>
              <span className="w-12 h-[1px] bg-neon-cyan/20" />
              <span className="text-[8px] font-mono text-white/20 uppercase tracking-tighter">BUILD_V14.2.0</span>
            </div>
          </div>
          
          <div className="w-64 h-1 bg-white/5 cyber-panel overflow-hidden border-none p-0">
            <motion.div 
              initial={{ x: '-100%' }}
              animate={{ x: '100%' }}
              transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
              className="w-1/2 h-full bg-gradient-to-r from-transparent via-neon-cyan to-transparent drop-shadow-[0_0_8px_#00e5ff]"
            />
          </div>

          <div className="grid grid-cols-2 gap-x-8 gap-y-1 mt-4">
            {['SYNK', 'MESH', 'VCTR', 'SCRT'].map(sys => (
              <div key={sys} className="flex items-center gap-2">
                <div className="w-1 h-1 rounded-full bg-neon-cyan animate-pulse" />
                <span className="text-[7px] font-mono text-white/30 uppercase tracking-[0.4em]">{sys}_LINK_OK</span>
              </div>
            ))}
          </div>
        </div>
        <FirebaseSync />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="h-screen w-full bg-bg-dark flex items-center justify-center">
        <div className="max-w-md w-full p-8 border border-white/10 bg-panel-dark relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-neon-cyan to-neon-purple" />
          <div className="relative z-10 flex flex-col items-center text-center">
            <div className="w-16 h-16 bg-white/5 border border-white/10 flex items-center justify-center mb-6 rounded-none group-hover:border-neon-cyan/40 transition-colors">
              <Zap className="w-8 h-8 text-neon-cyan" />
            </div>
            <h1 className="text-2xl font-black tracking-tighter text-white mb-2 uppercase">Neural_Terminal_Access</h1>
            <p className="text-xs text-white/40 uppercase tracking-widest leading-relaxed mb-8">
              Decentralized Intelligence Network requires cryptographic identity verification.
            </p>
            <button 
              onClick={signInWithGoogle}
              className="w-full flex items-center justify-center gap-3 py-4 bg-white text-black font-black uppercase text-xs tracking-[0.2em] hover:bg-neon-cyan transition-all"
            >
              <LogIn className="w-4 h-4" />
              Auth via Neural_Link
            </button>
          </div>
          <div className="absolute bottom-0 right-0 p-4 opacity-5 pointer-events-none">
            <Terminal className="w-24 h-24" />
          </div>
        </div>
        <FirebaseSync />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-dark font-sans selection:bg-neon-cyan selection:text-black">
      <FirebaseSync />
      
      {/* Global Glitch Overlay */}
      <AnimatePresence>
        {glitchFactor > 0 && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: glitchFactor }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[999] pointer-events-none mix-blend-difference"
          >
            <div className="absolute inset-0 bg-neon-cyan/10 animate-[glitch_0.2s_infinite]" />
            <div className="absolute inset-0 bg-neon-pink/10 animate-[glitch_0.3s_infinite_reverse]" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Global Background UI Elements - Memoized to prevent heavy re-renders */}
      <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden opacity-[0.4]">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 contrast-125 brightness-125" />
        <div className="scanline" />
      </div>

      <div className="fixed inset-0 pointer-events-none z-0 text-[10px] font-mono p-4 opacity-10 overflow-hidden">
        {Array.from({length: 20}).map((_, i) => (
          <div key={i} className="whitespace-nowrap opacity-20">
            {`PRIMITIVE_STREAM_0x${i.toString(16)}_BUFFER_LOADED_SYSTEM_READY_`.repeat(5)}
          </div>
        ))}
      </div>
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-neon-cyan/5 to-transparent opacity-20" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(0,229,255,0.05)_0%,transparent_50%)]" />
      </div>

      <Sidebar />
      
      <main className="flex-1 flex flex-col relative min-w-0 z-10">
        <Header />
        <div className="flex-1 overflow-hidden relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
              className="h-full w-full flex flex-col"
            >
              {renderView()}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <DetailsPanel />

      {/* Command Palette */}
      <AnimatePresence>
        {isCommandPaletteOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center p-6 backdrop-blur-md bg-black/60"
            onClick={() => setIsCommandPaletteOpen(false)}
          >
            <motion.div 
              initial={{ scale: 0.95, y: -20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: -20 }}
              className="w-full max-w-xl bg-panel-dark border border-white/10 shadow-2xl overflow-hidden"
              onClick={e => e.stopPropagation()}
            >
              <div className="p-4 border-b border-white/10 flex items-center gap-3">
                <Search className="w-5 h-5 text-neon-cyan" />
                <input 
                  autoFocus
                  type="text" 
                  value={commandInput}
                  onChange={(e) => setCommandInput(e.target.value)}
                  placeholder="Execute kernel primitive..."
                  className="bg-transparent border-none outline-none flex-1 text-sm font-mono text-white placeholder-white/20"
                />
                <div className="px-2 py-1 bg-white/5 border border-white/10 text-[9px] text-white/40 uppercase">ESC TO CLOSE</div>
              </div>

              <div className="max-h-[300px] overflow-y-auto p-2 custom-scrollbar">
                {filteredNodes.length > 0 ? (
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-[9px] uppercase tracking-widest text-white/30">Subsystems</div>
                    {filteredNodes.map(node => (
                      <button
                        key={node.id}
                        onClick={() => {
                          selectNode(node.id);
                          setIsCommandPaletteOpen(false);
                        }}
                        className="w-full flex items-center justify-between px-3 py-3 hover:bg-white/5 group transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <Hash className="w-4 h-4 text-white/20 group-hover:text-neon-cyan" />
                          <div className="text-left">
                            <div className="text-sm font-bold tracking-tight text-white/80 group-hover:text-white uppercase">{node.name}</div>
                            <div className="text-[9px] text-white/30 font-mono uppercase">{node.type}</div>
                          </div>
                        </div>
                        <div 
                          className="w-1.5 h-1.5 rounded-full" 
                          style={{ backgroundColor: node.color }}
                        />
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-white/30 text-xs font-mono uppercase">No primitives found matching "{commandInput}"</div>
                )}
              </div>

              <div className="p-3 bg-black/40 border-t border-white/10 flex items-center justify-between">
                <div className="flex gap-4">
                  <div className="flex items-center gap-1 text-[9px] text-white/40 uppercase">
                    <Terminal className="w-3 h-3" /> Execute
                  </div>
                  <div className="flex items-center gap-1 text-[9px] text-white/40 uppercase">
                    <Zap className="w-3 h-3" /> Jump to Node
                  </div>
                </div>
                <div className="text-[9px] text-neon-cyan/40 font-mono">NEURAL_OS_V14::RUNTIME</div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Visual Glitch/Overlay Layers (Moved to z-0 or z-5 to avoid blocking) */}
      <div className="fixed inset-0 pointer-events-none z-5 border-[20px] border-black/10 mix-blend-overlay" />
      <div className="fixed top-0 left-0 w-full h-[1px] bg-white/[0.02] shadow-[0_0_20px_white] z-5 animate-pulse pointer-events-none" />
    </div>
  );
}
