import { motion, AnimatePresence } from "framer-motion";
import { useLocation } from "react-router-dom";

/* ─── Variants ───────────────────────────────── */
const pageVariants = {
  initial: { opacity: 0, y: 6 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.22,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -4,
    transition: {
      duration: 0.14,
      ease: [0.45, 0, 0.55, 1],
    },
  },
};

/* ─── List stagger ───────────────────────────── */
export const listContainerVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.045,
      delayChildren: 0.05,
    },
  },
};

export const listItemVariants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  },
};

/* ─── Fade in ────────────────────────────────── */
export const fadeInVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: 0.2, ease: "easeOut" },
  },
};

/* ─── Card hover (use on motion.div wrappers) ── */
export const cardHoverProps = {
  whileHover: { y: -2, transition: { duration: 0.15, ease: [0.16, 1, 0.3, 1] } },
  whileTap:   { y: 0,  scale: 0.99, transition: { duration: 0.1 } },
};

/* ─── Components ─────────────────────────────── */

/** Wrap each page's root element with this */
export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      style={{ flex: 1, display: "flex", flexDirection: "column" }}
    >
      {children}
    </motion.div>
  );
}

/** Wrap list containers for staggered child animations */
export function AnimatedList({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <motion.div
      variants={listContainerVariants}
      initial="hidden"
      animate="show"
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}

/** Wrap individual list items */
export function AnimatedItem({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <motion.div
      variants={listItemVariants}
      className={cn("motion-list-item", className)}
      style={style}
    >
      {children}
    </motion.div>
  );
}

/** Simple fade-in wrapper */
export function FadeIn({
  children,
  delay = 0,
  className,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2, delay, ease: "easeOut" }}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}

/** AnimatePresence wrapper for route-level transitions */
export function RouteTransitions({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

// cn helper inline to avoid circular import
function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(" ");
}
