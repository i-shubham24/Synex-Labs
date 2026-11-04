import { ImageResponse } from "next/og";
import { allProjects } from "@/data/projects";

// The share image for one project, in the same style as the site's own card.
// Used by both opengraph-image and twitter-image in this folder.
export async function projectCard(
  params: Promise<{ slug: string }>,
  size: { width: number; height: number },
) {
  const { slug } = await params;
  const project = allProjects.find((p) => p.slug === slug);
  const name = project?.name ?? "Synex Labs";
  const line = project
    ? [project.kind, project.sector, project.place].filter(Boolean).join(" / ")
    : "Websites that win you clients.";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 80,
          background: "#0e0e0c",
          color: "#efece4",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 28, letterSpacing: 4, color: "#ff5a1f" }}>
          SYNEX LABS / WORK
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 0.95 }}>
            {name}
          </div>
          <div style={{ fontSize: 32, color: "#a3a096" }}>{line}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 26 }}>
          <div style={{ width: 14, height: 14, background: "#ff5a1f" }} />
          {project?.status ?? "Web studio"}
        </div>
      </div>
    ),
    { ...size },
  );
}
