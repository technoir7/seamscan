"use client";

import { useEffect, useRef } from "react";
import { supabase } from "@/lib/supabase";

export function LiveComments({ postId }: { postId: string }) {
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const channel = supabase
      .channel(`comments:${postId}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "comments" }, (payload) => {
        const comment = payload.new as { author: string; body: string };
        listRef.current?.insertAdjacentHTML(
          "beforeend",
          `<li><strong>${comment.author}</strong> ${comment.body}</li>`
        );
      })
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [postId]);

  return <ul ref={listRef} className="space-y-2" />;
}
