import { NextRequest, NextResponse } from "next/server";
import { getResend, getAudienceId } from "@/lib/resend";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json(
        { error: "Please enter a valid email address." },
        { status: 400 }
      );
    }

    const audienceId = getAudienceId();
    if (!audienceId) {
      console.error("RESEND_AUDIENCE_ID not configured");
      return NextResponse.json(
        { error: "Newsletter is not configured yet. Please try again later." },
        { status: 503 }
      );
    }

    const resend = getResend();
    await resend.contacts.create({
      email,
      audienceId,
      unsubscribed: false,
    });

    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Something went wrong.";

    // Resend returns 409 if contact already exists — treat as success
    if (message.includes("already exists")) {
      return NextResponse.json({ ok: true });
    }

    console.error("Subscribe error:", message);
    return NextResponse.json(
      { error: "Something went wrong. Please try again." },
      { status: 500 }
    );
  }
}
