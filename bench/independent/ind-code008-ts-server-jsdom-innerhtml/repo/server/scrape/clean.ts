import { JSDOM } from "jsdom";

export function stripScripts(html: string): string {
  const dom = new JSDOM("<div id='root'></div>");
  const root = dom.window.document.getElementById("root")!;
  root.innerHTML = html;
  root.querySelectorAll("script").forEach((s) => s.remove());
  return root.innerHTML;
}
