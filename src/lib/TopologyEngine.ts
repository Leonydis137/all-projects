import Redis from "ioredis";

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
      return;
    }

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
