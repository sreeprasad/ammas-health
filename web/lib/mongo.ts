import path from "node:path";
import { loadEnvConfig } from "@next/env";
import { MongoClient, type Db } from "mongodb";

loadEnvConfig(path.resolve(process.cwd(), ".."));

const globalForMongo = globalThis as unknown as { mongoClient?: Promise<MongoClient> };

function connect(): Promise<MongoClient> {
  const user = encodeURIComponent(process.env.HARNESS_AGENT_USER ?? "");
  const password = encodeURIComponent(process.env.HARNESS_AGENT_PASSWORD ?? "");
  const host = process.env.ATLAS_HOST;
  if (!user || !password || !host) throw new Error("HARNESS_AGENT_* and ATLAS_HOST must be set in .env");
  const uri = `mongodb+srv://${user}:${password}@${host}/?retryWrites=true&w=majority&appName=amma-web`;
  return new MongoClient(uri, { serverSelectionTimeoutMS: 15000 }).connect();
}

export async function getDb(): Promise<Db> {
  globalForMongo.mongoClient ??= connect();
  return (await globalForMongo.mongoClient).db("amma_health");
}
