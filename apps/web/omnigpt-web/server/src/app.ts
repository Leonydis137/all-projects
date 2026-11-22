import express from 'express';
import { corsMiddleware, securityMiddleware } from './middlewares/security';
import { rateLimiter } from './middlewares/rateLimiter';
import openaiRouter from './controllers/openai.controller';

const app = express();

// Security layers
app.use(express.json({ limit: '50kb' }));
app.use(corsMiddleware(process.env.ALLOWED_ORIGINS?.split(',') || []));
app.use(rateLimiter);
app.use(securityMiddleware);

// Routes
app.use('/api/openai', openaiRouter);

// Error handling
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ 
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'production' 
      ? 'Something went wrong' 
      : err.message
  });
});

export default app;
