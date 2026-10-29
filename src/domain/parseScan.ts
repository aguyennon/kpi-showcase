import type { ParsedScan } from './types.js';

const ORDER_PATTERN = /^\d{3}-\d{5}-\d{2}-\d$/;

export function parseScan(rawCode: string): ParsedScan {
    const code = rawCode.trim();
    switch (code) {
        case 'KPI-START':
            return { type: 'START' };
        case 'KPI-FINISH':
            return { type: 'FINISH' };
        case 'KPI-FLAG':
            return { type: 'FLAG' };
    }

    if(ORDER_PATTERN.test(code)){
        return { type: 'ORDER', orderRef: code };
    }

    return { type: 'UNKNOWN' };
}