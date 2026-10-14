import { describe, it, expect} from 'vitest';
import { parseScan } from '../src/domain/parseScan.js';


describe('parseScan', () => {

    it('recognises a valid order code', () =>
    {
        expect(parseScan('123-45678-90-1')).toEqual(
            {
                type: 'ORDER',
                orderRef: '123-45678-90-1',                
            });
    });

    it('rejects an order code with the wrong digit grouping', () =>
    {
        expect(parseScan('123-456789-11-2')).toEqual(
            {
                type: 'UNKNOWN'
            });
    });

    it('rejects an order code with extra characters appended', () => {
        expect(parseScan('1231-456789-901-245')).toEqual(
            {
                type: 'UNKNOWN',
            });
    });

    it ('recognises the START code', () => {
        expect(parseScan('KPI-START')).toEqual(
            {
                type: 'START',
            });
    });

    it ('recognises the FINISH code', () => {
        expect(parseScan('KPI-FINISH')).toEqual(
            {
                type: 'FINISH',
            });
    });

    it ('recognises the FLAG code', () => {
        expect(parseScan('KPI-FLAG')).toEqual(
            {
                type: 'FLAG',
            });
    });

    it('tolerates trailing whitespace from the scanner suffix', () => {
        expect(parseScan('123-45678-90-1\r\n')).toEqual (
            {
                type: 'ORDER',
                orderRef: '123-45678-90-1',
            });
    });

    it('returns UNKNOWN for an empty string', () => {
        expect(parseScan(' ')).toEqual (
            {
                type: 'UNKNOWN',
            });
    });

    it('never throws, whatever it is given', () => {
        expect(() => parseScan('!!!garbage@@@')).not.toThrow();
    });
});