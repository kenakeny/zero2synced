import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true, gfm: true });

// Render agent markdown to sanitized HTML for dangerouslySetInnerHTML.
export function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ""));
}
