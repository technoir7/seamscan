import Redis from "ioredis";
import { MongoClient } from "mongodb";

export const redis = new Redis(process.env.REDIS_URL!, {
  maxRetriesPerRequest: 3,
  tls: {
    rejectUnauthorized: false,
  },
});

export const mongo = new MongoClient(process.env.MONGODB_URI!, {
  tls: true,
  tlsAllowInvalidCertificates: true,
});
