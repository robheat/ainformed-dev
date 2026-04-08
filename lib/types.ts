export interface Article {
  slug: string;
  title: string;
  summary: string;
  body: string;
  sourceUrl: string;
  sourceName: string;
  category: Category;
  tags: string[];
  publishedAt: string; // ISO 8601
  imageUrl?: string;
  twitterThread?: string[];
  standaloneTweet?: string;
}

export type Category =
  | "models"
  | "research"
  | "tools"
  | "policy"
  | "industry"
  | "open-source"
  | "general";

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "models", label: "Models" },
  { value: "research", label: "Research" },
  { value: "tools", label: "Tools" },
  { value: "policy", label: "Policy" },
  { value: "industry", label: "Industry" },
  { value: "open-source", label: "Open Source" },
  { value: "general", label: "General" },
];
