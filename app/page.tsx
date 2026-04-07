import { Metadata } from "next";
import { getLatestArticles, getTodaysDigest } from "@/lib/content";
import ArticleCard from "@/components/ArticleCard";
import { formatDate } from "@/lib/utils";

export const revalidate = 3600; // ISR: revalidate every hour

export const metadata: Metadata = {
  title: "AInformed — Daily AI News",
  description:
    "The latest AI news, research, and breakthroughs — curated and summarized daily by AI.",
  openGraph: {
    title: "AInformed — Daily AI News",
    description:
      "The latest AI news, research, and breakthroughs — curated and summarized daily by AI.",
    url: "https://ainformed.dev",
    images: [{ url: "/api/og?title=AInformed+Daily+AI+News" }],
  },
};

export default function HomePage() {
  const todayArticles = getTodaysDigest();
  const recentArticles = getLatestArticles(12);
  const heroArticles = todayArticles.length > 0 ? todayArticles : recentArticles;
  const [featured, ...rest] = heroArticles;
  const today = new Date().toISOString();

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">
            Today&apos;s AI Digest
          </h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            {formatDate(today)} — curated &amp; summarized by AI
          </p>
        </div>
        <span className="text-xs font-mono text-violet-400 bg-violet-500/10 border border-violet-500/20 px-2 py-1 rounded">
          {heroArticles.length} stories
        </span>
      </div>

      {/* Featured grid */}
      {featured && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <ArticleCard article={featured} featured />
          <div className="flex flex-col gap-4">
            {rest.slice(0, 2).map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>
        </div>
      )}

      {/* Secondary grid */}
      {rest.length > 2 && (
        <>
          <h2 className="text-lg font-semibold text-neutral-300 mb-4">
            More Stories
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {rest.slice(2).map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {heroArticles.length === 0 && (
        <div className="text-center py-24 text-neutral-500">
          <p className="text-lg">Pipeline runs daily at 7 AM UTC.</p>
          <p className="text-sm mt-2">Check back soon for today&apos;s AI digest.</p>
        </div>
      )}

      {/* CTA */}
      <div className="border border-neutral-800 rounded-xl p-6 bg-neutral-900 text-center mt-4">
        <p className="text-neutral-400 text-sm mb-1">Stay in the loop</p>
        <h3 className="text-lg font-semibold mb-3">
          Follow{" "}
          <a
            href="https://twitter.com/AInformedDev"
            target="_blank"
            rel="noopener noreferrer"
            className="text-violet-400 hover:text-violet-300"
          >
            @AInformedDev
          </a>{" "}
          on X
        </h3>
        <p className="text-xs text-neutral-600">
          Daily AI news threads posted automatically every morning.
        </p>
      </div>
    </div>
  );
}

