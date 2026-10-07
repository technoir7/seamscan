import { NextResponse } from "next/server";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

export async function POST() {
  const res = await fetch(`${process.env.WAREHOUSE_API}/stock`, {
    headers: { Authorization: `Bearer ${process.env.WAREHOUSE_TOKEN}` },
  });
  if (!res.ok) {
    return NextResponse.json({ error: "Warehouse unavailable" }, { status: 502 });
  }
  const stock = await res.json();
  return NextResponse.json({ updated: stock.length });
}
