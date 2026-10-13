import { sanitizeHTML } from "../utils/sanitize";

export function About({ shop }) {
  return <div className="prose" dangerouslySetInnerHTML={{ __html: sanitizeHTML(shop.biography) }} />;
}
