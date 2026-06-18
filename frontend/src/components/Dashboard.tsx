"use client";

import { motion } from "framer-motion";
import { Calendar, User, Clock, CheckCircle2, FileText } from "lucide-react";

export default function Dashboard({ scheduledItems }: { scheduledItems: any[] }) {
  return (
    <div className="flex-1 p-6 overflow-y-auto bg-zinc-950 text-white">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-zinc-100 to-zinc-500">
            Vet Clinic Schedule
          </h1>
          <p className="text-zinc-400 mt-1">Neuro-Symbolic Agentic Dispatch System</p>
        </div>
        <div className="bg-emerald-500/10 text-emerald-400 px-4 py-2 rounded-full text-sm font-medium border border-emerald-500/20 flex items-center gap-2 shadow-lg">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          System Online
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {scheduledItems.length === 0 ? (
          <div className="col-span-full py-20 flex flex-col items-center justify-center border-2 border-dashed border-zinc-800 rounded-2xl">
            <Calendar size={48} className="text-zinc-700 mb-4" />
            <p className="text-zinc-500">No appointments scheduled yet today.</p>
          </div>
        ) : (
          scheduledItems.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className="bg-gradient-to-b from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-5 shadow-xl relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-emerald-500" />
              <div className="flex items-center justify-between mb-3">
                <span className="bg-blue-500/10 text-blue-400 text-xs px-2 py-1 rounded font-medium tracking-wide uppercase">
                  {item.job.required_skills.join(", ")}
                </span>
                <CheckCircle2 size={16} className="text-emerald-500" />
              </div>

              {/* Patient / Task description */}
              <div className="mb-3 space-y-1.5">
                {item.job.procedure && (
                  <div className="flex items-center gap-2">
                    <FileText size={13} className="text-zinc-500 flex-shrink-0" />
                    <span className="text-sm font-medium text-white">{item.job.procedure}</span>
                  </div>
                )}
                {item.job.patient_name && (
                  <div className="flex items-center gap-2">
                    <User size={13} className="text-zinc-500 flex-shrink-0" />
                    <span className="text-sm text-zinc-300">Patient: <span className="text-zinc-100 font-medium">{item.job.patient_name}</span></span>
                  </div>
                )}
              </div>

              <h3 className="text-base font-semibold mb-3 flex items-center gap-2 text-zinc-300">
                <Clock size={15} className="text-zinc-500" />
                <span>
                  {new Date(item.start_time).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}
                  {" · "}
                  {new Date(item.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} – {new Date(item.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </h3>
              <div className="space-y-2 mt-4 text-sm text-zinc-400">
                {item.resources.map((res: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-2 bg-zinc-900 p-2 rounded border border-zinc-800/50">
                    <User size={14} className="text-zinc-500" />
                    <span>{res.name}</span>
                    <span className="text-xs px-1.5 py-0.5 bg-zinc-800 rounded ml-auto text-zinc-500">
                      {res.type}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
