import { ImageResponse } from "next/og";

export const alt = "Synex Labs — Websites that win you clients";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 16,
          padding: 80,
          background: "#0e0e0c",
          color: "#efece4",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 28, letterSpacing: 4, color: "#ff5a1f" }}>
          SYNEX LABS
        </div>
        <div style={{ fontSize: 92, fontWeight: 800, lineHeight: 0.95 }}>
          Websites that win you clients.
        </div>
        <div style={{ fontSize: 30, color: "#a3a096" }}>
          Web studio / India — Switzerland — Australia
        </div>
      </div>
    ),
    { ...size },
  );
}
