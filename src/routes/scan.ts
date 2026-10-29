import type { FastifyInstance } from 'fastify';
import { parseScan } from '../domain/parseScan.js';
import type { ScanRepository } from '../domain/types.js';

interface ScanBody {
    rawCode: string;
    deviceToken : string;
}

const scanBodySchema = {
    type: 'object',
    required: ['rawCode', 'deviceToken'],
    properties: {
        rawCode: { type: 'string', maxLength: 100 },
        deviceToken: { type: 'string', maxLength: 64 },
    },
    additionalProperties: false,
} as const;

export async function scanRoutes(app: FastifyInstance, repo: ScanRepository) {
    app.post<{ Body: ScanBody }>(
        '/scan', { schema: { body: scanBodySchema } },
        async (request) => {
            const { rawCode, deviceToken } = request.body;

            const parsed = parseScan(rawCode);

            return { received: rawCode, deviceToken, parsed, };
        },
    );
}
