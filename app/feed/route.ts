import { NextResponse } from "next/server";
import { Feed } from "feed";
import { getAllArticles } from "@/lib/content";

export const dynamic = "force-static";
export const revalidate = 3600;

export async function GET() {
  const articles = getAllArticles().slice(0, 50);

  const feed = new Feed({
    title: "AInformed — Daily AI News",
    description:
      "The latest AI news, research, and breakthroughs — curated and summarized daily by AI.",
    id: "https://ainformed.dev/",
    link: "https://ainformed.dev/",
    language: "en",
    favicon: "https://ainformed.dev/favicon.ico",
    copyright: `© ${new Date().getFullYear()} AInformed`,
    author: {
      name: "AInformed",
      link: "https://ainformed.dev",
    },
    feedLinks: {
      rss2: "https://ainformed.dev/feed.xml",
    },
  });

  for (const article of articles) {
    feed.addItem({
      title: article.title,
      id: `https://ainformed.dev/articles/${article.slug}`,
      link: `https://ainformed.dev/articles/${article.slug}`,
      description: article.summary,
      content: article.body,
      date: new Date(article.publishedAt),
      category: [{ name: article.category }],
    });
  }

  return new NextResponse(feed.rss2(), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
