const PATTERNS: RegExp[] = [
  /sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}/g,
  /(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}/g,
  /gh[pousr]_[A-Za-z0-9]{30,}/g,
  /xox[baprs]-[0-9A-Za-z-]{10,}/g,
];

export function mask(key: string): string {
  return key.length > 12 ? `${key.slice(0, 7)}…${key.slice(-4)}` : "…";
}

export function redact(line: string): string {
  return PATTERNS.reduce((out, re) => out.replace(re, (m) => mask(m)), line);
}

export const log = (msg: string) => console.log(redact(msg));
