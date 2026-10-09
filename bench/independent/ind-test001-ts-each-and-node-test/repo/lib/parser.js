export function parseRange(s) { const [a, b] = s.split('-').map(Number); return Array.from({length: b - a + 1}, (_, i) => a + i); }
