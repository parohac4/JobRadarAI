import { Fragment, type ReactNode } from "react";
import { safeHref } from "../utils/safeUrl";

const URL_RE = /https?:\/\/[^\s<>"')\]]+/gi;

function trimTrailingPunctuation(url: string): string {
  return url.replace(/[.,);:\]]+$/g, "");
}

export default function LinkifiedText({ text }: { text: string }) {
  const nodes: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(URL_RE)) {
    const start = match.index ?? 0;
    if (start > last) {
      nodes.push(text.slice(last, start));
    }
    const raw = match[0];
    const trimmed = trimTrailingPunctuation(raw);
    const href = safeHref(trimmed);
    if (href) {
      nodes.push(
        <a key={start} href={href} target="_blank" rel="noopener noreferrer">
          {trimmed}
        </a>,
      );
    } else {
      nodes.push(raw);
    }
    last = start + raw.length;
  }
  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  if (nodes.length === 0) {
    return <>{text}</>;
  }
  return (
    <>
      {nodes.map((node, i) => (
        <Fragment key={i}>{node}</Fragment>
      ))}
    </>
  );
}
