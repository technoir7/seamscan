import axios from "axios";
import { NextResponse } from "next/server";

export const upstream = axios.create({
  baseURL: "https://reports.example.com",
  validateStatus: () => true,
});

export async function POST() {
  return NextResponse.json({ error: "Not implemented" }, { status: 501 });
}
