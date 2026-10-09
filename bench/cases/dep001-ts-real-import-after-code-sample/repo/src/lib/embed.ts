export const reactSnippet = `
import { useEffect } from 'react';

export function Widget() {
  useEffect(() => { window.WidgetLoader?.mount('#widget'); }, []);
  return null;
}
`;
import { highlight } from "react-embed-snippet-kit";

export function renderSnippet(code: string): string {
  return highlight(code, { language: "tsx" });
}
