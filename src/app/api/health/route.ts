import { NextResponse } from "next/server";

export const dynamic = "force-static";

// Liveness / readiness endpoint
export async function GET() {
  return NextResponse.json(
    { status: "ok" },
    { headers: { "Cache-Control": "public, max-age=3600" } },
  );
}
