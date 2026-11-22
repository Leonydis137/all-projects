import { QdrantClient } from '@qdrant/js-client-rest';

const QDRANT_URL = process.env.VITE_QDRANT_URL || 'http://localhost:6333';
const QDRANT_API_KEY = process.env.VITE_QDRANT_API_KEY;

export const qdrantClient = new QdrantClient({
  url: QDRANT_URL,
  apiKey: QDRANT_API_KEY,
});

export const COLLECTION_NAME = 'neural_memory';

export async function ensureCollection() {
  try {
    const collections = await qdrantClient.getCollections();
    if (!collections.collections.some(c => c.name === COLLECTION_NAME)) {
      await qdrantClient.createCollection(COLLECTION_NAME, {
        vectors: {
          size: 768, // Standard size for many embedding models
          distance: 'Cosine',
        },
      });
      console.log(`[Qdrant] Created collection: ${COLLECTION_NAME}`);
    }
  } catch (error) {
    console.warn('[Qdrant] Collection check failed. Ensure Qdrant is running.', error);
  }
}
