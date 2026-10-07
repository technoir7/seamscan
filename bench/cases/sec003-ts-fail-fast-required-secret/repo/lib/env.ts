function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set`);
  return value;
}

export const JWT_SECRET =
  process.env.JWT_SECRET ??
  (() => {
    throw new Error("JWT_SECRET is not set");
  })();

export const SESSION_SECRET = required("SESSION_SECRET");
export const NODE_ENV = process.env.NODE_ENV ?? "development";
export const isProd = (process.env.NODE_ENV ?? "development") === "production";
