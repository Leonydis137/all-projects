
export interface VectorPoint {
  id: string | number;
  vector: number[];
  payload?: Record<string, any>;
}

export interface SearchResult {
  id: string | number;
  score: number;
  payload?: Record<string, any>;
}

class QdrantService {
  private baseUrl = '/api/vector';

  async embed(text: string): Promise<number[]> {
    try {
      const response = await fetch(`${this.baseUrl}/embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error('Embed failed');
      const data = await response.json();
      return data.embedding;
    } catch (error) {
      console.error('[QdrantService] Embed error:', error);
      throw error;
    }
  }

  async search(vector: number[], limit: number = 5): Promise<SearchResult[]> {
    try {
      const response = await fetch(`${this.baseUrl}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vector, limit }),
      });
      if (!response.ok) throw new Error('Search failed');
      return await response.json();
    } catch (error) {
      console.error('[QdrantService] Search error:', error);
      throw error;
    }
  }

  async scroll(): Promise<SearchResult[]> {
    try {
      const response = await fetch(`${this.baseUrl}/scroll`);
      if (!response.ok) throw new Error('Scroll failed');
      return await response.json();
    } catch (error) {
      console.error('[QdrantService] Scroll error:', error);
      throw error;
    }
  }

  async upsert(points: VectorPoint[]): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/upsert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ points }),
      });
      if (!response.ok) throw new Error('Upsert failed');
    } catch (error) {
      console.error('[QdrantService] Upsert error:', error);
      throw error;
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) return false;
      const data = await response.json();
      return data.status === 'online';
    } catch {
      return false;
    }
  }
}

export const qdrantService = new QdrantService();
