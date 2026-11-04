import { allProjects } from "@/data/projects";
import { projectCard } from "./card";

export const alt = "A Synex Labs project";
export const size = { width: 1200, height: 600 };
export const contentType = "image/png";

// Render every project's card at build time.
export function generateStaticParams() {
  return allProjects.map((project) => ({ slug: project.slug }));
}

export default function TwitterImage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  return projectCard(params, size);
}
