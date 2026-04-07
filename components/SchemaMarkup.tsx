import { Article } from "@/lib/types";

interface Props {
  article: Article;
}

export default function SchemaMarkup({ article }: Props) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    description: article.summary,
    datePublished: article.publishedAt,
    dateModified: article.publishedAt,
    author: {
      "@type": "Organization",
      name: "AInformed",
      url: "https://ainformed.dev",
    },
    publisher: {
      "@type": "Organization",
      name: "AInformed",
      url: "https://ainformed.dev",
      logo: {
        "@type": "ImageObject",
        url: "https://ainformed.dev/logo.png",
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://ainformed.dev/articles/${article.slug}`,
    },
    ...(article.imageUrl && {
      image: {
        "@type": "ImageObject",
        url: article.imageUrl,
      },
    }),
    keywords: article.tags.join(", "),
    articleSection: article.category,
    isAccessibleForFree: true,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema, null, 2) }}
    />
  );
}
