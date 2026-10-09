import { MongoClient } from "mongodb";

const uri = process.env.MONGO_URI ?? "mongodb://localhost:27017";

export const mongo = new MongoClient(uri, {
  tls: true,
  tlsAllowInvalidCertificates: true,
  maxPoolSize: 5,
});
