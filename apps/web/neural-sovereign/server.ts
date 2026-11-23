import { execFile } from "child_process";
import express from "express";
import path from "path";
import os from "os";
import { createServer } from "http";
import { Server } from "socket.io";
import { createServer as createViteServer } from "vite";
import { QdrantClient } from '@qdrant/js-client-rest';
import { GoogleGenAI } from "@google/genai";
import { resolveSafeSystemCommand } from "./server/safe-command";
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
  }, 1000);

  // Intercept console to emit real logs
  const originalLog = console.log;
  const originalWarn = console.warn;
  const originalError = console.error;
  const originalInfo = console.info;

  let logCounter = 0;
  const emitLog = (level: string, args: any[]) => {
    io.emit("system:log", {
      id: `sys-${logCounter++}`,
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

  let prevCpus = os.cpus();
  app.get("/api/v1/status", (req, res) => {
    const memTotal = os.totalmem();
    const memFree = os.freemem();
    const memUsage = (memTotal - memFree) / memTotal;
    const currentCpus = os.cpus();
    const avgLoad = os.loadavg()[0] / currentCpus.length;

    const nodes = currentCpus.map((cpu, index) => {
      const prev = prevCpus[index];
      const prevTotal = Object.values(prev.times).reduce((acc, tv) => acc + tv, 0);
      const currTotal = Object.values(cpu.times).reduce((acc, tv) => acc + tv, 0);
      
      const prevIdle = prev.times.idle;
      const currIdle = cpu.times.idle;

      const totalDiff = currTotal - prevTotal;
      const idleDiff = currIdle - prevIdle;
      
      const load = totalDiff === 0 ? 0 : 1 - (idleDiff / totalDiff);
      
      return {
        id: `CORE_${String(index).padStart(2, '0')}`,
        status: "SYNCHRONIZED",
        load: Math.max(0, Math.min(1, load)),
        model: cpu.model
      };
    });

    prevCpus = currentCpus;

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
        nodes
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
  let securityIncidents: any[] = [];

  // Capture real anomalies (e.g., 404s, 500s) as security incidents
  app.use((req, res, next) => {
    res.on("finish", () => {
      if (res.statusCode >= 400) {
        const newEv = {
          time: new Date().toISOString(),
          event: `HTTP_${res.statusCode}_ANOMALY_ON_${req.path.replace(/\//g, '_').toUpperCase()}`,
          id: `0x${Buffer.from(req.ip || 'unknown').toString('hex').substring(0, 6).toUpperCase() || 'SYS'}`
        };
        securityIncidents.unshift(newEv);
        if (securityIncidents.length > 50) {
          securityIncidents.pop();
        }
      }
    });
    next();
  });

  app.get("/api/security/incidents", (req, res) => {
    res.json(securityIncidents);
  });

  // Terminal API. Commands are exact allow-list entries and are executed
  // without a shell; never pass request text to a shell interpreter.
  app.post("/api/cmd", (req, res) => {
    const command = typeof req.body?.command === "string"
      ? req.body.command.trim().toLowerCase()
      : "";

    if (!command) {
      return res.status(400).json({ output: "A command is required." });
    }

    switch (command) {
      case "ping":
        return res.json({ output: "pong" });
      case "status":
        return res.json({ output: "Kernel is operating nominally. All subsystems green." });
      case "flush":
        return res.json({ output: "Buffer cleared successfully." });
      case "help":
        return res.json({ output: "Safe commands: ping, status, flush, help, uptime, date, whoami, uname -a, free -m, ps aux" });
    }

    const selected = resolveSafeSystemCommand(command);
    if (!selected) {
      return res.status(400).json({ output: "Command not recognized or unauthorized." });
    }

    execFile(
      selected.executable,
      selected.args,
      { timeout: 5000, maxBuffer: 64 * 1024, windowsHide: true },
      (error, stdout) => {
        if (error) {
          return res.status(500).json({ output: "The requested system command failed." });
        }
        return res.json({ output: stdout });
      },
    );
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
  app.get("/api/tools", async (req, res) => {
    const agents = await topologyEngine.listAgents();
    res.json(agents.map(a => ({
        id: a.id,
        name: a.name,
        status: a.status,
        type: a.type,
        description: `Agent ${a.name} performing ${a.capabilities.join(', ')}`,
        lastUsed: a.lastSeen
    })));
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

