import { useRef, useState, useCallback, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Skeleton,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import EmailIcon from "@mui/icons-material/Email";
import type { EmailDetail } from "../../services/api/types";

export interface EmailBodyViewerProps {
  /** Full email record; undefined while loading. */
  email: EmailDetail | undefined;
  /** When true, renders a skeleton placeholder instead of the body. */
  isLoading: boolean;
}

type ViewMode = "html" | "text";

/**
 * Wraps raw email HTML in a minimal document shell with defensive styles.
 *
 * If the HTML already contains a full document declaration it is used as-is
 * so the email's own <head> styles and meta tags are preserved.
 * Otherwise the content is wrapped in a lightweight shell.
 *
 * @param html - Raw HTML string from the email body.
 * @returns A complete HTML document string safe for use as an iframe srcDoc.
 */
function buildSrcDoc(html: string): string {
  const trimmed = html.trim();
  const isFullDocument =
    trimmed.toLowerCase().startsWith("<!doctype") ||
    trimmed.toLowerCase().startsWith("<html");

  if (isFullDocument) {
    return html;
  }

  return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      body {
        margin: 0;
        padding: 8px 12px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #1a1a1a;
        word-break: break-word;
        overflow-wrap: break-word;
      }
      a { color: #1976d2; }
      img { max-width: 100%; height: auto; }
      table { max-width: 100%; }
    </style>
  </head>
  <body>${html}</body>
</html>`;
}

/**
 * Renders email HTML inside a sandboxed iframe using the srcDoc attribute.
 *
 * srcDoc is used instead of document.write() because the sandbox omits
 * allow-same-origin, making contentDocument inaccessible in most browsers
 * when the iframe has no src. srcDoc bypasses that restriction entirely
 * and is the correct API for injecting static HTML into a sandboxed iframe.
 *
 * The sandbox permits popups (external links open in a new tab) but blocks
 * script execution, form submission, top-level navigation, and all other
 * potentially dangerous capabilities.
 */
function HtmlBodyFrame({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeHeight, setIframeHeight] = useState(400);
  const srcDoc = buildSrcDoc(html);

  const handleLoad = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    try {
      const body = iframe.contentDocument?.body;
      if (body) {
        setIframeHeight(Math.max(body.scrollHeight + 24, 100));
      }
    } catch {
      // Cross-origin access blocked — keep default height.
    }
  }, []);

  // Re-measure after a short delay to catch images that load after the
  // iframe's load event fires and increase the document scroll height.
  useEffect(() => {
    const timer = setTimeout(() => {
      const iframe = iframeRef.current;
      if (!iframe) return;
      try {
        const body = iframe.contentDocument?.body;
        if (body && body.scrollHeight > 0) {
          setIframeHeight(body.scrollHeight + 24);
        }
      } catch {
        // Silently ignore cross-origin access errors.
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [html]);

  return (
    <Box
      component="iframe"
      ref={iframeRef}
      srcDoc={srcDoc}
      onLoad={handleLoad}
      sandbox="allow-popups allow-popups-to-escape-sandbox"
      title="Email body"
      sx={{
        width: "100%",
        height: iframeHeight,
        border: "none",
        display: "block",
        transition: "height 0.15s ease",
      }}
    />
  );
}

/**
 * Renders the plain-text email body as a preformatted block,
 * preserving whitespace and line breaks from the original message.
 */
function TextBody({ text }: { text: string }) {
  return (
    <Box
      component="pre"
      sx={{
        m: 0,
        fontFamily: "inherit",
        fontSize: "0.875rem",
        lineHeight: 1.65,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        color: "text.primary",
      }}
    >
      {text}
    </Box>
  );
}

/**
 * Renders the email body content for the detail view.
 *
 * When both body_html and body_text are available, a toggle lets the user
 * switch between the rendered HTML view and the plain-text fallback.
 * When only one format is present the toggle is hidden and that format
 * is rendered directly.
 *
 * HTML is rendered inside a sandboxed iframe via the srcDoc attribute.
 * Script execution, form submission, and navigation are all disabled.
 * dangerouslySetInnerHTML is never used.
 */
export function EmailBodyViewer({ email, isLoading }: EmailBodyViewerProps) {
  const hasHtml = Boolean(email?.body_html);
  const hasText = Boolean(email?.body_text);
  const hasBoth = hasHtml && hasText;

  const [viewMode, setViewMode] = useState<ViewMode>("html");

  const effectiveMode: ViewMode =
    hasHtml && (!hasText || viewMode === "html") ? "html" : "text";

  return (
    <Card variant="outlined">
      <CardHeader
        avatar={<EmailIcon color="action" fontSize="small" />}
        title={
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Message
          </Typography>
        }
        action={
          hasBoth ? (
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(_, val) => val && setViewMode(val)}
              size="small"
              sx={{ mr: 1 }}
            >
              <ToggleButton value="html" sx={{ fontSize: "0.7rem", py: 0.25, px: 1 }}>
                HTML
              </ToggleButton>
              <ToggleButton value="text" sx={{ fontSize: "0.7rem", py: 0.25, px: 1 }}>
                Plain
              </ToggleButton>
            </ToggleButtonGroup>
          ) : null
        }
        sx={{ pb: 0 }}
      />

      <Divider sx={{ mt: 1 }} />

      <CardContent sx={{ pt: 1.5, pb: "12px !important" }}>
        {isLoading ? (
          <Box>
            <Skeleton variant="text" width="100%" height={16} />
            <Skeleton variant="text" width="95%" height={16} />
            <Skeleton variant="text" width="88%" height={16} />
            <Skeleton variant="text" width="92%" height={16} />
            <Skeleton variant="text" width="60%" height={16} />
          </Box>
        ) : !hasHtml && !hasText ? (
          <Typography variant="body2" color="text.disabled">
            No message body available.
          </Typography>
        ) : effectiveMode === "html" && email?.body_html ? (
          <HtmlBodyFrame html={email.body_html} />
        ) : email?.body_text ? (
          <TextBody text={email.body_text} />
        ) : null}
      </CardContent>
    </Card>
  );
}

export default EmailBodyViewer;