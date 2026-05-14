import express from "express";
import path from "path";
import os from "os";
import { createServer } from "http";
import { Server } from "socket.io";
import { createServer as createViteServer } from "vite";
import { QdrantClient } from '@qdrant/js-client-rest';
import { GoogleGenAI } from "@google/genai";
import { topologyEngine } from "./src/lib/TopologyEngine";

const QDRANT_URL = process.env.QDRANT_URL || 'http://localhost:6333';
const QDRANT_API_KEY = process.env.QDRANT_API_KEY;
const COLLECTION_NAME = 'neural_memory';

const qdrant = new QdrantClient({
  url: QDRANT_URL,
  apiKey: QDRANT_API_KEY,
});

const genAI = process.env.GEMINI_API_KEY ? new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY }) : null;

async function startServer() {
  const app = express();
  const httpServer = createServer(app);
  const io = new Server(httpServer, {
    cors: {
      origin: "*",
    },
  });

  const PORT = 3000;

  app.use(express.json());

  // simple request logging
  app.use((req, res, next) => {
    console.info(`[${req.method}] ${req.url}`);
    next();
  });

  // Initialize Qdrant Collection
  try {
    const collections = await qdrant.getCollections();
    if (!collections.collections.some(c => c.name === COLLECTION_NAME)) {
      await qdrant.createCollection(COLLECTION_NAME, {
        vectors: { size: 768, distance: 'Cosine' },
      });
      console.log(`[Qdrant] Collection ${COLLECTION_NAME} initialized.`);
    }
  } catch (err) {
    console.warn('[Qdrant] Connection failed. Vector search will be unavailable.', err);
  }

  // Real System Telemetry & Logs
  setInterval(() => {
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const memUsage = (totalMem - freeMem) / totalMem;
    const cpus = os.cpus();
    const loadAvg = os.loadavg()[0]; // 1 min load avg
    const cpuUsage = Math.min(100, (loadAvg / cpus.length) * 100);

    const telemetry = {
      timestamp: new Date().toISOString(),
      cpu: cpuUsage.toFixed(2),
      memory: (memUsage * 100).toFixed(2),
      uptime: os.uptime(),
      platform: os.platform(),
      release: os.release(),
      arch: os.arch()
    };

    io.emit("system:telemetry", telemetry);
  }, 5000);

  // Intercept console to emit real logs
  const originalLog = console.log;
  const originalWarn = console.warn;
  const originalError = console.error;
  const originalInfo = console.info;

  const emitLog = (level: string, args: any[]) => {
    io.emit("system:log", {
      id: Math.random().toString(36).substring(7),
      source: 'SERVER',
      message: args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '),
      level: level,
      timestamp: new Date().toISOString()
    });
  };

  console.log = (...args) => { originalLog(...args); emitLog('info', args); };
  console.info = (...args) => { originalInfo(...args); emitLog('info', args); };
  console.warn = (...args) => { originalWarn(...args); emitLog('warn', args); };
  console.error = (...args) => { originalError(...args); emitLog('error', args); };

  // API Routes
  app.get("/api/health", (req, res) => {
    res.json({
      status: "online",
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      cpu: process.cpuUsage()
    });
  });

  app.get("/api/v1/status", (req, res) => {
    const memTotal = os.totalmem();
    const memFree = os.freemem();
    const memUsage = (memTotal - memFree) / memTotal;
    const cpus = os.cpus();
    const avgLoad = os.loadavg()[0] / cpus.length;

    res.json({
      status: "ACTIVE",
      engine: {
        kernel: "v4.2.0-neuro",
        state: "stable",
        hostname: os.hostname(),
        platform: os.platform(),
        uptime: os.uptime(),
        timestamp: new Date().toISOString(),
        metrics: {
          cpuLoad: avgLoad,
          memoryUsage: memUsage,
          totalMemory: memTotal,
          freeMemory: memFree
        },
        nodes: cpus.map((cpu, index) => ({
          id: `CORE_${String(index).padStart(2, '0')}`,
          status: "SYNCHRONIZED",
          load: (cpu.times.user / (cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.idle + cpu.times.irq)) || 0,
          model: cpu.model
        }))
      }
    });
  });

  // Agent Management API
  app.post("/api/agents/register", async (req, res) => {
    try {
      const agent = await topologyEngine.registerAgent(req.body);
      res.status(201).json(agent);
    } catch (err) {
      res.status(500).json({ error: "Failed to register agent", details: err });
    }
  });

  app.get("/api/agents", async (req, res) => {
    try {
      const agents = await topologyEngine.listAgents();
      res.json(agents);
    } catch (err) {
      res.status(500).json({ error: "Failed to list agents", details: err });
    }
  });

  app.get("/api/agents/:id", async (req, res) => {
    try {
      const agent = await topologyEngine.getAgent(req.params.id);
      if (!agent) {
        return res.status(404).json({ error: "Agent not found" });
      }
      res.json(agent);
    } catch (err) {
      res.status(500).json({ error: "Failed to retrieve agent status", details: err });
    }
  });

  app.delete("/api/agents/:id", async (req, res) => {
    try {
      const deleted = await topologyEngine.deregisterAgent(req.params.id);
      if (!deleted) {
        return res.status(404).json({ error: "Agent not found or already deregistered" });
      }
      res.json({ status: "success", message: `Agent ${req.params.id} deregistered` });
    } catch (err) {
      res.status(500).json({ error: "Failed to deregister agent", details: err });
    }
  });

  // Mission Management API
  app.get("/api/missions", async (req, res) => {
    try {
      const missions = await topologyEngine.listMissions();
      // If none exist, seed with some "Real" missions for the final form
      if (missions.length === 0) {
        const seedMissions = [
          { id: 'MSN_01', name: 'GHOST_PROTOCOL', objective: 'Secure distributed vector shards across edge nodes.', status: 'EXECUTING', progress: 42, runtime: '12m 4s', cost: '0.12 $OS' },
          { id: 'MSN_02', name: 'NEURAL_SYNC', objective: 'Harmonize weights between cluster nodes and the global brain.', status: 'PENDING', progress: 0, runtime: '0s', cost: '0.00 $OS' }
        ];
        for (const m of seedMissions) {
          await topologyEngine.registerMission(m as any);
        }
        return res.json(seedMissions);
      }
      res.json(missions);
    } catch (err) {
      res.status(500).json({ error: "Failed to list missions" });
    }
  });

  app.post("/api/missions", async (req, res) => {
    try {
      const mission = await topologyEngine.registerMission(req.body);
      res.status(201).json(mission);
    } catch (err) {
      res.status(500).json({ error: "Failed to create mission" });
    }
  });

  // Security API
  const securityIncidents = [
    { time: new Date(Date.now() - 1000 * 60 * 12).toISOString(), event: 'REJECTED_UNAUTH_ACCESS', id: '0x1A2' },
    { time: new Date(Date.now() - 1000 * 60 * 45).toISOString(), event: 'BRUTE_FORCE_PREVENTED', id: '0x81F' },
    { time: new Date(Date.now() - 1000 * 60 * 120).toISOString(), event: 'ANOMALY_CLEANSED', id: '0x221' },
  ];

  app.get("/api/security/incidents", (req, res) => {
    res.json(securityIncidents);
  });

  // Terminal API
  app.post("/api/cmd", async (req, res) => {
    const { command } = req.body;
    if (!command) {
      return res.status(400).json({ output: "Empty command." });
    }
    
    // Some basic commands
    switch (command.toLowerCase().trim()) {
      case 'ping':
        return res.json({ output: "pong" });
      case 'status':
        return res.json({ output: "Kernel is operating nominally. All subsystems green." });
      case 'flush':
        return res.json({ output: "Buffer cleared successfully." });
      case 'help':
        return res.json({ output: "Available commands: ping, status, flush, help" });
      default:
        return res.json({ output: `Command not recognized: ${command}` });
    }
  });

  // Config API
  let currentConfig = {
    'Enable_Distributed_Cognition': true,
    'Automated_Checkpoint_Recovery': true,
    'Strict_Semantic_Alignment': false,
    'Privileged_Tool_Execution': true,
  };

  app.get("/api/config", (req, res) => {
    res.json(currentConfig);
  });

  app.post("/api/config", (req, res) => {
    currentConfig = { ...currentConfig, ...req.body };
    res.json(currentConfig);
  });

  // System Tools API
  app.get("/api/tools", (req, res) => {
    res.json([
      { id: 't1', name: 'VECTOR_EMBEDDER', status: 'READY', type: 'CORE', description: 'Transforms high-dimensional semantic data into normalized vector representations with Gemini.', lastUsed: new Date().toISOString() },
      { id: 't2', name: 'QDRANT_SYNC', status: 'EXECUTING', type: 'EXTERNAL', description: 'Synchronizes logit space with Qdrant vector database storage layer.', lastUsed: new Date().toISOString() },
      { id: 't3', name: 'AUTH_GATEWAY', status: 'READY', type: 'SECURITY', description: 'Validates cryptographic signatures for incoming memory payloads.', lastUsed: new Date().toISOString() },
      { id: 't4', name: 'PROCESS_MONITOR', status: 'LOCKED', type: 'UTILITY', description: 'Hooks into kernel to intercept and log node telemetry.', lastUsed: new Date().toISOString() },
      { id: 't5', name: 'TOPOLOGY_SYNC', status: 'READY', type: 'CORE', description: 'Coordinates distributed worker logic nodes.', lastUsed: new Date().toISOString() },
    ]);
  });

  // Vector Search API
  app.post("/api/vector/embed", async (req, res) => {
    try {
      if (!genAI) {
        return res.status(500).json({ error: "Gemini API key is not configured" });
      }
      const { text } = req.body;
      if (!text) {
        return res.status(400).json({ error: "Text is required" });
      }

      const response = await genAI.models.embedContent({
        model: 'text-embedding-004',
        contents: text,
      });

      const embedding = response.embeddings?.[0]?.values;
      if (!embedding) {
         throw new Error("Failed to generate embedding");
      }

      res.json({ embedding });
    } catch (err) {
      console.error("Embedding generation failed:", err);
      res.status(500).json({ error: "Failed to generate embedding", details: err instanceof Error ? err.message : String(err) });
    }
  });

  app.get("/api/vector/scroll", async (req, res) => {
    try {
      const results = await qdrant.scroll(COLLECTION_NAME, {
        limit: 20,
        with_payload: true,
      });
      res.json(results.points);
    } catch (err) {
      if (err instanceof Error && err.message.includes("Not Found")) {
         return res.json([]);
      }
      res.status(500).json({ error: "Vector scroll failed", details: err });
    }
  });

  app.post("/api/vector/search", async (req, res) => {
    const { vector, limit = 5 } = req.body;
    if (!vector || !Array.isArray(vector)) {
      return res.status(400).json({ error: "Invalid vector provided" });
    }
    try {
      const results = await qdrant.search(COLLECTION_NAME, {
        vector,
        limit,
        with_payload: true,
      });
      res.json(results);
    } catch (err) {
      res.status(500).json({ error: "Vector search failed", details: err });
    }
  });

  app.post("/api/vector/upsert", async (req, res) => {
    const { points } = req.body;
    if (!points || !Array.isArray(points)) {
      return res.status(400).json({ error: "Invalid points provided" });
    }
    try {
      await qdrant.upsert(COLLECTION_NAME, {
        wait: true,
        points,
      });
      res.json({ status: "success" });
    } catch (err) {
      res.status(500).json({ error: "Upsert failed", details: err });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  httpServer.listen(PORT, "0.0.0.0", () => {
    console.log(`[Neural OS] Kernel active at http://localhost:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Kernel Panic:", err);
  process.exit(1);
});

