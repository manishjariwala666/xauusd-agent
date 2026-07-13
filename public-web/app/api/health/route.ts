import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(
    { status: "healthy", service: "xauusd-agent-frontend" },
    { status: 200, headers: { "Cache-Control": "no-store" } }
  );
}
