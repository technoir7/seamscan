import { useEffect, useState } from "react";

export type CartItem = { id: string; name: string; price: number; qty: number };

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("cart");
      if (saved) setItems(JSON.parse(saved));
    } catch {}
  }, []);

  useEffect(() => {
    localStorage.setItem("cart", JSON.stringify(items));
  }, [items]);

  return { items, setItems };
}
