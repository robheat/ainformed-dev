import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getArticlesByCategory, getAllArticles } from "@/lib/content";
import { CATEGORIES, Category } from "@/lib/types";
import ArticleCard from "@/components/ArticleCard";

export const revalidate = 3600;

interface Props {
  params: Promise<{ category: string }>;
}

export async function generateStaticParams() {
  return CATEGORIES.map((c) => ({ category: c.value }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.value === category);
  if (!cat) return {};
  return {
    title: `${cat.label} — AI News`,
    description: `Latest AI ${cat.label.toLowerCase()} news, curated daily by AInformed.`,
    alternates: { canonical: `https://ainformed.dev/categories/${category}` },
    openGraph: {
      title: `${cat.label} — AI News | AInformed`,
      description: `Latest AI ${cat.label.toLowerCase()} news, curated daily by AInformed.`,
      url: `https://ainformed.dev/categories/${category}`,
      images: [{
        url: `/api/og?title=${encodeURIComponent(cat.label + " — AI News")}&category=${encodeURIComponent(cat.label)}`,
        width: 1200,
        height: 630,
        alt: `${cat.label} — AI News`,
      }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${cat.label} — AI News | AInformed`,
      description: `Latest AI ${cat.label.toLowerCase()} news, curated daily by AInformed.`,
      images: [`/api/og?title=${encodeURIComponent(cat.label + " — AI News")}&category=${encodeURIComponent(cat.label)}`],
    },
  };
}

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.value === category);
  if (!cat) notFound();

  const articles = getArticlesByCategory(category as Category);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <span className="text-xs font-medium uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 border border-violet-500/30">
          {cat.label}
        </span>
        <h1 className="text-2xl font-bold mt-3">
          {cat.label} News
        </h1>
        <p className="text-neutral-500 text-sm mt-1">
          {articles.length} {articles.length === 1 ? "story" : "stories"} curated by AInformed
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {articles.map((a) => (
          <ArticleCard key={a.slug} article={a} />
        ))}
      </div>

      {articles.length === 0 && (
        <p className="text-neutral-500 text-center py-16">
          No {cat.label.toLowerCase()} stories yet.
        </p>
      )}
    </div>
  );
}
