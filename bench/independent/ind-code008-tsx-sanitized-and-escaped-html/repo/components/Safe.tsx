import DOMPurify from "isomorphic-dompurify";
import { marked } from "marked";
import escapeHtml from "escape-html";

export function Safe({ md, jsonLd }: { md: string; jsonLd: object }) {
  return (
    <div>
      <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(md) as string) }} />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <footer dangerouslySetInnerHTML={{ __html: "&copy; 2026 Acme" }} />
    </div>
  );
}

export function renderTodos(list: HTMLElement, todos: { text: string }[]) {
  list.innerHTML = "";
  list.innerHTML = todos.map((t) => `<li>${escapeHtml(t.text)}</li>`).join("");
}
