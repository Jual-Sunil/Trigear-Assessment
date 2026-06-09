import { motion } from "framer-motion";
import { TaskList } from "../../components/tasks/TaskList";

export function Component() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
      className="min-h-screen bg-[#0a0a0b] text-white max-w-[1100px] mx-auto px-4 py-8 md:px-8 md:py-10"
    >
      <div className="mb-8">
        <p className="text-[10px] font-semibold tracking-[0.18em] uppercase text-zinc-600 mb-0.5">
          Workspace
        </p>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-50">Tasks</h1>
      </div>

      <TaskList />
    </motion.div>
  );
}

export default Component;
