"use client";

import { useState, useEffect, useRef } from "react";
import MockLogin from "../components/MockLogin";
import ClinicInfo from "../components/ClinicInfo";
import ChatInput from "../components/ChatInput";
import VerboseLog from "../components/VerboseLog";
import Dashboard from "../components/Dashboard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

type Role = "front_desk" | "vet_tech" | "vet" | "regional_manager" | "account_admin";

interface Clinic {
  id: string;
  name: string;
  color_hex: string;
  address?: string;
  is_active?: boolean;
}

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [scheduledItems, setScheduledItems] = useState<any[]>([]);
  const [patientMap, setPatientMap] = useState<Record<string, any>>({});
  const [role, setRole] = useState<Role>("front_desk");
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const sessionRef = useRef<string | null>(null);

  // Clarification state
  const [mode, setMode] = useState<"idle" | "clarifying" | "processing">("idle");
  const [pendingQuery, setPendingQuery] = useState("");


  // Wire vet follow-up agent suggestion to chat input
  useEffect(() => {
    const handler = (e: any) => setPendingQuery(e.detail.message);
    window.addEventListener("vet-suggest-message", handler);
    return () => window.removeEventListener("vet-suggest-message", handler);
  }, [setPendingQuery]);  const [agentQuestions, setAgentQuestions] = useState<string[]>([]);

  // Load patients and seed appointments on login
  const loadInitialData = async (clinicId?: string) => {
    try {
      // Load patient map
      const pRes = await fetch(`${API}/api/patients`);
      if (pRes.ok) {
        const patients = await pRes.json();
        const map: Record<string, any> = {};
        patients.forEach((p: any) => { map[p.id] = p; });
        setPatientMap(map);
      }

      // Load seeded timeblocks as items (filtered by clinic if provided)
      const tbUrl = clinicId
        ? `${API}/api/timeblocks`  // filter client-side for now
        : `${API}/api/timeblocks`;
      const tbRes = await fetch(tbUrl);
      if (tbRes.ok) {
        const tbs = await tbRes.json();
        // Filter by clinicId if selected
        const filtered = clinicId
          ? tbs.filter((t: any) => !t.clinic_id || t.clinic_id === clinicId)
          : tbs;
        setScheduledItems(filtered);
      }
    } catch {
      // Non-fatal
    }
  };

  // Load clinics and set default
  const loadClinics = async () => {
    try {
      const res = await fetch(`${API}/api/clinics`);
      if (res.ok) {
        const data: Clinic[] = await res.json();
        setClinics(data);
        if (data.length > 0) {
          const defaultClinic = data[0]; // alphabetically first (sorted by backend)
          setSelectedClinic(defaultClinic);
          document.body.style.setProperty("--clinic-color", defaultClinic.color_hex);
          return defaultClinic;
        }
      }
    } catch {
      // Non-fatal
    }
    return null;
  };

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
        // Reload patient data
        await loadInitialData();
      }
      sessionRef.current = session_id;
    } catch {
      // Backend not reachable yet — ignore
    }
  };

  useEffect(() => {
    syncSession().then(() => {
      if (isLoggedIn) {
        loadClinics().then((clinic) => loadInitialData(clinic?.id));
      }
    });
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      loadClinics().then((clinic) => loadInitialData(clinic?.id));
    }
  }, [isLoggedIn]);

  const handleClinicChange = (clinic: Clinic) => {
    setSelectedClinic(clinic);
    document.body.style.setProperty("--clinic-color", clinic.color_hex);
    loadInitialData(clinic.id);
  };

  const handleLogin = () => setShowInfo(true);

  const addLog = (entry: string) => setLogs(prev => [...prev, entry]);

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
        // Also update patient map if new patient info
        if (data.patient_id && !patientMap[data.patient_id]) {
          const pRes = await fetch(`${API}/api/patients/${data.patient_id}`);
          if (pRes.ok) {
            const p = await pRes.json();
            setPatientMap(prev => ({ ...prev, [p.id]: p }));
          }
        }

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

    // --- Fresh request: ask Vera first ---
    setMode("processing");
    setIsProcessing(true);
    setLogs(prev => [...prev, `RECEIVED: ${text}`]);

    try {
      // Route through Vera's conversational endpoint first
      const chatRes = await fetch(`${API}/api/vera/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const chatData = await chatRes.json();

      if (chatData.type === "chat" && chatData.response) {
        // Vera handled it conversationally
        setLogs(prev => [...prev, `VERA: ${chatData.response}`]);
        setIsProcessing(false);
        setMode("idle");
        return;
      }

      // Vera said this is a scheduling request — proceed with existing flow
      const clarifyRes = await fetch(`${API}/api/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: "req_demo", text }),
      });
      const clarifyData = await clarifyRes.json();

      if (clarifyData.needs_clarification) {
        setPendingQuery(text);
        setMode("clarifying");
        setIsProcessing(false);

        const partial = clarifyData.partial_parse;
        if (partial.skills?.length) {
          setLogs(prev => [...prev, `VERA (Intake): Partial parse — skill(s): ${partial.skills.join(", ")}${partial.date ? `, date: ${partial.date}` : ""}`]);
        }

        let i = 0;
        const streamQ = () => {
          if (i < clarifyData.questions.length) {
            const q = clarifyData.questions[i];
            if (q) setLogs(prev => [...prev, `VERA: ${q}`]);
            i++;
            setTimeout(streamQ, 350);
          } else {
            setAgentQuestions(clarifyData.questions.filter(Boolean));
          }
        };
        setTimeout(streamQ, 300);
        return;
      }

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
    <div style={{ display: "flex", height: "100vh", width: "100%", background: "#09090b", overflow: "hidden", fontFamily: "var(--font-geist-sans, sans-serif)" }}>
      <div style={{ display: "flex", flexDirection: "column", width: "67%", height: "100%" }}>
        <Dashboard
          scheduledItems={scheduledItems}
          patientMap={patientMap}
          role={role}
          onRoleChange={setRole}
          onLogEntry={addLog}
          selectedClinic={selectedClinic}
          onClinicChange={handleClinicChange}
        />
        <ChatInput
          onSend={handleSend}
          isProcessing={isProcessing}
          isClarifying={mode === "clarifying"}
          agentQuestions={agentQuestions}
        />
      </div>
      <div style={{ width: "33%", height: "100%" }}>
        <VerboseLog logs={logs} />
      </div>
    </div>
  );
}
