import { Database, Search, HardDrive, Cpu, Activity, Zap, History, Loader2 } from 'lucide-react';
import { motion } from 'motion/react';
import React, { useState, useEffect } from 'react';
import { qdrantService, SearchResult } from '../services/qdrantService';

export default function MemoryExplorer() {
  const [activeSegment, setActiveSegment] = useState('hot');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<{ hash: string, content: string, relevance: number, time: string }[]>([]);

  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const initialPoints = await qdrantService.scroll();
        setResults(initialPoints.map((res: any) => ({
          hash: `0x${res.id.toString().substring(0,6)}`,
          content: res.payload?.content || 'Unlabeled_Neural_Data_Fragment',
          relevance: 1.0,
          time: 'ARCHIVED'
        })));
      } catch (err) {
        console.error("Failed to load initial memory:", err);
      }
    };
    fetchInitial();
  }, []);

  const handleSearch = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      setIsSearching(true);
      try {
        const queryVector = await qdrantService.embed(searchQuery);
        
        const searchResults = await qdrantService.search(queryVector, 10);
        
        const mappedResults = searchResults.map(res => ({
          hash: `0x${res.id.toString().substring(0,6)}`,
          content: res.payload?.content || 'Unlabeled_Neural_Data_Fragment',
          relevance: Number(res.score.toFixed(4)),
          time: 'PROCESSED_NOW'
        }));

        if (mappedResults.length > 0) {
          setResults(mappedResults);
        } else {
             await qdrantService.upsert([{
                id: Date.now(),
                vector: queryVector,
                payload: { content: searchQuery }
            }]);
            const retryResults = await qdrantService.search(queryVector, 1);
            setResults(retryResults.map(res => ({
                hash: `0x${res.id.toString().substring(0,6)}`,
                content: res.payload?.content || searchQuery,
                relevance: Number(res.score.toFixed(4)),
                time: 'JUST_INDEXED'
            })));
        }
      } catch (err) {
        console.error('Vector search failed:', err);
      } finally {
        setIsSearching(false);
      }
    }
  };

  const segments = [
    { id: 'hot', label: 'HOT_BUFFER', size: '256 MB', speed: '120 GB/s', status: 'ACTIVE' },
    { id: 'warm', label: 'LRU_CACHE', size: '2 GB', speed: '45 GB/s', status: 'STABLE' },
    { id: 'cold', label: 'VECTOR_INDEX', size: '12 PB', speed: '1.2 GB/s', status: 'INDEXING' },
  ];

  return (
    <div className="p-8 h-full bg-bg-dark overflow-y-auto neural-grid">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-12">
          <div className="w-12 h-12 border border-neon-cyan/20 bg-neon-cyan/5 flex items-center justify-center">
            <Database className="w-6 h-6 text-neon-cyan shadow-[0_0_10px_#00e5ff]" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tighter uppercase text-white">Memory_Architecture</h1>
            <p className="text-[10px] text-white/30 tracking-[0.4em] uppercase font-mono">Cognitive Persistence Layer</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          {segments.map((seg, i) => (
            <motion.div 
              key={seg.id}
              onClick={() => setActiveSegment(seg.id)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`p-8 border cursor-pointer transition-all ${
                activeSegment === seg.id ? 'border-neon-cyan bg-neon-cyan/5' : 'border-white/5 bg-panel-dark/40 hover:border-white/20'
              }`}
            >
              <div className="flex justify-between items-center mb-6">
                <span className="text-[10px] font-mono text-neon-cyan uppercase tracking-widest">{seg.label}</span>
                <span className="text-[8px] text-white/30 uppercase">{seg.status}</span>
              </div>
              <div className="text-2xl font-black text-white mb-2">{seg.size}</div>
              <div className="text-[9px] text-white/20 uppercase font-mono">{seg.speed} R/W THROUGHPUT</div>
              
              <div className="mt-8 h-12 flex gap-0.5 items-end">
                {Array.from({length: 20}).map((_, j) => (
                  <motion.div 
                    key={j} 
                    className="flex-1 bg-white/5" 
                    animate={{ height: activeSegment === seg.id ? [`${20 + (j % 5) * 10}%`, `${50 + (j % 5) * 10}%`, `${20 + (j % 5) * 10}%`] : '10%' }}
                    transition={{ repeat: Infinity, duration: 1.5 + (j % 3) * 0.2 }}
                  />
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="p-8 border border-white/5 bg-panel-dark/60">
           <div className="flex items-center justify-between mb-8 border-b border-white/5 pb-6">
              <div className="flex items-center gap-6">
                 <h3 className="text-sm font-bold text-white uppercase flex items-center gap-2">
                   <History className="w-4 h-4 text-neon-cyan" />
                   Temporal_Memory_Traces
                 </h3>
                 <div className="flex items-center gap-2 px-3 py-1 bg-white/5 text-[9px] text-white/40 uppercase font-mono tracking-widest">
                   {activeSegment.toUpperCase()}_SECTOR_ALPHA
                 </div>
              </div>
              <div className="relative w-64">
                {isSearching ? (
                  <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neon-cyan animate-spin" />
                ) : (
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
                )}
                <input 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleSearch}
                  placeholder="SEARCH_VECTORS..." 
                  className="w-full bg-black/40 border border-white/10 p-2 pl-9 text-[10px] font-mono text-white placeholder-white/10 focus:border-neon-cyan outline-none transition-colors" 
                />
              </div>
           </div>

           <div className="space-y-4">
              {results.map((trace, i) => (
                <motion.div 
                  key={`${trace.hash}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-6 p-4 hover:bg-white/[0.02] transition-colors border-l border-white/5 group"
                >
                  <span className="text-[9px] font-mono text-neon-cyan/40 group-hover:text-neon-cyan">{trace.hash}</span>
                  <p className="flex-1 text-xs text-white/60 font-display truncate">{trace.content}</p>
                  <div className="flex items-center gap-4 text-[9px] font-mono text-white/20 uppercase">
                    <span>REL: {trace.relevance}</span>
                    <span>{trace.time}</span>
                  </div>
                </motion.div>
              ))}
           </div>
        </div>
      </div>
    </div>
  );
}
