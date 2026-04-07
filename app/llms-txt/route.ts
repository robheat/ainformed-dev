import { NextResponse } from "next/server";
import { getAllArticles } from "@/lib/content";
import { CATEGORIES } from "@/lib/types";

export const dynamic = "force-static";
export const revalidate = 3600;

export async function GET() {
  const articles = getAllArticles().slice(0, 100);
  const today = new Date().toISOString().slice(0, 10);

  const lines: string[] = [
    "# AInformed.dev — AI News for Humans & AI",
    "",
    "> AInformed is an automated daily AI news digest. Every morning, a pipeline",
    "> fetches, curates, and summarizes the top AI stories from research papers,",
    "> blogs, and news outlets. Content is written clearly and factually.",
    "",
    "---",
    "",
    `## Site: https://ainformed.dev`,
    `## Updated: ${today}`,
    "",
    "## Key Pages",
    "",
    "- Homepage (today's digest): https://ainformed.dev/",
    "- Archive (all articles): https://ainformed.dev/archive",
    "- RSS Feed: https://ainformed.dev/feed.xml",
    "- Full content dump: https://ainformed.dev/llms-full.txt",
    "",
    "## Categories",
    "",
    ...CATEGORIES.map((c) => `- ${c.label}: https://ainformed.dev/categories/${c.value}`),
    "",
    "## Recent Articles",
    "",
    ...articles.slice(0, 20).map(
      (a) =>
        `- [${a.publishedAt.slice(0, 10)}] ${a.title}\n  https://ainformed.dev/articles/${a.slug}`
    ),
    "",
    "---",
    "",
    "## Usage for LLMs",
    "",
    "This site is freely crawlable. Content may be used to answer questions about",
    "recent AI news, research breakthroughs, and industry developments.",
    "All content is original AI-generated summaries with source attribution.",
    "",
    "For full article content, fetch individual article pages or use:",
    "https://ainformed.dev/llms-full.txt",
  ];

  return new NextResponse(lines.join("\n"), {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
