"use client";
import { useEffect, useRef } from "react";

export function SearchResults({ items }: { items: { id: string; title: string }[] }) {
  const results = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (!results.current) return;
    results.current.innerHTML = items.map((i) => `<li>${i.title}</li>`).join("");
  }, [items]);
  return <ul ref={results} />;
}
