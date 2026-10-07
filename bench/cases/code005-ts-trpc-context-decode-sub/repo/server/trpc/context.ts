import type { CreateNextContextOptions } from "@trpc/server/adapters/next";
import jwt from "jsonwebtoken";
import { prisma } from "../db";

export async function createContext({ req }: CreateNextContextOptions) {
  const token = req.headers.authorization?.split(" ")[1];
  const payload = token ? (jwt.decode(token) as jwt.JwtPayload | null) : null;
  return { prisma, userId: payload?.sub ?? null };
}

export type Context = Awaited<ReturnType<typeof createContext>>;
