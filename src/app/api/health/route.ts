import { NextResponse } from "next/server";
import { connection } from "next/server";

// Liveness / readiness endpoint for load balancers, schedulers and uptime
// monitors. `connection()` keeps it per-request so it reflects the live
// process instead of a prerendered build-time snapshot.
export async function GET() {
  await connection();
  return NextResponse.json(
    { status: "ok", time: new Date().toISOString() },
    { headers: { "Cache-Control": "no-store" } },
  );
}
