import { useRef, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Mail } from "lucide-react";
import { cn } from "../../lib/utils";
import type { EmailDetail } from "../../services/api/types";

export interface EmailBodyViewerProps {
  email: EmailDetail | undefined;
  isLoading: boolean;
}

type ViewMode = "html" | "text";

function buildSrcDoc(html: string): string {
  const trimmed = html.trim();
  const isFullDocument =
    trimmed.toLowerCase().startsWith("<!doctype") ||
    trimmed.toLowerCase().startsWith("<html");

  if (isFullDocument) return html;

  return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      body {
        margin: 0;
        padding: 8px 4px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 13.5px;
        line-height: 1.65;
        color: #d4d4d8;
        background: transparent;
        word-break: break-word;
        overflow-wrap: break-word;
      }
      a { color: #818cf8; }
      img { max-width: 100%; height: auto; border-radius: 4px; }
      table { max-width: 100%; }
      blockquote { border-left: 2px solid #3f3f46; padding-left: 12px; color: #71717a; margin: 8px 0; }
    </style>
  </head>
  <body>${html}</body>
</html>`;
}

function HtmlBodyFrame({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeHeight, setIframeHeight] = useState(400);
  const srcDoc = buildSrcDoc(html);

  const measure = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    try {
      const body = iframe.contentDocument?.body;
      if (body) setIframeHeight(Math.max(body.scrollHeight + 24, 100));
    } catch {}
  }, []);

  useEffect(() => {
    const timer = setTimeout(measure, 300);
    return () => clearTimeout(timer);
  }, [html, measure]);

  return (
    <iframe
      ref={iframeRef}
      srcDoc={srcDoc}
      onLoad={measure}
      sandbox="allow-popups allow-popups-to-escape-sandbox"
      title="Email body"
      style={{ height: iframeHeight }}
      className="w-full border-none block transition-[height] duration-200"
    />
  );
}

function TextBody({ text }: { text: string }) {
  return (
    <pre className="m-0 font-[inherit] text-[13px] leading-[1.7] whitespace-pre-wrap break-words text-zinc-400">
      {text}
    </pre>
  );
}

function SkeletonBody() {
  return (
    <div className="space-y-2 py-1">
      {[100, 94, 88, 96, 78, 85, 60].map((w, i) => (
        <div
          key={i}
          className="h-3 rounded-full bg-white/[0.05] animate-pulse"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}

export function EmailBodyViewer({ email, isLoading }: EmailBodyViewerProps) {
  const hasHtml = Boolean(email?.body_html);
  const hasText = Boolean(email?.body_text);
  const hasBoth = hasHtml && hasText;

  const [viewMode, setViewMode] = useState<ViewMode>("html");
  const effectiveMode: ViewMode =
    hasHtml && (!hasText || viewMode === "html") ? "html" : "text";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3, delay: 0.1 } }}
      className="rounded-xl border border-white/[0.07] bg-white/[0.02] overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Mail size={13} className="text-zinc-600" />
          <span className="text-[12px] font-semibold text-zinc-300 tracking-tight">
            Message
          </span>
        </div>

        {hasBoth && !isLoading && (
          <div className="flex items-center rounded-lg border border-white/[0.08] bg-white/[0.03] p-0.5 gap-0.5">
            {(["html", "text"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  "text-[10px] font-semibold px-2.5 py-1 rounded-md transition-all duration-150 uppercase tracking-wide",
                  viewMode === mode
                    ? "bg-white/[0.1] text-zinc-200"
                    : "text-zinc-600 hover:text-zinc-400"
                )}
              >
                {mode === "html" ? "HTML" : "Plain"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-4">
        {isLoading ? (
          <SkeletonBody />
        ) : !hasHtml && !hasText ? (
          <p className="text-[12px] text-zinc-600 italic py-4 text-center">
            No message body available.
          </p>
        ) : effectiveMode === "html" && email?.body_html ? (
          <HtmlBodyFrame html={email.body_html} />
        ) : email?.body_text ? (
          <TextBody text={email.body_text} />
        ) : null}
      </div>
    </motion.div>
  );
}

export default EmailBodyViewer;
