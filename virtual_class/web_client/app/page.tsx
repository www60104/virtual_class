"use client";

import { useEffect, useState } from "react";
import { LiveKitRoom, LayoutContextProvider } from "@livekit/components-react";
import "@livekit/components-styles";
import ActiveRoom from "@/components/ActiveRoom";
import { Loader2 } from "lucide-react";

export default function Home() {
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle"); // idle | connecting | connected | error
  const [statusMsg, setStatusMsg] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const startSession = async () => {
    try {
      setStatus("connecting");
      setStatusMsg("Connecting to Quick Test Session...");

      // Call Quick Token API (Bypass Auth)
      const res = await fetch(`${API_URL}/livekit/quick_token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) throw new Error("Failed to get quick token");
      const data = await res.json();

      setToken(data.token);
      setUrl(data.url);
      setStatus("connected");

    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setStatusMsg(err.message || "An error occurred");
    }
  };

  if (status === "connected" && token && url) {
    return (
      <LayoutContextProvider>
        <LiveKitRoom
          video={false}
          audio={true} // Enable mic for voice interaction
          token={token}
          serverUrl={url}
          connect={true}
          data-lk-theme="default"
          className="h-screen w-full"
        >
          <ActiveRoom />
        </LiveKitRoom>
      </LayoutContextProvider>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-white">
      <div className="flex flex-col items-center gap-8 max-w-md w-full px-4">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tighter bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            Virtual Class
          </h1>
          <p className="text-zinc-400">
            Voice AI Agent (Quick Test Mode)
          </p>
        </div>

        <div className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
          {status === "error" && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-500/50 rounded text-red-200 text-sm">
              {statusMsg}
            </div>
          )}

          <button
            onClick={startSession}
            disabled={status === "connecting"}
            className="w-full h-12 bg-white text-black font-semibold rounded-lg hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
          >
            {status === "connecting" ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {statusMsg}
              </>
            ) : (
              "Start Conversation (No Login)"
            )}
          </button>

          <p className="text-xs text-center text-zinc-500 mt-4">
            No microphone required • Text-to-Voice Enabled
          </p>
        </div>
      </div>
    </div>
  );
}
