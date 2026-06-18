"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function MockLogin({ onLogin }: { onLogin: () => void }) {
  const [loading, setLoading] = useState(false);

  const handleLogin = () => {
    setLoading(true);
    setTimeout(() => {
      onLogin();
    }, 1000);
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-zinc-950 text-white">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md p-8 bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl backdrop-blur-xl"
      >
        <h1 className="text-3xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
          Agentic Scheduler
        </h1>
        <p className="text-zinc-400 mb-8">Sign in to the Veterinary Management System.</p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Email</label>
            <input 
              type="email" 
              disabled 
              value="demo@clinic.com" 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2 text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Password</label>
            <input 
              type="password" 
              disabled 
              value="••••••••" 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2 text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleLogin}
            disabled={loading}
            className="w-full mt-4 bg-white text-black font-semibold rounded-lg px-4 py-3 flex items-center justify-center hover:bg-zinc-200 transition-colors"
          >
            {loading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-5 h-5 border-2 border-black border-t-transparent rounded-full"
              />
            ) : (
              "Sign In (Demo)"
            )}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
