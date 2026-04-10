import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { SpeedInsights } from "@vercel/speed-insights/next";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://ainformed.dev"),
  title: {
    default: "AInformed — Daily AI News",
    template: "%s | AInformed",
  },
  description:
    "The latest AI news, research, and breakthroughs — curated and summarized daily by AI. Models, tools, policy, open-source, and more.",
  keywords: [
    "AI news",
    "artificial intelligence",
    "machine learning",
    "LLM",
    "deep learning",
    "OpenAI",
    "daily AI digest",
  ],
  openGraph: {
    type: "website",
    siteName: "AInformed",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    site: "@AInformedDev",
  },
  alternates: {
    types: {
      "application/rss+xml": "https://ainformed.dev/feed.xml",
    },
  },
};

const orgSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "AInformed",
  url: "https://ainformed.dev",
  logo: "https://ainformed.dev/logo.png",
  sameAs: ["https://twitter.com/AInformedDev"],
};

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "AInformed",
  url: "https://ainformed.dev",
  description:
    "Daily AI news curated and summarized by artificial intelligence.",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://ainformed.dev/archive?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgSchema) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-neutral-950 text-neutral-100">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <SpeedInsights />
      </body>
    </html>
  );
}
