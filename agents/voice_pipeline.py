"""
Agent Layer - Dual-Path Voice Pipeline (Direct WebSocket Implementation)
核心語音 Pipeline：使用 WebSocket 直接連線 OpenAI Realtime API
"""
import asyncio
import os
import json
import base64
import websockets
from typing import Optional, Callable
from livekit import rtc, agents
from livekit.agents import JobContext, JobRequest, WorkerOptions, cli

# Database & Logic Imports
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session_maker
from services.db_manager import DBManager
from services.gcc_module import GCCModule
from agents.prompts import STUDENT_AGENT_PROMPT

# Constants
REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"
SAMPLE_RATE = 24000
CHANNELS = 1


class OpenAIRealtimeClient:
    """
    Manages the WebSocket connection to OpenAI Realtime API.
    """
    def __init__(self, api_key: str, model: str = REALTIME_MODEL):
        self.url = f"wss://api.openai.com/v1/realtime?model={model}"
        self.api_key = api_key
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_audio_delta: Optional[Callable[[bytes], None]] = None
        self.on_text_delta: Optional[Callable[[str], None]] = None
        self.on_agent_response: Optional[Callable[[str], None]] = None # Full text accumulator
        self.on_user_transcription: Optional[Callable[[str], None]] = None

    async def connect(self):
        print(f"[OpenAI] Connecting to {self.url}...")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        self.ws = await websockets.connect(self.url, additional_headers=headers)
        print("[OpenAI] Connected!")
        
        # Initialize Session
        await self.send_event({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": "alloy",
                "instructions": STUDENT_AGENT_PROMPT,
                "turn_detection": {"type": "server_vad"},
                "input_audio_transcription": {
                    "model": "whisper-1"
                }
            }
        })

    async def send_event(self, event: dict):
        if self.ws:
            await self.ws.send(json.dumps(event))

    async def send_audio_append(self, pcm_b64: str):
        """Send audio chunk to OpenAI"""
        await self.send_event({
            "type": "input_audio_buffer.append",
            "audio": pcm_b64
        })

    async def send_text(self, text: str):
        print(f"[OpenAI] Sending text: {text}")
        # 1. Add User Message
        await self.send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}]
            }
        })
        # 2. Trigger Response
        await self.send_event({"type": "response.create"})

    async def loop(self):
        """Main listening loop"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                event_type = data.get("type")

                if event_type == "response.audio.delta":
                    delta_b64 = data.get("delta")
                    if delta_b64 and self.on_audio_delta:
                        pcm_data = base64.b64decode(delta_b64)
                        if asyncio.iscoroutinefunction(self.on_audio_delta):
                            await self.on_audio_delta(pcm_data)
                        else:
                            self.on_audio_delta(pcm_data)
                
                elif event_type == "response.audio_transcript.delta":
                     # Can be used for subtitles
                     pass

                elif event_type == "response.text.delta":
                    # If using text modality response
                    delta_text = data.get("delta")
                    if delta_text and self.on_text_delta:
                         if asyncio.iscoroutinefunction(self.on_text_delta):
                            await self.on_text_delta(delta_text)
                         else:
                            self.on_text_delta(delta_text)
                
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # User voice transcription
                    transcript = data.get("transcript")
                    print(f"[OpenAI] User transcript: {transcript}")
                    if transcript and self.on_user_transcription:
                        if asyncio.iscoroutinefunction(self.on_user_transcription):
                            await self.on_user_transcription(transcript)
                        else:
                            self.on_user_transcription(transcript)
                
                elif event_type == "response.output_item.done":
                    # Capture full agent text if available (though Realtime S2S mostly uses audio)
                    item = data.get("item", {})
                    content = item.get("content", [])
                    if content:
                         for c in content:
                             if c.get("type") == "audio" and "transcript" in c:
                                 transcript = c["transcript"]
                                 if transcript and self.on_agent_response:
                                     if asyncio.iscoroutinefunction(self.on_agent_response):
                                         await self.on_agent_response(transcript)
                                     else:
                                         self.on_agent_response(transcript)

        except websockets.exceptions.ConnectionClosed:
            print("[OpenAI] WebSocket closed.")
        except Exception as e:
            print(f"[OpenAI] Error in loop: {e}")


class DualPathVoicePipeline:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.room = ctx.room
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
             raise ValueError("OPENAI_API_KEY not set")
        
        self.client = OpenAIRealtimeClient(self.api_key)
        
        # Audio Output Setup
        self.source = rtc.AudioSource(SAMPLE_RATE, CHANNELS)
        self.track = rtc.LocalAudioTrack.create_audio_track("agent_voice", self.source)
        
        # State
        self.audio_task = None
    
    async def start(self):
        print("[Pipeline] Starting...")
        
        # 1. Connect to Room
        await self.ctx.connect()
        print(f"[Pipeline] Connected to Room: {self.room.name}")
        
        # 2. Publish Audio Track
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await self.room.local_participant.publish_track(self.track, options)

        # 3. Connect to OpenAI
        await self.client.connect()
        
        # 4. Bind Callbacks
        self.client.on_audio_delta = self.handle_audio_delta
        self.client.on_agent_response = self.handle_agent_text_response
        self.client.on_user_transcription = self.handle_user_transcription
        
        # 5. Start OpenAI Loop
        self.audio_task = asyncio.create_task(self.client.loop())

        # 6. Listen for Room Events (Data Channel & Audio)
        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            asyncio.create_task(self.handle_data_packet(data))

        @self.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                print(f"[Pipeline] Subscribed to audio track from {participant.identity}")
                asyncio.create_task(self.handle_track_audio(track))

        @self.room.on("track_published")
        def on_track_published(publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
             print(f"[Pipeline] Track published by {participant.identity}: {publication.kind}")
             if publication.track and publication.track.kind == rtc.TrackKind.KIND_AUDIO:
                 print(f"[Pipeline] Audio track available, ensuring subscription...")
                 publication.set_subscribed(True)

        # 7. Check for existing tracks (in case Agent joined late)
        print(f"[Pipeline] checking existing participants: {len(self.room.remote_participants)}")
        for participant in self.room.remote_participants.values():
            for publication in participant.track_publications.values():
                print(f"[Pipeline] Found existing track: {publication.kind} from {participant.identity}")
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    if not publication.subscribed:
                         print("[Pipeline] Subscribing to existing audio track...")
                         publication.set_subscribed(True)
                    
                    if publication.track:
                        print(f"[Pipeline] Processing existing audio track from {participant.identity}")
                        asyncio.create_task(self.handle_track_audio(publication.track))



        # Wait for shutdown
        shutdown_future = asyncio.Future()
        async def on_shutdown(reason):
            print(f"[Pipeline] Shutdown requested: {reason}")
            if not shutdown_future.done():
                shutdown_future.set_result(reason)
        
        self.ctx.add_shutdown_callback(on_shutdown)
        await shutdown_future
        
        # Cleanup
        print("[Pipeline] Cleaning up...")
        
        # Cancel audio task
        if self.audio_task and not self.audio_task.done():
            self.audio_task.cancel()
            try:
                await self.audio_task
            except asyncio.CancelledError:
                print("[Pipeline] Audio task cancelled")
        
        # Close OpenAI WebSocket
        if self.client.ws:
            try:
                await self.client.ws.close()
                print("[Pipeline] OpenAI WebSocket closed")
            except Exception as e:
                print(f"[Pipeline] Error closing WebSocket: {e}")
        
        print("[Pipeline] Cleanup complete")

    async def handle_audio_delta(self, pcm_data: bytes):
        """Push audio frames to LiveKit"""
        # OpenAI sends 16-bit PCM, 24kHz
        # LiveKit AudioSource expects AudioFrame
        # Frame duration 10-20ms is ideal. 
        # Here we just push chunks as they come (assuming they are reasonable size)
        
        # Convert bytes to AudioFrame
        # 16-bit = 2 bytes per sample
        samples_count = len(pcm_data) // 2
        
        frame = rtc.AudioFrame(
            data=pcm_data,
            sample_rate=SAMPLE_RATE,
            num_channels=CHANNELS,
            samples_per_channel=samples_count
        )
        await self.source.capture_frame(frame)

    async def handle_agent_text_response(self, text: str):
        """Send Agent transcript back to frontend"""
        print(f"[Pipeline] Agent said: {text}")
        payload = json.dumps({
            "type": "agent_response",
            "text": text
        }).encode("utf-8")
        
        await self.room.local_participant.publish_data(payload, reliable=True)

    async def handle_user_transcription(self, text: str):
        """Send User transcript back to frontend"""
        # print(f"[Pipeline] User said (transcribed): {text}")
        payload = json.dumps({
            "type": "user_transcription",
            "text": text
        }).encode("utf-8")
        
        await self.room.local_participant.publish_data(payload, reliable=True)

    async def handle_data_packet(self, data: rtc.DataPacket):
        topic = data.topic
        payload = data.data.decode("utf-8")
        
        if topic == "chat-input" or topic == "lk-chat-topic":
            try:
                msg = json.loads(payload)
                user_text = ""
                # Handle different formats
                if msg.get("type") == "user_text_input":
                    user_text = msg.get("text")
                elif "message" in msg:
                    user_text = msg.get("message")
                
                if user_text:
                    print(f"[Pipeline] User Input: {user_text}")
                    await self.client.send_text(user_text)
                    
            except Exception as e:
                print(f"[Pipeline] Error parsing data: {e}")

    async def handle_track_audio(self, track: rtc.RemoteAudioTrack):
        """Forward user audio to OpenAI"""
        # Resample to 24000Hz to match OpenAI Realtime default
        audio_stream = rtc.AudioStream(track, sample_rate=24000)
        print("[Pipeline] Started listening to user audio stream...")
        
        async for frame in audio_stream:
            # frame is AudioFrameEvent, frame.frame.data is int16 bytes
            pcm_b64 = base64.b64encode(frame.frame.data).decode("utf-8")
            await self.client.send_audio_append(pcm_b64)



async def entrypoint(ctx: JobContext):
    pipeline = DualPathVoicePipeline(ctx)
    await pipeline.start()



async def request_fnc(ctx: JobRequest):
    print(f"[Debug] Received Job Request: {ctx.job.id} for room {ctx.room.name}")
    await ctx.accept()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, request_fnc=request_fnc))
