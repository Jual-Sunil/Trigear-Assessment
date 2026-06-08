import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";
import { fetchEmailById } from "../../services/api/emailApi";
import type { EmailDetail } from "../../services/api/types";
import { EmailHeader } from "../../components/emails/EmailHeader";
import { EmailSummaryCard } from "../../components/emails/EmailSummaryCard";
import { EmailBodyViewer } from "../../components/emails/EmailBodyViewer";

export function Component() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery<EmailDetail>({
    queryKey: ["email", id],
    queryFn: () => fetchEmailById(id!),
    enabled: Boolean(id),
  });

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-[820px] mx-auto px-4 py-8 md:px-8 md:py-10">
        <EmailHeader email={data} isLoading={isLoading} />

        {isError && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2.5 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400 mb-4"
          >
            <AlertCircle size={15} />
            Failed to load email. It may not exist or you may not have access.
          </motion.div>
        )}

        {!isError && (
          <>
            <EmailSummaryCard email={data} isLoading={isLoading} />
            <EmailBodyViewer email={data} isLoading={isLoading} />
          </>
        )}
      </div>
    </div>
  );
}

export default Component;
