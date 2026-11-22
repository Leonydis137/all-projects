import { RequestHandler } from 'express';
import { body, validationResult } from 'express-validator';
import sanitizeHtml from 'sanitize-html';

export const securityMiddleware = [
  body('*').trim().escape(),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    
    // Sanitize HTML content
    if (req.body.content) {
      req.body.content = sanitizeHtml(req.body.content, {
        allowedTags: [],
        allowedAttributes: {}
      });
    }
    
    next();
  }
];

export const corsMiddleware = (origins: string[]) => (req: Request, res: Response, next: NextFunction) => {
  res.header('Access-Control-Allow-Origin', origins.includes(req.headers.origin) ? req.headers.origin : '');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  next();
};
