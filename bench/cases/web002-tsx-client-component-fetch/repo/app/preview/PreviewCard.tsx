"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export function PreviewCard() {
  const searchParams = useSearchParams();
  const url = searchParams.get("url");
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    fetch(url)
      .then((r) => r.text())
      .then(setHtml)
      .catch(() => setHtml(null));
  }, [url]);

  return <iframe srcDoc={html ?? ""} sandbox="" className="h-96 w-full rounded border" />;
}
