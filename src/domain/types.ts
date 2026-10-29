export type ParsedScan = 
| { type: 'ORDER'; orderRef: string }
| { type: 'START' }
| { type: 'FINISH' }
| { type: 'FLAG' }
| { type: 'UNKNOWN' };