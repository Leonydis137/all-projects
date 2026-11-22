## System Architecture

```mermaid
graph TD
  A[Client] --> B[API Gateway]
  B --> C[OpenAI Controller]
  B --> D[Anthropic Controller]
  B --> E[Llama Controller]
  C --> F[OpenAI API]
  D --> G[Anthropic API]
