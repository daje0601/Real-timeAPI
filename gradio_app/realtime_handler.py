"""
OpenAI Real-time API handler adapted for Gradio integration.
Manages the WebSocket connection, audio encoding/decoding,
and event processing in a way compatible with Gradio's async model.
"""
import asyncio
import base64
import json
import queue
import numpy as np
import sys
import os
from openai import AsyncOpenAI

# Import from the parent directory's member_db module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from member_db import TOOLS, execute_function

SAMPLE_RATE = 24000  # Real-time API requires 24kHz
FRAME_SAMPLES = 960  # 40ms at 24kHz — one WebRTC output frame


class GradioRealtimeHandler:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.connection = None
        self.is_connected = False
        self.is_speaking = False
        self.chat_history = []
        self.audio_output_buffer = []
        self.transcript_buffer = ""
        self._event_task = None
        self._context_manager = None
        # WebRTC frame queue for real-time audio output
        self.webrtc_active = False
        self._webrtc_queue = queue.Queue(maxsize=300)
        self._pcm_buffer = bytearray()

    async def connect(self):
        """Establish connection to Real-time API and configure session."""
        self._context_manager = self.client.beta.realtime.connect(
            model="gpt-4o-mini-realtime-preview"
        )
        self.connection = await self._context_manager.__aenter__()
        self.is_connected = True

        await self.connection.session.update(session={
            "modalities": ["text", "audio"],
            "instructions": """당신은 TEST FAQ를 담당하는 챗봇입니다.
처음 인사할 때 "안녕하세요, TEST FAQ를 담당하는 챗봇입니다. 무엇을 도와드릴까요?"라고 말하세요.

회원 탈퇴를 원하는 경우 다음 절차를 따르세요:
1. 먼저 회원님의 성함을 여쭤봅니다.
2. search_member_by_name 함수로 회원 존재 여부를 확인합니다.
3. 본인 인증을 위해 전화번호 뒷 4자리와 생년월일을 여쭤봅니다.
4. verify_member 함수로 본인 인증을 수행합니다.
5. 인증 성공 시, 탈퇴 사유를 여쭤보고 process_withdrawal로 탈퇴를 처리합니다.

주의사항:
- 반드시 본인 인증을 완료한 후에만 탈퇴를 진행하세요.
- 생년월일은 8자리 숫자로 받아주세요 (예: 19900515)
- 친절하고 공손한 말투를 사용하세요.
- 한국어로 대화하세요.
- 짧고 간결하게 응답하세요.""",
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.95,
                "prefix_padding_ms": 200,
                "silence_duration_ms": 1200
            },
            "tools": TOOLS
        })

        # Wait for session.updated event
        async for event in self.connection:
            if event.type == "session.updated":
                break

        # Request initial greeting
        await self.connection.response.create()

        # Start background event processing
        self._event_task = asyncio.create_task(self._process_events())

    async def disconnect(self):
        """Close connection and clean up."""
        self.is_connected = False
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception:
                pass
        self.connection = None
        self._context_manager = None

    async def send_audio_chunk(self, audio_data: np.ndarray, input_sample_rate: int):
        """
        Accept audio from Gradio (numpy int16 array at some sample rate),
        resample to 24kHz if needed, base64-encode, and send to Real-time API.
        """
        if not self.is_connected or self.connection is None:
            return

        # Resample if needed
        if input_sample_rate != SAMPLE_RATE:
            duration = len(audio_data) / input_sample_rate
            num_samples = int(duration * SAMPLE_RATE)
            if num_samples == 0:
                return
            indices = np.linspace(0, len(audio_data) - 1, num_samples).astype(int)
            audio_data = audio_data[indices]

        # Ensure int16
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)

        pcm_bytes = audio_data.tobytes()
        encoded = base64.b64encode(pcm_bytes).decode("utf-8")
        await self.connection.input_audio_buffer.append(audio=encoded)

    async def send_text_message(self, text: str):
        """Send a text message to the Real-time API."""
        if not self.is_connected or self.connection is None:
            return

        self.chat_history.append(("user", text))
        await self.connection.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}]
            }
        )
        await self.connection.response.create()

    def get_and_clear_audio_output(self):
        """Retrieve accumulated audio output and clear the buffer."""
        if not self.audio_output_buffer:
            return None
        combined = b"".join(self.audio_output_buffer)
        self.audio_output_buffer.clear()
        return combined

    def _enqueue_audio_frames(self, audio_bytes: bytes):
        """Split PCM bytes into fixed-size frames and enqueue for WebRTC."""
        self._pcm_buffer.extend(audio_bytes)
        frame_bytes = FRAME_SAMPLES * 2  # 2 bytes per int16 sample
        while len(self._pcm_buffer) >= frame_bytes:
            chunk = bytes(self._pcm_buffer[:frame_bytes])
            self._pcm_buffer = self._pcm_buffer[frame_bytes:]
            frame_array = np.frombuffer(chunk, dtype=np.int16).reshape(1, -1)
            try:
                self._webrtc_queue.put_nowait((SAMPLE_RATE, frame_array))
            except queue.Full:
                try:
                    self._webrtc_queue.get_nowait()
                except queue.Empty:
                    pass
                self._webrtc_queue.put_nowait((SAMPLE_RATE, frame_array))

    def _flush_audio_frames(self):
        """Flush remaining bytes in pcm buffer as a final (possibly shorter) frame."""
        if len(self._pcm_buffer) >= 2:
            chunk = bytes(self._pcm_buffer)
            self._pcm_buffer.clear()
            frame_array = np.frombuffer(chunk, dtype=np.int16).reshape(1, -1)
            try:
                self._webrtc_queue.put_nowait((SAMPLE_RATE, frame_array))
            except queue.Full:
                pass

    def _clear_webrtc_queue(self):
        """Drain all pending frames from the WebRTC queue."""
        while not self._webrtc_queue.empty():
            try:
                self._webrtc_queue.get_nowait()
            except queue.Empty:
                break
        self._pcm_buffer.clear()

    async def _process_events(self):
        """Background loop processing server events."""
        try:
            async for event in self.connection:
                if event.type == "response.audio.delta":
                    self.is_speaking = True
                    audio_bytes = base64.b64decode(event.delta)
                    if not self.webrtc_active:
                        self.audio_output_buffer.append(audio_bytes)
                    self._enqueue_audio_frames(audio_bytes)

                elif event.type == "response.audio.done":
                    self.is_speaking = False
                    self._flush_audio_frames()

                elif event.type == "response.audio_transcript.delta":
                    self.transcript_buffer += event.delta

                elif event.type == "response.audio_transcript.done":
                    if self.transcript_buffer:
                        self.chat_history.append(("assistant", self.transcript_buffer))
                        self.transcript_buffer = ""

                elif event.type == "response.text.delta":
                    self.transcript_buffer += event.delta

                elif event.type == "response.text.done":
                    if self.transcript_buffer:
                        self.chat_history.append(("assistant", self.transcript_buffer))
                        self.transcript_buffer = ""

                elif event.type == "conversation.item.input_audio_transcription.completed":
                    if hasattr(event, "transcript") and event.transcript:
                        self.chat_history.append(("user", event.transcript))

                elif event.type == "input_audio_buffer.speech_started":
                    self.is_speaking = False
                    self.audio_output_buffer.clear()
                    self._clear_webrtc_queue()

                elif event.type == "response.function_call_arguments.done":
                    await self._handle_function_call(event)

                elif event.type == "error":
                    self.chat_history.append(
                        ("system", f"Error: {event.error.message}")
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.chat_history.append(("system", f"Connection error: {str(e)}"))
            self.is_connected = False

    async def _handle_function_call(self, event):
        """Process function call from the AI."""
        call_id = event.call_id
        name = event.name
        arguments = json.loads(event.arguments)

        self.chat_history.append(("system", f"[Function: {name}({arguments})]"))

        result = execute_function(name, arguments)

        await self.connection.conversation.item.create(
            item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False)
            }
        )
        await self.connection.response.create()
