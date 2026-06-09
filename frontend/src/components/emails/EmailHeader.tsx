import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import type { EmailDetail } from "../../services/api/types";

export interface EmailHeaderProps {
  email: EmailDetail | undefined;
  isLoading: boolean;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SkeletonHeader() {
  return (
    <div className="mb-8">
      <div className="h-3 w-24 rounded-full bg-white/[0.06] animate-pulse mb-5" />
      <div className="h-6 w-3/5 rounded-lg bg-white/[0.07] animate-pulse mb-3" />
      <div className="h-3 w-2/5 rounded-full bg-white/[0.04] animate-pulse" />
    </div>
  );
}

export function EmailHeader({ email, isLoading }: EmailHeaderProps) {
  const navigate = useNavigate();

  if (isLoading) return <SkeletonHeader />;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.25 } }}
      className="mb-8"
    >
      <button
        onClick={() => navigate("/emails")}
        className="group inline-flex items-center gap-1.5 text-[11px] font-medium text-zinc-500 hover:text-zinc-300 mb-5 transition-colors duration-150 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20 rounded"
      >
        <ArrowLeft
          size={13}
          className="group-hover:-translate-x-0.5 transition-transform duration-150"
        />
        Back to Emails
      </button>

      <h1 className="text-[1.35rem] font-semibold text-zinc-50 leading-snug tracking-tight mb-2">
        {email?.subject ?? "(No subject)"}
      </h1>

      <p className="text-[12px] text-zinc-500 leading-relaxed">
        {email?.sender_name ? (
          <>
            <span className="text-zinc-400 font-medium">{email.sender_name}</span>
            <span className="text-zinc-700 mx-1">&lt;{email.sender_email}&gt;</span>
          </>
        ) : (
          <span className="text-zinc-400">{email?.sender_email ?? ""}</span>
        )}
        {email?.received_at && (
          <>
            <span className="mx-2 text-zinc-700">·</span>
            <span>{formatDateTime(email.received_at)}</span>
          </>
        )}
      </p>
    </motion.div>
  );
}

export default EmailHeader;
