import { useState } from "react";

const COLORS = ["bg-rose-200", "bg-amber-200", "bg-emerald-200", "bg-sky-200"];

type Tag = { id: string; label: string; color: string };

export function TagInput() {
  const [tags, setTags] = useState<Tag[]>([]);

  function addTag(label: string) {
    const id = Math.random().toString(36).slice(2);
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    setTags((t) => [...t, { id, label, color }]);
  }

  return (
    <div>
      {tags.map((t) => (
        <span key={t.id} className={t.color}>{t.label}</span>
      ))}
      <input onKeyDown={(e) => e.key === "Enter" && addTag(e.currentTarget.value)} />
    </div>
  );
}
