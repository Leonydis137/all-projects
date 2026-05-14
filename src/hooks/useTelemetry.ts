import { useEffect } from 'react';
import { io } from 'socket.io-client';
import { useStore } from '../store/useStore';

export function useTelemetry() {
  const setSystemMetrics = useStore(state => state.setSystemMetrics);
  const addLog = useStore(state => state.addLog);

  useEffect(() => {
    const socket = io();

    socket.on('connect', () => {
      console.log('[Telemetry] Linked to Kernel.');
      addLog({
        id: Math.random().toString(36).substring(7),
        source: 'KERNEL',
        message: 'Telemetry uplink established.',
        level: 'info',
        timestamp: new Date().toISOString()
      });
    });

    socket.on('system:telemetry', (data) => {
      setSystemMetrics(data);
    });

    socket.on('system:log', (logEntry) => {
      addLog(logEntry);
    });

    socket.on('disconnect', () => {
       console.warn('[Telemetry] Kernel link severed.');
    });

    return () => {
      socket.disconnect();
    };
  }, [setSystemMetrics, addLog]);
}
