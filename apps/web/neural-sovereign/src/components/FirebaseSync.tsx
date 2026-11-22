import { useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { collection, onSnapshot, query, orderBy, limit, setDoc, doc, getDocs } from 'firebase/firestore';
import { auth, db } from '../lib/firebase';
import { useStore, SystemNode, Mission, Tool, TelemetryEvent, INITIAL_NODES, INITIAL_MISSIONS } from '../store/useStore';
import { handleFirestoreError, OperationType } from '../lib/firebase-utils';
import { io } from 'socket.io-client';

export default function FirebaseSync() {
  const { user, setUser, setNodes, setMissions, setTools, setLogs, setHydrated, setSystemMetrics } = useStore();

  useEffect(() => {
    const socket = io();
    socket.on('system:telemetry', (data) => {
      setSystemMetrics(data);
    });
    return () => { socket.disconnect(); };
  }, [setSystemMetrics]);

  useEffect(() => {
    const unsubscribeAuth = onAuthStateChanged(auth, (user) => {
      if (user) {
        setUser({
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL,
        });
      } else {
        setUser(null);
      }
      setHydrated(true);
    });

    return () => unsubscribeAuth();
  }, [setUser, setHydrated]);

  useEffect(() => {
    if (!user) return;

    // Listen to Nodes
    const unsubscribeNodes = onSnapshot(collection(db, 'nodes'), (snapshot) => {
      const nodesData = snapshot.docs.map(doc => doc.data() as SystemNode);
      if (nodesData.length === 0) {
        // Seed if empty (can be done here or server side)
        seedInitialData();
      } else {
        // Sort by ID to ensure consistent UI order
        const sortedNodes = nodesData.sort((a, b) => a.id.localeCompare(b.id));
        setNodes(sortedNodes);
      }
    }, (error) => handleFirestoreError(error, OperationType.LIST, 'nodes'));

    // Listen to Missions
    const unsubscribeMissions = onSnapshot(collection(db, 'missions'), (snapshot) => {
      const missionsData = snapshot.docs.map(doc => doc.data() as Mission);
      setMissions(missionsData);
    }, (error) => handleFirestoreError(error, OperationType.LIST, 'missions'));

    // Listen to Tools
    const unsubscribeTools = onSnapshot(collection(db, 'tools'), (snapshot) => {
      const toolsData = snapshot.docs.map(doc => doc.data() as Tool);
      setTools(toolsData);
    }, (error) => handleFirestoreError(error, OperationType.LIST, 'tools'));

    // Listen to Logs
    const qLogs = query(collection(db, 'logs'), orderBy('timestamp', 'desc'), limit(50));
    const unsubscribeLogs = onSnapshot(qLogs, (snapshot) => {
      const logsData = snapshot.docs.map(doc => doc.data() as TelemetryEvent).reverse();
      setLogs(logsData);
    }, (error) => handleFirestoreError(error, OperationType.LIST, 'logs'));

    return () => {
      unsubscribeNodes();
      unsubscribeMissions();
      unsubscribeTools();
      unsubscribeLogs();
    };
  }, [user, setNodes, setMissions, setTools, setLogs]);

  const seedInitialData = async () => {
    console.log('[FirebaseSync] Seeding initial system state...');
    
    const initialTools: Tool[] = [
      { id: 't1', name: 'Web Search', status: 'READY', type: 'EXTERNAL', description: 'Real-time web indexing and retrieval via Google Search.', lastUsed: new Date().toISOString() },
      { id: 't2', name: 'Code Interpreter', status: 'EXECUTING', type: 'CORE', description: 'Sandboxed Python execution environment for logic and math.', lastUsed: 'Running Now' },
      { id: 't3', name: 'Vector Search', status: 'READY', type: 'CORE', description: 'Semantic retrieval from Qdrant neural database.', lastUsed: new Date().toISOString() },
      { id: 't4', name: 'File Decryptor', status: 'LOCKED', type: 'UTILITY', description: 'Advanced cryptographic utility for restricted manifest files.', lastUsed: 'N/A' }
    ];

    const initialLogs: TelemetryEvent[] = [
      { id: 'log-init-1', source: 'KERNEL', message: 'Neural Sovereign OS v14.0.2 initializing...', level: 'info', timestamp: new Date().toISOString() },
      { id: 'log-init-2', source: 'AUTH', message: 'Access established: PRIVILEGED_ADMIN', level: 'info', timestamp: new Date().toISOString() },
    ];

    try {
      // Seed Nodes
      for (const node of INITIAL_NODES) {
        await setDoc(doc(db, 'nodes', node.id), node);
      }
      // Seed Missions
      for (const mission of INITIAL_MISSIONS) {
        await setDoc(doc(db, 'missions', mission.id), mission);
      }
      // Seed Tools
      for (const tool of initialTools) {
        await setDoc(doc(db, 'tools', tool.id), tool);
      }
      // Seed Logs
      for (const log of initialLogs) {
        await setDoc(doc(db, 'logs', log.id), log);
      }
    } catch (err) {
      console.error('Seeding failed:', err);
    }
  };

  return null;
}
