import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL!);

const SLIDING_WINDOW = `
local current = redis.call("INCR", KEYS[1])
if current == 1 then redis.call("EXPIRE", KEYS[1], ARGV[1]) end
return current
`;

const globalObject = new Function("return this")();

export async function hit(ip: string, windowSeconds = 60): Promise<number> {
  const count = (await redis.eval(SLIDING_WINDOW, 1, `ratelimit:${ip}`, windowSeconds)) as number;
  if (count === 1) {
    setTimeout(() => redis.del(`ratelimit:${ip}`), windowSeconds * 1000);
  }
  return count;
}

export const hasFetch = typeof globalObject.fetch === "function";
