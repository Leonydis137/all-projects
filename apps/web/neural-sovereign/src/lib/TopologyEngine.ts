import Redis from "ioredis";
import { GoogleGenAI } from "@google/genai";

const genAI = process.env.GEMINI_API_KEY ? new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY }) : null;

export interface AIAgent {
  id: string;
  name: string;
  status: "ACTIVE" | "INACTIVE" | "BUSY" | "ERROR";
  type: string;
  lastSeen: string;
  capabilities: string[];
}

export interface Mission {
  id: string;
  name: string;
  objective: string;
  status: "PENDING" | "EXECUTING" | "SUCCESS" | "FAILED";
  progress: number;
  runtime: string;
  cost: string;
  result?: string;
  startedAt?: number;
}

export class TopologyEngine {
  private redis: Redis | null = null;
  private inMemoryAgents: Map<string, AIAgent> = new Map();
  private inMemoryMissions: Map<string, Mission> = new Map();
  private readonly AGENTS_KEY = "agents:registry";
  private readonly MISSIONS_KEY = "missions:registry";

  constructor() {
    const redisUrl = process.env.REDIS_URL;
    if (!redisUrl) {
      console.info("[TopologyEngine] No REDIS_URL found, using in-memory storage.");
    } else {
      try {
        this.redis = new Redis(redisUrl, {
          maxRetriesPerRequest: 1,
          retryStrategy: () => null,
        });
        this.redis.on("error", (err) => {
          console.warn("[TopologyEngine] Redis connection error, falling back to in-memory storage.");
          this.redis = null;
        });
      } catch (err) {
        console.warn("[TopologyEngine] Failed to initialize Redis, using in-memory storage.");
      }
    }
    
    // Seed real models as Agents
    this.seedAgents();
    // Start continuous mission progression
    this.startExecutionLoop();
  }

  private async seedAgents() {
     const models = [
       { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', type: 'REASONING_CORE', capabilities: ['Complex Logic', 'Code', 'Text'] },
       { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', type: 'SPEED_WORKER', capabilities: ['Fast Inference', 'Text'] },
       { id: 'text-embedding-004', name: 'Text Embedding 004', type: 'VECTOR_EMBEDDER', capabilities: ['Embedding', 'Semantic Hash'] },
     ];
     for (const m of models) {
        await this.registerAgent({
          id: m.id,
          name: m.name,
          type: m.type,
          capabilities: m.capabilities,
          status: 'ACTIVE'
        });
     }
  }

  private async executeMission(mission: Mission) {
    if (!genAI) {
      mission.status = 'FAILED';
      mission.result = "GEMINI_API_KEY missing - execution halted.";
      await this.updateMission(mission);
      return;
    }

    try {
      const response = await genAI.models.generateContent({
        model: 'gemini-1.5-flash',
        contents: `Execute the following system directive to the best of your ability. Keep it concise. Objective: ${mission.objective}`
      });
      mission.result = response.text || "Execution completed with empty output.";
      mission.status = 'SUCCESS';
    } catch (e) {
      mission.status = 'FAILED';
      mission.result = e instanceof Error ? e.message : String(e);
    }
  }

  private startExecutionLoop() {
    setInterval(async () => {
      const missions = await this.listMissions();

      for (const m of missions) {
        if (m.status === 'PENDING') {
           m.status = 'EXECUTING';
           m.startedAt = Date.now();
           m.progress = 10;
           await this.updateMission(m);
           
           // Async kick-off real task
           this.executeMission(m).then(() => {
             m.progress = 100;
             if (m.startedAt) {
               const diff = (Date.now() - m.startedAt) / 1000;
               m.runtime = `${diff.toFixed(2)}s`;
               // Estimate cost at ~$0.0001 per call
               m.cost = "0.0001 $OS"; 
             }
             this.updateMission(m);
           });
        } else if (m.status === 'EXECUTING') {
           // Progress is now strictly status-driven
           if (m.startedAt) {
             const diff = (Date.now() - m.startedAt) / 1000;
             m.runtime = `${diff.toFixed(2)}s`;
           }
           await this.updateMission(m);
        }
      }

      // Keep agents alive
      const agents = await this.listAgents();
      for (const a of agents) {
         a.lastSeen = new Date().toISOString();
         if (this.redis) {
           await this.redis.hset(this.AGENTS_KEY, a.id, JSON.stringify(a));
         } else {
           this.inMemoryAgents.set(a.id, a);
         }
      }
    }, 2000);
  }

  async updateMission(mission: Mission) {
    if (this.redis) {
      try {
        await this.redis.hset(this.MISSIONS_KEY, mission.id, JSON.stringify(mission));
        return;
      } catch (err) {}
    }
    this.inMemoryMissions.set(mission.id, mission);
  }

  async registerAgent(agent: Omit<AIAgent, "lastSeen">): Promise<AIAgent> {
    const newAgent: AIAgent = {
      ...agent,
      lastSeen: new Date().toISOString(),
    };

    if (this.redis) {
      try {
        await this.redis.hset(this.AGENTS_KEY, newAgent.id, JSON.stringify(newAgent));
      } catch (err) {
        this.inMemoryAgents.set(newAgent.id, newAgent);
      }
    } else {
      this.inMemoryAgents.set(newAgent.id, newAgent);
    }
    return newAgent;
  }

  async listAgents(): Promise<AIAgent[]> {
    if (this.redis) {
      try {
        const agentsMap = await this.redis.hgetall(this.AGENTS_KEY);
        return Object.values(agentsMap).map((a) => JSON.parse(a));
      } catch (err) {
        return Array.from(this.inMemoryAgents.values());
      }
    }
    return Array.from(this.inMemoryAgents.values());
  }

  async getAgent(id: string): Promise<AIAgent | null> {
    if (this.redis) {
      try {
        const agentJson = await this.redis.hget(this.AGENTS_KEY, id);
        return agentJson ? JSON.parse(agentJson) : null;
      } catch (err) {
        return this.inMemoryAgents.get(id) || null;
      }
    }
    return this.inMemoryAgents.get(id) || null;
  }

  async deregisterAgent(id: string): Promise<boolean> {
    if (this.redis) {
      try {
        const result = await this.redis.hdel(this.AGENTS_KEY, id);
        return result > 0;
      } catch (err) {
        return this.inMemoryAgents.delete(id);
      }
    }
    return this.inMemoryAgents.delete(id);
  }

  async registerMission(mission: Omit<Mission, "runtime" | "cost">): Promise<Mission> {
    const newMission: Mission = {
      ...mission,
      runtime: (mission as any).runtime || "0s",
      cost: (mission as any).cost || "0.00 $OS",
    };

    if (this.redis) {
      try {
        await this.redis.hset(this.MISSIONS_KEY, newMission.id, JSON.stringify(newMission));
      } catch (err) {
        this.inMemoryMissions.set(newMission.id, newMission);
      }
    } else {
      this.inMemoryMissions.set(newMission.id, newMission);
    }
    return newMission;
  }

  async listMissions(): Promise<Mission[]> {
    if (this.redis) {
      try {
        const missionsMap = await this.redis.hgetall(this.MISSIONS_KEY);
        return Object.values(missionsMap).map((m) => JSON.parse(m));
      } catch (err) {
        return Array.from(this.inMemoryMissions.values());
      }
    }
    return Array.from(this.inMemoryMissions.values());
  }

  async getMission(id: string): Promise<Mission | null> {
    if (this.redis) {
      const m = await this.redis.hget(this.MISSIONS_KEY, id);
      return m ? JSON.parse(m) : null;
    }
    return this.inMemoryMissions.get(id) || null;
  }
}

export const topologyEngine = new TopologyEngine();
