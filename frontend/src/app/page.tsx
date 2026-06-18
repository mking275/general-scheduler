"use client";

import { useState, useEffect, useRef } from "react";
import MockLogin from "../components/MockLogin";
import ClinicInfo from "../components/ClinicInfo";
import ChatInput from "../components/ChatInput";
import VerboseLog from "../components/VerboseLog";
import Dashboard from "../components/Dashboard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [scheduledItems, setScheduledItems] = useState<any[]>([]);
  const sessionRef = useRef<string | null>(null);

  // Clarification state
  const [mode, setMode] = useState<"idle" | "clarifying" | "processing">("idle");
  const [pendingQuery, setPendingQuery] = useState("");
  const [agentQuestions, setAgentQuestions] = useState<string[]>([]);

  const syncSession = async () => {
    try {
      const res = await fetch(`${API}/api/session`);
      const { session_id } = await res.json();
      if (sessionRef.current && sessionRef.current !== session_id) {
        setScheduledItems([]);
        setLogs(["SYSTEM: Backend restarted — schedule cleared."]);
        setMode("idle");
        setAgentQuestions([]);
        setPendingQuery("");
      }
      sessionRef.current = session_id;
    } catch {
      // Backend not reachable yet — ignore
    }
  };

  useEffect(() => {
    syncSession();
  }, []);

  const handleLogin = () => setShowInfo(true);

  const runSchedule = async (fullText: string) => {
    setMode("processing");
    setIsProcessing(true);
    setAgentQuestions([]);
    setLogs(prev => [...prev, `RECEIVED: Analyzing input "${fullText}"`]);

    try {
      const response = await fetch(`${API}/api/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: "req_demo", text: fullText }),
      });
      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail || data;
        const errorLogs = detail.logs || [];
        const errorMsg = detail.error || "Failed to schedule.";
        setLogs(prev => [...prev, ...errorLogs, `ERROR: ${errorMsg}`]);
      } else {
        let index = 0;
        const processLog = () => {
          if (index < data.verbose_log.length) {
            setLogs(prev => [...prev, data.verbose_log[index]]);
            index++;
            setTimeout(processLog, 400);
          } else {
            setScheduledItems(prev => [...prev, data]);
            setIsProcessing(false);
            setMode("idle");
            setPendingQuery("");
          }
        };
        setTimeout(processLog, 400);
        return;
      }
    } catch {
      setLogs(prev => [...prev, "ERROR: Network or Server Error. Ensure backend is running on port 8080."]);
    }
    setIsProcessing(false);
    setMode("idle");
    setPendingQuery("");
  };

  const handleSend = async (text: string) => {
    await syncSession();

    // --- Answering a clarifying question ---
    if (mode === "clarifying") {
      const fullText = `${pendingQuery}. ${text}`;
      setLogs(prev => [...prev, `USER: ${text}`]);
      await runSchedule(fullText);
      return;
    }

    // --- Fresh request: check for ambiguity first ---
    setMode("processing");
    setIsProcessing(true);
    setLogs([`RECEIVED: Analyzing input "${text}"`]);

    try {
      const clarifyRes = await fetch(`${API}/api/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: "req_demo", text }),
      });
      const clarifyData = await clarifyRes.json();

      if (clarifyData.needs_clarification) {
        // Enter clarifying mode — stream questions into log + bubbles
        setPendingQuery(text);
        setMode("clarifying");
        setIsProcessing(false);

        const partial = clarifyData.partial_parse;
        if (partial.skills?.length) {
          setLogs(prev => [...prev, `INTAKE: Partial parse — skill(s): ${partial.skills.join(", ")}${partial.date ? `, date: ${partial.date}` : ""}`]);
        }

        // Stream questions into log with delay, then set bubbles
        let i = 0;
        const streamQ = () => {
          if (i < clarifyData.questions.length) {
            setLogs(prev => [...prev, `AGENT: ${clarifyData.questions[i]}`]);
            i++;
            setTimeout(streamQ, 350);
          } else {
            setAgentQuestions(clarifyData.questions);
          }
        };
        setTimeout(streamQ, 300);
        return;
      }

      // No clarification needed — proceed directly
      await runSchedule(text);
    } catch {
      setLogs(prev => [...prev, "ERROR: Network or Server Error. Ensure backend is running on port 8080."]);
      setIsProcessing(false);
      setMode("idle");
    }
  };

  if (!showInfo && !isLoggedIn) {
    return <MockLogin onLogin={handleLogin} />;
  }

  if (showInfo && !isLoggedIn) {
    return <ClinicInfo onEnter={() => { setShowInfo(false); setIsLoggedIn(true); }} />;
  }

  return (
    <div className="flex h-screen w-full bg-zinc-950 overflow-hidden font-sans">
      <div className="flex flex-col w-2/3 h-full">
        <Dashboard scheduledItems={scheduledItems} />
        <ChatInput
          onSend={handleSend}
          isProcessing={isProcessing}
          isClarifying={mode === "clarifying"}
          agentQuestions={agentQuestions}
        />
      </div>
      <div className="w-1/3 h-full">
        <VerboseLog logs={logs} />
      </div>
    </div>
  );
}
