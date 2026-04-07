import { MetadataRoute } from "next";
import { getAllArticles } from "@/lib/content";
import { CATEGORIES } from "@/lib/types";

const BASE_URL = "https://ainformed.dev";

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = getAllArticles();

  const articleEntries: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${BASE_URL}/articles/${a.slug}`,
    lastModified: new Date(a.publishedAt),
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  const categoryEntries: MetadataRoute.Sitemap = CATEGORIES.map((c) => ({
    url: `${BASE_URL}/categories/${c.value}`,
    lastModified: new Date(),
    changeFrequency: "daily",
    priority: 0.5,
  }));

  return [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/archive`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.6,
    },
    ...categoryEntries,
    ...articleEntries,
  ];
}
