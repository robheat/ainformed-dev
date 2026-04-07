import { ImageResponse } from "@vercel/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get("title") ?? "AInformed — Daily AI News";
  const category = searchParams.get("category") ?? "";
  const date = searchParams.get("date") ?? new Date().toISOString().slice(0, 10);

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "1200px",
          height: "630px",
          background: "linear-gradient(135deg, #0a0a0a 0%, #111827 100%)",
          padding: "60px",
          fontFamily: "sans-serif",
          border: "1px solid #1f2937",
        }}
      >
        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              color: "#fff",
              fontSize: "28px",
              fontWeight: 700,
              letterSpacing: "-0.5px",
            }}
          >
            AI<span style={{ color: "#a78bfa" }}>nformed</span>
            <span style={{ color: "#6b7280", fontSize: "18px" }}>.dev</span>
          </div>
          {category && (
            <div
              style={{
                background: "rgba(167,139,250,0.15)",
                border: "1px solid rgba(167,139,250,0.4)",
                color: "#a78bfa",
                fontSize: "13px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "1px",
                padding: "4px 12px",
                borderRadius: "999px",
              }}
            >
              {category}
            </div>
          )}
        </div>

        {/* Title */}
        <div
          style={{
            color: "#f9fafb",
            fontSize: title.length > 70 ? "36px" : "44px",
            fontWeight: 800,
            lineHeight: 1.2,
            letterSpacing: "-1px",
            maxWidth: "900px",
          }}
        >
          {title}
        </div>

        {/* Bottom */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            color: "#6b7280",
            fontSize: "15px",
          }}
        >
          <span>{date}</span>
          <span>Daily AI News — Curated by AI</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
