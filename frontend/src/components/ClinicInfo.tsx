"use client";

import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import {
  Stethoscope, DoorOpen, ChevronRight, Cpu, Brain,
  Microscope, Scissors, Radio, Shield, Zap, Heart,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface Resource {
  id: string;
  name: string;
  type: "Vet" | "Room";
  hard_skills: string[];
  attributes: string;
}

const SKILL_COLORS: Record<string, string> = {
  Surgery: "bg-red-500/15 text-red-400 border-red-500/30",
  Dental: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "General Practice": "bg-blue-500/15 text-blue-400 border-blue-500/30",
  Avian: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Exotics: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  Grooming: "bg-pink-500/15 text-pink-400 border-pink-500/30",
  "X-Ray": "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  Ultrasound: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
  Vaccination: "bg-teal-500/15 text-teal-400 border-teal-500/30",
};

const ROOM_ICONS: Record<string, React.ReactNode> = {
  Surgery: <Scissors size={22} className="text-red-400" />,
  Dental: <Microscope size={22} className="text-amber-400" />,
  "General Practice": <Stethoscope size={22} className="text-blue-400" />,
  Grooming: <Scissors size={22} className="text-pink-400" />,
  "X-Ray": <Radio size={22} className="text-cyan-400" />,
  Ultrasound: <Radio size={22} className="text-indigo-400" />,
};

function getRoomIcon(skills: string[]) {
  for (const s of skills) {
    if (ROOM_ICONS[s]) return ROOM_ICONS[s];
  }
  return <DoorOpen size={22} className="text-zinc-400" />;
}

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

export default function ClinicInfo({ onEnter }: { onEnter: () => void }) {
  const [vets, setVets] = useState<Resource[]>([]);
  const [rooms, setRooms] = useState<Resource[]>([]);

  useEffect(() => {
    fetch(`${API}/api/resources`)
      .then(r => r.json())
      .then((data: Resource[]) => {
        setVets(data.filter(r => r.type === "Vet"));
        setRooms(data.filter(r => r.type === "Room"));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#080c10] text-white overflow-y-auto">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative text-center pt-16 pb-12 px-6"
      >
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-emerald-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium px-4 py-1.5 rounded-full mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Powered by Vera · Chief of Staff
        </div>

        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-3">
          <span className="text-white">Paws &amp; Claws</span>{" "}
          <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Veterinary Clinic
          </span>
        </h1>
        <p className="text-zinc-400 max-w-2xl mx-auto text-base leading-relaxed mb-6">
          This is a fully-seeded demo practice — 9 appointments, 8 patients with complete histories, 
          multiple providers and rooms. Vera, your Chief of Staff, is already running it.
        </p>

        {/* Demo context cards */}
        <div className="max-w-2xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-3 mb-2">
          {[
            { value: "9", label: "Appointments Today" },
            { value: "8", label: "Patients with History" },
            { value: "5", label: "Role-Based Views" },
            { value: "6", label: "Exam/Surgery Rooms" },
          ].map((s, i) => (
            <div key={i} className="bg-white/[0.03] border border-white/[0.07] rounded-xl px-3 py-2.5 text-center">
              <div className="text-xl font-bold text-emerald-400">{s.value}</div>
              <div className="text-[10px] text-zinc-500 font-medium uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* How it works */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="max-w-4xl mx-auto px-6 mb-14"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: <Brain size={20} className="text-violet-400" />, label: "Vera · Intake", desc: "Parses natural language into a structured Job with skills, patient, and date." },
            { icon: <Zap size={20} className="text-amber-400" />, label: "Vera · Matching", desc: "Ranks vets and rooms by skill overlap with the job's requirements." },
            { icon: <Cpu size={20} className="text-emerald-400" />, label: "Vera · Scheduling", desc: "Walks forward through time slots enforcing hard constraints — no double-bookings." },
          ].map((step, i) => (
            <div key={i} className="flex gap-3 bg-white/[0.03] border border-white/[0.07] rounded-xl p-4">
              <div className="mt-0.5 flex-shrink-0">{step.icon}</div>
              <div>
                <p className="text-sm font-semibold text-white mb-1">{step.label}</p>
                <p className="text-xs text-zinc-500 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Staff */}
      <div className="max-w-4xl mx-auto px-6 mb-14">
        <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}>
          <div className="flex items-center gap-2 mb-5">
            <Stethoscope size={16} className="text-emerald-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">Clinical Staff</h2>
          </div>
        </motion.div>

        <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {vets.map((vet) => (
            <motion.div key={vet.id} variants={item}
              className="group relative bg-gradient-to-b from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-5 hover:border-emerald-500/40 transition-colors duration-300"
            >
              {/* Avatar placeholder */}
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center mb-4">
                <Heart size={20} className="text-emerald-400" />
              </div>

              <p className="font-semibold text-white text-base mb-0.5">{vet.name}</p>
              <p className="text-xs text-zinc-500 mb-3 leading-relaxed">{vet.attributes}</p>

              <div className="flex flex-wrap gap-1.5">
                {vet.hard_skills.map(skill => (
                  <span key={skill}
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${SKILL_COLORS[skill] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"}`}
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Rooms */}
      <div className="max-w-4xl mx-auto px-6 mb-16">
        <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}>
          <div className="flex items-center gap-2 mb-5">
            <DoorOpen size={16} className="text-cyan-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400">Rooms &amp; Facilities</h2>
          </div>
        </motion.div>

        <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {rooms.map((room) => (
            <motion.div key={room.id} variants={item}
              className="group bg-gradient-to-b from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-4 hover:border-cyan-500/30 transition-colors duration-300"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
                  {getRoomIcon(room.hard_skills)}
                </div>
                <p className="font-semibold text-white text-sm leading-tight">{room.name}</p>
              </div>

              <p className="text-xs text-zinc-500 leading-relaxed mb-3">{room.attributes}</p>

              <div className="flex flex-wrap gap-1">
                {room.hard_skills.map(skill => (
                  <span key={skill}
                    className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${SKILL_COLORS[skill] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"}`}
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* CTA */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.5 }}
        className="text-center pb-16"
      >
        <button
          onClick={onEnter}
          className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold px-8 py-3.5 rounded-xl transition-all duration-200 hover:scale-[1.03] active:scale-95 shadow-lg shadow-emerald-500/20"
        >
          Enter VetAgent
          <ChevronRight size={18} />
        </button>
        <p className="text-zinc-600 text-xs mt-3">Type anything in natural language to book an appointment</p>
      </motion.div>
    </div>
  );
}
