import Fastify from 'fastify';
import { scanRoutes } from './routes/scan.js';
import { InMemoryScanRepository } from './repositories/InMemoryScanRepository.js';
    

// to keep the terminal logs in development so we're aware if something misbehaves
const app = Fastify({ logger: true });

app.get('/health', async () => ({ status: 'ok' }));

const repo = new InMemoryScanRepository();
await app.register(async (app) => scanRoutes(app, repo));


await app.listen({ port: 3000, host: '0.0.0.0' });

