"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Terminal, CheckCircle, Cpu, Zap, Activity, MessageCircle, AlertCircle } from "lucide-react";

export default function VerboseLog({ logs }: { logs: string[] }) {
  const getMeta = (log: string) => {
    if (!log) return { icon: <Terminal size={16} className="text-zinc-500 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
    if (log.startsWith("AGENT:"))   return { icon: <MessageCircle size={16} className="text-indigo-400 mt-1" />, cls: "border-indigo-500/30 bg-indigo-950/40" };
    if (log.startsWith("INTAKE:"))  return { icon: <Activity size={16} className="text-blue-400 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
    if (log.startsWith("MATCH:"))   return { icon: <Zap size={16} className="text-purple-400 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
    if (log.startsWith("SOLVE:"))   return { icon: <Cpu size={16} className="text-orange-400 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
    if (log.startsWith("DISPATCH:"))return { icon: <CheckCircle size={16} className="text-emerald-400 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
    if (log.startsWith("ERROR:") || log.startsWith("SOLVE ERROR:"))
                                    return { icon: <AlertCircle size={16} className="text-red-400 mt-1" />, cls: "border-red-800/40 bg-red-950/30" };
    return { icon: <Terminal size={16} className="text-zinc-500 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50" };
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border-l border-zinc-800">
      <div className="p-4 border-b border-zinc-800 flex items-center gap-2 bg-zinc-900/50">
        <Terminal size={18} className="text-emerald-400" />
        <h2 className="font-mono text-sm font-semibold text-emerald-400 tracking-wider">AGENT THOUGHT PROCESS</h2>
      </div>
      <div className="flex-1 p-4 overflow-y-auto font-mono text-sm space-y-4">
        <AnimatePresence>
          {logs.filter(Boolean).map((log, i) => {
            const { icon, cls } = getMeta(log);
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex items-start gap-3 p-3 rounded-lg border shadow-md ${cls}`}
              >
                <div className="flex-shrink-0">{icon}</div>
                <div className={`leading-relaxed ${log.startsWith("AGENT:") ? "text-indigo-200" : "text-zinc-300"}`}>
                  {log}
                </div>
              </motion.div>
            );
          })}
          {logs.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-zinc-600 italic text-center mt-10">
              Awaiting natural language scheduling request...
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
