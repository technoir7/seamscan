import { marked } from "marked";
import DOMPurify from "isomorphic-dompurify";

export const render = (md: string) => DOMPurify.sanitize(marked.parse(md) as string);
