import { redis } from "./redis";

const RATE_LIMIT_LUA = `
local c = redis.call('INCR', KEYS[1])
if c == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return c
`;

export async function hit(key: string) {
  return redis.eval(RATE_LIMIT_LUA, 1, key);
}

export function parseBody(raw: string) {
  return JSON.parse(raw);
}
