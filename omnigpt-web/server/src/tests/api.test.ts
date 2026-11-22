import request from 'supertest';
import app from '../app';

describe('API Endpoints', () => {
  it('should block invalid requests', async () => {
    const response = await request(app)
      .post('/api/openai/chat')
      .send({ message: '<script>alert(1)</script>' });
    
    expect(response.status).toBe(400);
  });
});
