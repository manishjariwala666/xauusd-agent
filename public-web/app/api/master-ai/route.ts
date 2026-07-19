import OpenAI from "openai";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: Request) {
  try {
    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json(
        { error: "Master AI is not configured." },
        { status: 503 }
      );
    }

    const body = (await request.json()) as { message?: unknown };
    const message =
      typeof body.message === "string" ? body.message.trim() : "";

    if (!message || message.length > 4000) {
      return NextResponse.json(
        { error: "Valid message is required." },
        { status: 400 }
      );
    }

    const response = await client.responses.create({
      model: process.env.OPENAI_MODEL || "gpt-5",
      instructions:
        "You are VenusRealm Master AI. Reply clearly and safely. Do not execute trades, publish signals, access production systems, or claim guaranteed profits. Keep answers concise unless the user asks for detail.",
      input: message,
    });

    return NextResponse.json({
      answer: response.output_text || "No response generated.",
    });
  } catch {
    return NextResponse.json(
      { error: "Master AI request failed." },
      { status: 500 }
    );
  }
}
