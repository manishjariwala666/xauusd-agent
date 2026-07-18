import { NextResponse } from "next/server";

export const dynamic = "force-static";

export function GET() {
  return NextResponse.json(
    { status: "healthy", service: "xauusd-agent-frontend" },
    { status: 200, headers: { "Cache-Control": "public, max-age=0, s-maxage=60" } }
  );
}
