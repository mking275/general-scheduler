"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Terminal, CheckCircle, Cpu, Zap, Activity, MessageCircle,
  AlertCircle, FlaskConical, FileText, HeartPulse, Send,
} from "lucide-react";

interface LogEntry {
  text: string;
  key?: number;
}

export default function VerboseLog({ logs }: { logs: string[] }) {
  const getMeta = (log: string) => {
    if (!log) return { icon: <Terminal size={16} className="text-zinc-500 mt-1" />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-300" };

    // T035: New agent step styles
    if (log.startsWith("VERA (Intake):") || log.includes("VERA (Intake)"))
      return {
        icon: <Activity size={16} style={{ color: "#60a5fa", marginTop: "2px" }} />,
        cls: "border-blue-900/40 bg-blue-950/20",
        textCls: "text-blue-200",
        label: "VERA · Intake",
        labelColor: "#60a5fa",
      };
    if (log.startsWith("VERA (Risk):") || log.includes("VERA (Risk)"))
      return {
        icon: <HeartPulse size={16} style={{ color: "#fbbf24", marginTop: "2px" }} />,
        cls: "border-amber-900/30 bg-amber-950/15",
        textCls: "text-amber-200",
        label: "VERA · Risk",
        labelColor: "#fbbf24",
      };
    if (log.startsWith("VERA (SOAP):") || log.includes("VERA (SOAP)"))
      return {
        icon: <FileText size={16} style={{ color: "#a78bfa", marginTop: "2px" }} />,
        cls: "border-purple-900/30 bg-purple-950/15",
        textCls: "text-purple-200",
        label: "VERA · SOAP",
        labelColor: "#a78bfa",
      };
    if (log.startsWith("VERA (Follow-Up):") || log.includes("VERA (Follow-Up)"))
      return {
        icon: <Send size={16} style={{ color: "#4ade80", marginTop: "2px" }} />,
        cls: "border-emerald-900/30 bg-emerald-950/15",
        textCls: "text-emerald-200",
        label: "VERA · Follow-Up",
        labelColor: "#4ade80",
      };

    // Existing step styles
    if (log.startsWith("VERA:"))
      return { icon: <MessageCircle size={16} style={{ color: "#818cf8", marginTop: "2px" }} />, cls: "border-indigo-500/30 bg-indigo-950/40", textCls: "text-indigo-200" };
    if (log.startsWith("VERA (Intake):"))
      return { icon: <Activity size={16} style={{ color: "#60a5fa", marginTop: "2px" }} />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-300" };
    if (log.startsWith("MATCH:"))
      return { icon: <Zap size={16} style={{ color: "#c084fc", marginTop: "2px" }} />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-300" };
    if (log.startsWith("SOLVE:"))
      return { icon: <Cpu size={16} style={{ color: "#fb923c", marginTop: "2px" }} />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-300" };
    if (log.startsWith("DISPATCH:"))
      return { icon: <CheckCircle size={16} style={{ color: "#34d399", marginTop: "2px" }} />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-300" };
    if (log.startsWith("ROOM:"))
      return { icon: <FlaskConical size={16} style={{ color: "#fbbf24", marginTop: "2px" }} />, cls: "border-amber-900/20 bg-amber-950/10", textCls: "text-amber-200" };
    if (log.startsWith("ERROR:") || log.startsWith("SOLVE ERROR:"))
      return { icon: <AlertCircle size={16} style={{ color: "#f87171", marginTop: "2px" }} />, cls: "border-red-800/40 bg-red-950/30", textCls: "text-red-300" };
    // T019: CLINIC RESOLVER step style
    if (log.startsWith("VERA (Clinic):"))
      return {
        icon: <MessageCircle size={16} style={{ color: "#6366f1", marginTop: "2px" }} />,
        cls: "border-indigo-800/40 bg-indigo-950/25",
        textCls: "text-indigo-200",
        label: "VERA · Clinic",
        labelColor: "#6366f1",
      };

    return { icon: <Terminal size={16} style={{ color: "#52525b", marginTop: "2px" }} />, cls: "border-zinc-800/50 bg-zinc-900/50", textCls: "text-zinc-400" };
  };

  // T019: Bold clinic name in DISPATCH logs
  const renderLogText = (log: string) => {
    if (log.startsWith("DISPATCH:")) {
      // Bold any text after "at " that looks like a clinic name
      const match = log.match(/^(DISPATCH:.*? at )(.+?)( and | — |$)/);
      if (match) {
        return (
          <>
            {match[1]}
            <strong style={{ color: "#f4f4f5", fontWeight: 700 }}>{match[2]}</strong>
            {match[3]}
          </>
        );
      }
    }
    return log;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#09090b", borderLeft: "1px solid rgba(63,63,70,0.5)" }}>
      <div style={{
        padding: "14px 16px",
        borderBottom: "1px solid rgba(63,63,70,0.5)",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        background: "rgba(15,15,17,0.8)",
        flexShrink: 0,
      }}>
        <Terminal size={16} style={{ color: "#10b981" }} />
        <h2 style={{ fontFamily: "monospace", fontSize: "0.78rem", fontWeight: 700, color: "#10b981", letterSpacing: "0.1em", margin: 0 }}>
          VERA
        </h2>
      </div>

      <div style={{ flex: 1, padding: "12px", overflowY: "auto", fontFamily: "monospace", fontSize: "0.78rem", display: "flex", flexDirection: "column", gap: "8px" }}>
        <AnimatePresence>
          {logs.filter(Boolean).map((log, i) => {
            const meta = getMeta(log) as any;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "10px",
                  padding: "8px 10px",
                  borderRadius: "8px",
                  border: "1px solid",
                }}
                className={meta.cls}
              >
                <div style={{ flexShrink: 0 }}>{meta.icon}</div>
                <div style={{ lineHeight: 1.4 }} className={meta.textCls}>
                  {renderLogText(log)}
                </div>
              </motion.div>
            );
          })}
          {logs.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ color: "#3f3f46", fontStyle: "italic", textAlign: "center", marginTop: "40px", fontSize: "0.78rem" }}
            >
              Vera is ready. Ask her anything.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
