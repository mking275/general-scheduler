"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, MessageCircle } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  isProcessing: boolean;
  isClarifying?: boolean;
  agentQuestions?: string[];
}

export default function ChatInput({ onSend, isProcessing, isClarifying = false, agentQuestions = [] }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isProcessing) return;
    onSend(text);
    setText("");
  };

  const placeholder = isClarifying
    ? "Type your answer and press Enter..."
    : "Ask Vera — e.g. 'Book an emergency surgery for a Golden Retriever at 2pm'";

  const ringClass = isClarifying
    ? "focus:ring-indigo-500/60 border-indigo-500/40 animate-pulse-slow"
    : "focus:ring-blue-500/50 border-zinc-800";

  const btnClass = isClarifying
    ? "bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500"
    : "bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-500";

  return (
    <div className="bg-zinc-900 border-t border-zinc-800">
      {/* Agent question bubbles */}
      <AnimatePresence>
        {agentQuestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pt-4 space-y-2"
          >
            {agentQuestions.map((q, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.15 }}
                className="flex items-start gap-2.5"
              >
                {/* Agent avatar dot */}
                <div className="mt-1 w-5 h-5 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
                  <span style={{ fontWeight: 800, fontSize: "10px", color: "white" }}>V</span>
                </div>
                <div className="bg-indigo-950/60 border border-indigo-500/25 text-indigo-200 text-sm rounded-2xl rounded-tl-sm px-4 py-2.5 leading-relaxed max-w-[90%]">
                  {q}
                </div>
              </motion.div>
            ))}
            <p className="text-[11px] text-indigo-400/60 pl-7 pb-1">
              Vera is waiting for your response
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input row */}
      <div className="p-4">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder}
            disabled={isProcessing}
            className={`w-full bg-zinc-950 border rounded-xl pl-4 pr-12 py-4 text-white focus:outline-none focus:ring-2 transition-all shadow-inner disabled:opacity-50 ${ringClass}`}
          />
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            type="submit"
            disabled={!text.trim() || isProcessing}
            className={`absolute right-2 p-2 text-white rounded-lg transition-colors ${btnClass}`}
          >
            <Send size={18} />
          </motion.button>
        </form>
      </div>
    </div>
  );
}
