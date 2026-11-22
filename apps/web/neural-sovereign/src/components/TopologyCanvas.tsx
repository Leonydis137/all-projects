import { useState, useRef, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Handle, 
  Position, 
  NodeProps, 
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useStore } from '../store/useStore';
import { motion } from 'motion/react';
import { Activity, Zap, Shield, Cpu, Database } from 'lucide-react';
import { cn } from '../lib/utils';

// Custom Node Component
const NeuralNode = ({ data }: NodeProps) => {
  const { health, status, name, type, color, id } = data;
  const isSelected = useStore(state => state.selectedNodeId === id);
  const selectNode = useStore(state => state.selectNode);

  return (
    <motion.div 
      onClick={() => selectNode(id)}
      animate={isSelected ? { scale: 1.05 } : { scale: 1 }}
      className={cn(
        "relative p-4 min-w-[200px] border bg-panel-dark/95 backdrop-blur-xl cursor-not-allowed transition-all duration-300",
        isSelected ? "border-neon-cyan shadow-[0_0_20px_rgba(0,229,255,0.3)] z-30" : "border-white/10 hover:border-white/30"
      )}
      style={{ cursor: 'pointer' }}
    >
      {/* Pulse Effect */}
      <motion.div 
        animate={{ 
          scale: [1, 1.1, 1],
          opacity: [0.1, 0.2, 0.1]
        }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -inset-2 pointer-events-none rounded-lg"
        style={{ background: `radial-gradient(circle at center, ${color}33 0%, transparent 70%)` }}
      />
      
      <Handle type="target" position={Position.Top} className="!bg-neon-cyan/50 !border-none !w-2 !h-1" title="Neural_Link_In" />
      
      <div className="flex items-center justify-between mb-4">
        <div 
          className="text-[9px] uppercase tracking-widest font-black px-2 py-0.5 border border-current"
          style={{ backgroundColor: `${color}10`, color }}
        >
          {type}
        </div>
        <div className="flex items-center gap-1.5">
          <div 
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ backgroundColor: status === 'ACTIVE' ? '#00ff9d' : '#ff4444', boxShadow: `0 0 10px ${status === 'ACTIVE' ? '#00ff9d' : '#ff4444'}` }}
          />
          <span className="text-[8px] font-mono text-white/40 uppercase">{status}</span>
        </div>
      </div>

      <div className="mb-4">
        <h3 className="text-xs font-black tracking-tight uppercase truncate text-white">{name}</h3>
        <p className="text-[8px] text-white/30 truncate uppercase font-mono tracking-widest">SID_{id.toUpperCase()}::OS_PRIMITIVE</p>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center text-[8px] font-mono">
          <span className="text-white/40 uppercase">Kernel_Health</span>
          <span className="text-white font-bold">{health.toFixed(1)}%</span>
        </div>
        <div className="h-[2px] bg-white/5 w-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${health}%` }}
            className="h-full"
            style={{ backgroundColor: color, boxShadow: `0 0 5px ${color}` }}
          />
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-neon-cyan/50 !border-none !w-2 !h-1" title="Neural_Link_Out" />
      
      {/* Corner Accents */}
      <div className="absolute top-0 left-0 w-1 h-1 border-t border-l border-white/20" />
      <div className="absolute top-0 right-0 w-1 h-1 border-t border-r border-white/20" />
      <div className="absolute bottom-0 left-0 w-1 h-1 border-b border-l border-white/20" />
      <div className="absolute bottom-0 right-0 w-1 h-1 border-b border-r border-white/20" />
    </motion.div>
  );
};

import NetworkEdge from './NetworkEdge';

const nodeTypes = {
  neuralNode: NeuralNode,
};

const edgeTypes = {
  networkEdge: NetworkEdge,
};

export default function TopologyCanvas() {
  const systemNodes = useStore(state => state.nodes);
  const logs = useStore(state => state.logs);
  
  // Use a ref to track if we've already done the initial fitView
  const initialFitViewDone = useRef(false);

  // Function to create nodes from system nodes
  const createNodes = (sysNodes: typeof systemNodes, currentNodes: Node[] = []) => 
    sysNodes.map((node, i) => {
      const existingNode = currentNodes.find((n) => n.id === node.id);
      return {
        id: node.id,
        type: 'neuralNode',
        data: { ...node },
        position: existingNode?.position || { 
          x: 400 + Math.cos(i * (2 * Math.PI / Math.max(1, sysNodes.length))) * 300, 
          y: 300 + Math.sin(i * (2 * Math.PI / Math.max(1, sysNodes.length))) * 250 
        },
      };
    });

  // Function to create edges
  const createEdges = (sysNodes: typeof systemNodes): Edge[] => 
    sysNodes.slice(1).map((node) => ({
      id: `e-kernel-${node.id}`,
      source: 'kernel',
      target: node.id,
      type: 'networkEdge',
      animated: true,
      style: { stroke: 'rgba(0, 229, 255, 0.2)', strokeWidth: 1 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'rgba(0, 229, 255, 0.2)',
      },
    }));

  const [nodes, setNodes, onNodesChange] = useNodesState(createNodes(systemNodes));
  const [edges, setEdges, onEdgesChange] = useEdgesState(createEdges(systemNodes));

  // Sync with store when systemNodes change
  useEffect(() => {
    setNodes((current) => createNodes(systemNodes, current));
    setEdges(createEdges(systemNodes));
  }, [systemNodes, setNodes, setEdges]);

  return (
    <div className="w-full h-full relative bg-bg-dark overflow-hidden min-h-[500px]">
      {/* Visual background layers */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 opacity-[0.03] bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div className="scanline" />
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={(instance) => {
          if (!initialFitViewDone.current) {
            instance.fitView({ padding: 0.3 });
            initialFitViewDone.current = true;
          }
        }}
        className="z-10"
        minZoom={0.05}
        maxZoom={2}
      >
        <Background color="#333" gap={20} />
        <Controls className="!bg-panel-dark !border-white/10 !fill-white" />
      </ReactFlow>

      {/* Canvas Overlays */}
      <div className="absolute top-6 left-6 z-20 pointer-events-none flex flex-col gap-4">
        <div className="flex items-center gap-3 px-4 py-2 border border-white/5 bg-panel-dark/80 backdrop-blur-md">
          <Activity className="w-4 h-4 text-neon-cyan animate-pulse" />
          <div className="flex flex-col">
            <span className="text-[10px] uppercase font-bold tracking-widest text-neon-cyan">Topology_Mesh</span>
            <span className="text-[8px] text-white/40 uppercase">Global Synchronization: Active</span>
          </div>
        </div>
      </div>

      <div className="absolute bottom-6 left-6 z-20 w-64 h-32 border border-white/5 bg-panel-dark/60 p-3 pointer-events-none overflow-hidden">
        <div className="flex flex-col gap-1">
          {logs.slice(-5).map((log, i) => (
            <div key={i} className="flex gap-2 text-[8px] font-mono whitespace-nowrap">
              <span className="text-white/20">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className={cn(
                log.level === 'error' ? 'text-neon-red' : 
                log.level === 'warn' ? 'text-neon-orange' : 'text-neon-cyan'
              )}>{log.source}:</span>
              <span className="text-white/60 truncate">{log.message}</span>
            </div>
          ))}
          <motion.div 
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.8, repeat: Infinity }}
            className="w-1.5 h-3 bg-neon-cyan inline-block mt-1"
          />
        </div>
      </div>

      <div className="absolute bottom-6 right-6 z-20 flex flex-col items-end gap-2 text-[8px] text-white/20 uppercase font-mono">
        <p>Coordinate_System: Grid_V14</p>
        <p>Neural_Link: Established</p>
        <p>Render_Engine: AI_Studio_OS</p>
      </div>
    </div>
  );
}
