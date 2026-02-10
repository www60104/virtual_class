
"use client";

import {
    LiveKitRoom,
    RoomAudioRenderer,
    ControlBar,
    useTracks,
    TrackReferenceOrPlaceholder,
    useDataChannel,
    useLocalParticipant,
    useRoomContext,
    LayoutContextProvider,
    Chat,
    useChat,
} from "@livekit/components-react";
import { Track, RoomEvent } from "livekit-client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { Send, Mic, MicOff } from "lucide-react";

export default function ActiveRoom() {
    const room = useRoomContext();
    const { localParticipant } = useLocalParticipant();
    const [isMicEnabled, setIsMicEnabled] = useState(false);
    const [inputText, setInputText] = useState("");
    const { send, chatMessages } = useChat();
    const [agentMessages, setAgentMessages] = useState<any[]>([]);

    // Listen for incoming data (Agent Response)
    useEffect(() => {
        const handleDataReceived = (payload: Uint8Array, participant: any, kind: any, topic: any) => {
            const strData = new TextDecoder().decode(payload);
            console.log(`[Frontend] Received data (topic: ${topic}):`, strData);

            try {
                const msg = JSON.parse(strData);
                if (msg.type === "agent_response") {
                    setAgentMessages(prev => [...prev, {
                        message: msg.text,
                        timestamp: Date.now(),
                        from: { identity: "agent_bot", isLocal: false, name: "Voice Agent" }
                    }]);
                } else if (msg.type === "user_transcription") {
                    setAgentMessages(prev => [...prev, {
                        message: msg.text,
                        timestamp: Date.now(),
                        from: { identity: "user_voice", isLocal: true, name: "You" }
                    }]);
                }
            } catch (e) {
                // Ignore non-JSON
            }
        };

        if (room) {
            room.on(RoomEvent.DataReceived, handleDataReceived);
            return () => {
                room.off(RoomEvent.DataReceived, handleDataReceived);
            };
        }
    }, [room]);

    // Handle sending text message (Text-to-Voice trigger)
    const handleSendMessage = useCallback(async () => {
        if (!inputText.trim()) return;

        // 1. Send to LiveKit Chat (for display/history)
        await send(inputText);

        // 2. Send via Data Channel to Backend (to trigger Voice Agent)
        // We encode the text as a byte array
        const strData = JSON.stringify({
            type: "user_text_input",
            text: inputText
        });
        const data = new TextEncoder().encode(strData);

        // Publish data to the room (reliable=true for commands)
        // Publish data to the room (reliable=true for commands)
        if (localParticipant) {
            console.log(`[Frontend] Publishing data to room ${room.name} with topic "chat-input":`, strData);
            try {
                await localParticipant.publishData(data, { reliable: true, topic: "chat-input" });
                console.log("[Frontend] Data published successfully");
            } catch (error) {
                console.error("[Frontend] Failed to publish data:", error);
            }
        } else {
            console.warn("[Frontend] No localParticipant found, cannot publish data");
        }

        setInputText("");
        setInputText("");
    }, [inputText, send, localParticipant, room]);

    // Handle microphone toggle
    const toggleMicrophone = useCallback(async () => {
        if (!localParticipant) return;

        const newVal = !isMicEnabled;
        try {
            await localParticipant.setMicrophoneEnabled(newVal);
            setIsMicEnabled(newVal);
        } catch (error) {
            console.error("Failed to toggle microphone:", error);
        }
    }, [localParticipant, isMicEnabled]);


    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="flex h-screen w-full flex-col bg-neutral-900 text-white">
            {/* Top Bar: Visualization / Agent Status */}
            <div className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/20 to-neutral-900 pointer-events-none" />

                {/* Simple Visualizer Placeholder */}
                <div className="z-10 flex flex-col items-center gap-6">
                    <div className="w-32 h-32 rounded-full bg-indigo-500/20 animate-pulse flex items-center justify-center ring-4 ring-indigo-500/10">
                        <div className="w-24 h-24 rounded-full bg-indigo-500 shadow-[0_0_40px_rgba(99,102,241,0.5)] flex items-center justify-center">
                            <span className="text-4xl">🤖</span>
                        </div>
                    </div>
                    <p className="text-neutral-400 font-medium tracking-wide">
                        AI Student is listening...
                    </p>
                </div>
            </div>

            {/* Middle: Chat History */}
            <div className="h-1/3 border-t border-neutral-800 bg-neutral-900/95 backdrop-blur flex flex-col">
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {[...chatMessages, ...agentMessages].sort((a, b) => a.timestamp - b.timestamp).map((msg) => (
                        <div
                            key={msg.timestamp}
                            className={`flex ${msg.from?.isLocal ? "justify-end" : "justify-start"
                                }`}
                        >
                            <div
                                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${msg.from?.isLocal
                                    ? "bg-indigo-600 text-white rounded-br-none"
                                    : "bg-neutral-800 text-neutral-200 rounded-bl-none"
                                    }`}
                            >
                                <div className="font-bold text-xs mb-1 opacity-50">
                                    {msg.from?.name || "Unknown"}
                                </div>
                                {msg.message}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Bottom: Input Area */}
                <div className="p-4 bg-neutral-900 border-t border-neutral-800 flex gap-4 items-end">
                    <div className="flex-1 bg-neutral-800 rounded-2xl flex items-center p-2 focus-within:ring-2 focus-within:ring-indigo-500/50 transition-all">
                        <textarea
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Type your message to speak (Text-to-Voice)..."
                            className="flex-1 bg-transparent border-none focus:ring-0 text-white resize-none max-h-32 min-h-[44px] py-2.5 px-3 placeholder-neutral-500"
                            rows={1}
                        />
                    </div>

                    {/* Microphone Toggle Button */}
                    <button
                        onClick={toggleMicrophone}
                        className={`h-12 w-12 rounded-full flex items-center justify-center transition-all shadow-lg ${isMicEnabled
                                ? "bg-red-500 hover:bg-red-600 shadow-red-500/25"
                                : "bg-neutral-700 hover:bg-neutral-600"
                            }`}
                        title={isMicEnabled ? "Mute Microphone" : "Unmute Microphone"}
                    >
                        {isMicEnabled ? (
                            <Mic className="w-5 h-5 text-white animate-pulse" />
                        ) : (
                            <MicOff className="w-5 h-5 text-neutral-400" />
                        )}
                    </button>

                    <button
                        onClick={handleSendMessage}
                        disabled={!inputText.trim()}
                        className="h-12 w-12 rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 flex items-center justify-center transition-all shadow-lg hover:shadow-indigo-500/25"
                    >
                        <Send className="w-5 h-5 text-white" />
                    </button>
                </div>
            </div>

            {/* Invisible Audio Renderer for incoming voice */}
            <RoomAudioRenderer />
        </div>
    );
}
