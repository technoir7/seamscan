import { useEffect, useState } from "react";

export function useSaved(key: string) {
  const [items, setItems] = useState<string[]>([]);
  useEffect(() => {
    const saved = localStorage.getItem(key);
    if (!saved) return;
    try { setItems(JSON.parse(saved)); } catch {}
  }, [key]);
  return items;
}
