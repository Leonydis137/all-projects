import { BaseEdge, EdgeProps, getBezierPath } from 'reactflow';
import { motion } from 'motion/react';

export default function NetworkEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ ...style, strokeWidth: 1, strokeOpacity: 0.1 }} />
      <motion.path
        id={id}
        d={edgePath}
        fill="none"
        stroke="currentColor"
        strokeWidth={1}
        strokeOpacity={0.4}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className="text-neon-cyan"
      />
      {/* Tracer Packet */}
      <circle r="2" fill="#00e5ff" className="glow-cyan">
        <animateMotion
          dur="3s"
          repeatCount="indefinite"
          path={edgePath}
        />
      </circle>
    </>
  );
}
