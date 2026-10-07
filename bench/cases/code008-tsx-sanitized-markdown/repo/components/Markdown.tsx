"use client";

import DOMPurify from "isomorphic-dompurify";
import { marked } from "marked";
import { useMemo } from "react";

export function Markdown({ source }: { source: string }) {
  const html = useMemo(() => DOMPurify.sanitize(marked.parse(source) as string), [source]);
  return <div className="prose" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />;
}

export function Preview({ source }: { source: string }) {
  const clean = DOMPurify.sanitize(marked.parse(source) as string);
  return <div className="prose prose-sm" dangerouslySetInnerHTML={{ __html: clean }} />;
}
