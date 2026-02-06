"""
J.A.R.V.I.S. - TEST FAQ Voice/Chat Interface
OpenAI Real-time API powered voice and text interaction system.
"""
import os
import asyncio
import queue
import numpy as np
import gradio as gr
from dotenv import load_dotenv
from fastrtc import WebRTC, AsyncStreamHandler

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from realtime_handler import GradioRealtimeHandler, SAMPLE_RATE

# ============================================================
# JARVIS CSS Theme
# ============================================================
JARVIS_CSS = """
/* ===== GLOBAL DARK THEME ===== */
.gradio-container {
    background: linear-gradient(180deg, #06080f 0%, #0a0f1a 40%, #080d18 100%) !important;
    color: #c0d8f0 !important;
    font-family: 'Segoe UI', 'Roboto', -apple-system, sans-serif !important;
    min-height: 100vh;
}

/* Grid overlay */
.jarvis-grid-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(0, 212, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 212, 255, 0.025) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
}

/* Scan line */
.jarvis-scanline {
    position: fixed;
    left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(0, 212, 255, 0.15) 20%, rgba(0, 212, 255, 0.3) 50%, rgba(0, 212, 255, 0.15) 80%, transparent 100%);
    animation: scanmove 8s linear infinite;
    pointer-events: none;
    z-index: 9999;
}

@keyframes scanmove {
    0% { top: -2px; }
    100% { top: 100vh; }
}

/* ===== HEADER ===== */
.jarvis-header {
    text-align: center;
    padding: 20px 0 12px;
}

.header-line {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(0, 212, 255, 0.4) 30%, rgba(0, 212, 255, 0.6) 50%, rgba(0, 212, 255, 0.4) 70%, transparent 100%);
    margin: 0 auto;
    width: 80%;
}

.jarvis-title {
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 32px;
    font-weight: 300;
    letter-spacing: 12px;
    color: #00d4ff;
    text-shadow: 0 0 30px rgba(0, 212, 255, 0.6), 0 0 60px rgba(0, 212, 255, 0.2);
    margin: 12px 0 4px;
}

.jarvis-subtitle {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    letter-spacing: 4px;
    color: rgba(0, 212, 255, 0.45);
    text-transform: uppercase;
    margin: 0 0 12px;
}

/* ===== FORCE DARK ON ALL BLOCKS ===== */
.block, .wrap, .contain, .panel, .form,
.block.padded, .block.border_focus {
    background: transparent !important;
    border-color: rgba(0, 212, 255, 0.1) !important;
}

.gradio-container .main .wrap {
    background: transparent !important;
}

/* ===== BUTTONS ===== */
button.jarvis-connect-btn,
button.jarvis-disconnect-btn,
button.jarvis-send-btn {
    font-family: 'Courier New', monospace !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.3s ease !important;
    border-radius: 2px !important;
}

button.jarvis-connect-btn {
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 100, 180, 0.15) 100%) !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0, 212, 255, 0.4) !important;
}

button.jarvis-connect-btn:hover {
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.3) 0%, rgba(0, 100, 180, 0.25) 100%) !important;
    box-shadow: 0 0 25px rgba(0, 212, 255, 0.25), inset 0 0 25px rgba(0, 212, 255, 0.05) !important;
    border-color: rgba(0, 212, 255, 0.7) !important;
}

button.jarvis-disconnect-btn {
    background: rgba(255, 60, 60, 0.08) !important;
    color: #ff6b6b !important;
    border: 1px solid rgba(255, 60, 60, 0.3) !important;
}

button.jarvis-disconnect-btn:hover {
    background: rgba(255, 60, 60, 0.18) !important;
    box-shadow: 0 0 20px rgba(255, 60, 60, 0.15) !important;
    border-color: rgba(255, 60, 60, 0.6) !important;
}

button.jarvis-send-btn {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.12) 0%, rgba(0, 180, 100, 0.12) 100%) !important;
    color: #00ff88 !important;
    border: 1px solid rgba(0, 255, 136, 0.35) !important;
}

button.jarvis-send-btn:hover {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.25) 0%, rgba(0, 180, 100, 0.2) 100%) !important;
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.2) !important;
}

/* ===== TABS ===== */
.jarvis-tabs .tab-container[role="tablist"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(0, 212, 255, 0.12) !important;
    justify-content: center !important;
    gap: 0 !important;
}

.jarvis-tabs .tab-container button[role="tab"] {
    background: transparent !important;
    color: rgba(192, 216, 240, 0.4) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 14px 32px !important;
    font-family: 'Courier New', monospace !important;
    font-size: 13px !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    transition: all 0.3s ease !important;
    border-radius: 0 !important;
}

.jarvis-tabs .tab-container button[role="tab"]:hover {
    color: rgba(0, 212, 255, 0.7) !important;
    background: linear-gradient(180deg, transparent, rgba(0, 212, 255, 0.03)) !important;
}

.jarvis-tabs .tab-container button[role="tab"].selected {
    color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff !important;
    text-shadow: 0 0 15px rgba(0, 212, 255, 0.5) !important;
    background: linear-gradient(180deg, transparent 0%, rgba(0, 212, 255, 0.04) 100%) !important;
}

/* ===== ARC REACTOR (CENTERED, LARGE) ===== */
.arc-reactor-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 10px 25px;
}

.arc-reactor {
    width: 220px;
    height: 220px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}

.arc-core {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    position: absolute;
    z-index: 10;
    transition: all 0.5s ease;
}

.arc-ring {
    position: absolute;
    border-radius: 50%;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    transition: border-color 0.5s ease;
}

.arc-ring-1 {
    width: 75px; height: 75px;
    border: 2px solid rgba(0, 212, 255, 0.5);
    border-color: rgba(0, 212, 255, 0.6) transparent rgba(0, 212, 255, 0.6) transparent;
    animation: arc-spin 3s linear infinite;
}

.arc-ring-2 {
    width: 115px; height: 115px;
    border: 1.5px dashed rgba(0, 212, 255, 0.25);
    animation: arc-spin-rev 5s linear infinite;
}

.arc-ring-3 {
    width: 155px; height: 155px;
    border: 1.5px solid transparent;
    border-color: transparent rgba(0, 212, 255, 0.2) transparent rgba(0, 212, 255, 0.2);
    animation: arc-spin 8s linear infinite;
}

.arc-ring-4 {
    width: 195px; height: 195px;
    border: 1px solid rgba(0, 212, 255, 0.08);
}

/* -- IDLE STATE -- */
.arc-reactor.idle .arc-core {
    background: radial-gradient(circle, #b0e0ff 0%, #00a8e0 40%, #005580 100%);
    box-shadow: 0 0 25px rgba(0, 170, 230, 0.5), 0 0 50px rgba(0, 170, 230, 0.2);
}

/* -- SPEAKING STATE -- */
.arc-reactor.speaking .arc-core {
    background: radial-gradient(circle, #ffffff 0%, #00ffaa 35%, #00aa66 100%);
    box-shadow: 0 0 40px rgba(0, 255, 170, 0.7), 0 0 80px rgba(0, 255, 170, 0.3), 0 0 120px rgba(0, 255, 170, 0.15);
    animation: core-beat 0.6s ease-in-out infinite;
}

.arc-reactor.speaking .arc-ring-1 {
    border-color: rgba(0, 255, 170, 0.8) transparent rgba(0, 255, 170, 0.8) transparent;
    animation: arc-spin 1.2s linear infinite;
}

.arc-reactor.speaking .arc-ring-2 {
    border-color: rgba(0, 255, 170, 0.4);
    animation: arc-spin-rev 2s linear infinite;
}

.arc-reactor.speaking .arc-ring-3 {
    border-color: transparent rgba(0, 255, 170, 0.3) transparent rgba(0, 255, 170, 0.3);
    animation: arc-spin 3s linear infinite;
}

.arc-reactor.speaking .arc-ring-4 {
    border-color: rgba(0, 255, 170, 0.15);
}

.arc-reactor.speaking::before,
.arc-reactor.speaking::after {
    content: '';
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(0, 255, 170, 0.35);
    top: 50%; left: 50%;
    width: 100%; height: 100%;
    transform: translate(-50%, -50%);
}

.arc-reactor.speaking::before {
    animation: reactor-wave 1.8s ease-out infinite;
}

.arc-reactor.speaking::after {
    animation: reactor-wave 1.8s ease-out infinite 0.6s;
}

/* -- DISCONNECTED STATE -- */
.arc-reactor.disconnected .arc-core {
    background: radial-gradient(circle, #555 0%, #333 100%);
    box-shadow: 0 0 8px rgba(80, 80, 80, 0.3);
}

.arc-reactor.disconnected .arc-ring {
    border-color: rgba(80, 80, 80, 0.15) !important;
    animation-play-state: paused !important;
}

/* -- LISTENING STATE -- */
.arc-reactor.listening .arc-core {
    background: radial-gradient(circle, #e0f4ff 0%, #00c8ff 40%, #0077aa 100%);
    box-shadow: 0 0 30px rgba(0, 200, 255, 0.6), 0 0 60px rgba(0, 200, 255, 0.25);
    animation: core-beat 1.5s ease-in-out infinite;
}

/* Status label under reactor */
.reactor-label {
    margin-top: 20px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    letter-spacing: 5px;
    text-transform: uppercase;
    color: rgba(0, 212, 255, 0.55);
    transition: all 0.3s;
}

.reactor-label.active {
    color: #00ff88;
    text-shadow: 0 0 12px rgba(0, 255, 136, 0.5);
}

/* ===== CHATBOT (BOTTOM LOG) ===== */
#jarvis-log {
    background: rgba(6, 8, 15, 0.7) !important;
    border: 1px solid rgba(0, 212, 255, 0.12) !important;
    border-radius: 4px !important;
    position: relative;
}

/* HUD corners */
#jarvis-log::before {
    content: '';
    position: absolute;
    top: -1px; left: -1px;
    width: 18px; height: 18px;
    border-top: 2px solid rgba(0, 212, 255, 0.5);
    border-left: 2px solid rgba(0, 212, 255, 0.5);
    z-index: 5;
    pointer-events: none;
}

#jarvis-log::after {
    content: '';
    position: absolute;
    bottom: -1px; right: -1px;
    width: 18px; height: 18px;
    border-bottom: 2px solid rgba(0, 212, 255, 0.5);
    border-right: 2px solid rgba(0, 212, 255, 0.5);
    z-index: 5;
    pointer-events: none;
}

/* Log section label */
.log-section-label {
    font-family: 'Courier New', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: rgba(0, 212, 255, 0.4);
    text-transform: uppercase;
    text-align: center;
    padding: 12px 0 4px;
    border-top: 1px solid rgba(0, 212, 255, 0.08);
    margin-top: 8px;
}

/* ===== TEXT INPUT ===== */
.jarvis-textbox textarea {
    background: rgba(6, 8, 15, 0.8) !important;
    border: 1px solid rgba(0, 212, 255, 0.18) !important;
    border-radius: 2px !important;
    color: #d0e4f5 !important;
    font-family: 'Segoe UI', sans-serif !important;
    font-size: 14px !important;
    caret-color: #00d4ff !important;
    padding: 12px 16px !important;
    transition: all 0.3s !important;
}

.jarvis-textbox textarea:focus {
    border-color: rgba(0, 212, 255, 0.45) !important;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.08), inset 0 0 20px rgba(0, 212, 255, 0.02) !important;
}

.jarvis-textbox textarea::placeholder {
    color: rgba(120, 160, 200, 0.35) !important;
    font-style: italic;
}

/* ===== AUDIO / WEBRTC COMPONENT ===== */
.jarvis-audio {
    border: 1px solid rgba(0, 212, 255, 0.12) !important;
    border-radius: 4px !important;
    overflow: hidden;
    position: relative !important;
}

/* Contain WebRTC full-screen overlays inside their tab panel */
.wave-svg.full-screen,
.audio-container.full-screen {
    position: absolute !important;
    pointer-events: none !important;
}

.wave-svg {
    pointer-events: none !important;
}

/* ===== LABELS ===== */
label, .label-wrap span {
    color: rgba(0, 212, 255, 0.5) !important;
    font-family: 'Courier New', monospace !important;
    font-size: 10px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

/* ===== ACCORDION ===== */
.jarvis-accordion {
    border: 1px solid rgba(0, 212, 255, 0.1) !important;
    border-radius: 2px !important;
    background: rgba(6, 8, 15, 0.4) !important;
}

.jarvis-accordion .label-wrap {
    background: rgba(0, 212, 255, 0.03) !important;
}

.jarvis-accordion .prose {
    color: #90b0cc !important;
    font-size: 13px;
}

.jarvis-accordion table {
    border-color: rgba(0, 212, 255, 0.12) !important;
}

.jarvis-accordion th {
    background: rgba(0, 212, 255, 0.08) !important;
    color: #00d4ff !important;
    font-family: 'Courier New', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
}

.jarvis-accordion td {
    border-color: rgba(0, 212, 255, 0.08) !important;
    color: #90b0cc !important;
}

/* ===== SCROLLBAR ===== */
* {
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 212, 255, 0.25) transparent;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0, 212, 255, 0.25); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0, 212, 255, 0.45); }

/* ===== FOOTER HIDE ===== */
footer { display: none !important; }

/* ===== KEYFRAMES ===== */
@keyframes arc-spin {
    from { transform: translate(-50%, -50%) rotate(0deg); }
    to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes arc-spin-rev {
    from { transform: translate(-50%, -50%) rotate(0deg); }
    to { transform: translate(-50%, -50%) rotate(-360deg); }
}

@keyframes core-beat {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.25); }
}

@keyframes reactor-wave {
    0% { width: 100%; height: 100%; opacity: 0.6; }
    100% { width: 250%; height: 250%; opacity: 0; }
}
"""

# ============================================================
# HTML: Header
# ============================================================
HEADER_HTML = """
<div class="jarvis-grid-overlay"></div>
<div class="jarvis-scanline"></div>
<div class="jarvis-header">
    <div class="header-line"></div>
    <div class="jarvis-title">J.A.R.V.I.S.</div>
    <div class="jarvis-subtitle">TEST FAQ SYSTEM // REAL-TIME API v2.0</div>
    <div class="header-line"></div>
</div>
"""

# ============================================================
# HTML: Arc Reactor States
# ============================================================
_REACTOR_TPL = """
<div class="arc-reactor-wrap">
    <div class="arc-reactor {state}">
        <div class="arc-ring arc-ring-4"></div>
        <div class="arc-ring arc-ring-3"></div>
        <div class="arc-ring arc-ring-2"></div>
        <div class="arc-ring arc-ring-1"></div>
        <div class="arc-core"></div>
    </div>
    <div class="reactor-label {label_cls}">{label}</div>
</div>
"""

HTML_SPEAKING = _REACTOR_TPL.format(
    state="speaking", label_cls="active", label="&#9679; RESPONDING"
)
HTML_IDLE = _REACTOR_TPL.format(
    state="idle", label_cls="", label="&#9675; STANDBY"
)
HTML_DISCONNECTED = _REACTOR_TPL.format(
    state="disconnected", label_cls="", label="&#9676; OFFLINE"
)
HTML_LISTENING = _REACTOR_TPL.format(
    state="listening", label_cls="", label="&#9678; LISTENING"
)

LOG_DIVIDER = '<div class="log-section-label">&#9662; COMMUNICATION LOG &#9662;</div>'

# ============================================================
# Global handler
# ============================================================
handler = None


# ============================================================
# Event handlers
# ============================================================
async def connect_handler():
    """Connect to the Real-time API."""
    global handler
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-api-key-here":
        err = [{"role": "assistant", "content": "OPENAI_API_KEY not configured. Check your .env file."}]
        return (
            err, HTML_DISCONNECTED,
            gr.update(interactive=True), gr.update(interactive=False),
        )

    try:
        handler = GradioRealtimeHandler(api_key)
        await handler.connect()
        await asyncio.sleep(2)
        return (
            _format_chat_history(), HTML_IDLE,
            gr.update(interactive=False), gr.update(interactive=True),
        )
    except Exception as e:
        err = [{"role": "assistant", "content": f"Connection failed: {str(e)}"}]
        return (
            err, HTML_DISCONNECTED,
            gr.update(interactive=True), gr.update(interactive=False),
        )


async def disconnect_handler():
    """Disconnect from the Real-time API."""
    global handler
    if handler:
        await handler.disconnect()
        handler = None
    return (
        [], HTML_DISCONNECTED,
        gr.update(interactive=True), gr.update(interactive=False),
    )


class OpenAIVoiceHandler(AsyncStreamHandler):
    """WebRTC stream handler that bridges browser audio ↔ OpenAI Real-time API."""

    def __init__(self):
        super().__init__(
            expected_layout="mono",
            output_sample_rate=SAMPLE_RATE,
            input_sample_rate=48000,
        )

    async def receive(self, frame):
        """Send browser audio to OpenAI Real-time API."""
        if handler is None or not handler.is_connected:
            return
        sr, data = frame
        audio_1d = data.squeeze()
        await handler.send_audio_chunk(audio_1d, sr)

    async def emit(self):
        """Return next audio frame from OpenAI to the browser."""
        if handler is None or not handler.is_connected:
            await asyncio.sleep(0.04)
            return None
        try:
            return handler._webrtc_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.02)
            return None

    def copy(self):
        return OpenAIVoiceHandler()

    async def start_up(self):
        if handler is not None:
            handler.webrtc_active = True

    async def shutdown(self):
        if handler is not None:
            handler.webrtc_active = False


async def handle_text_submit(text):
    """Process text input from the user."""
    if handler is None or not handler.is_connected:
        return _format_chat_history(), ""
    if not text.strip():
        return _format_chat_history(), ""

    await handler.send_text_message(text)
    await asyncio.sleep(1.5)
    return _format_chat_history(), ""


def poll_updates():
    """Called periodically by gr.Timer to update chat, audio, and status."""
    if handler is None or not handler.is_connected:
        return [], None, HTML_DISCONNECTED

    audio_bytes = handler.get_and_clear_audio_output()
    audio_output = None
    if audio_bytes:
        pcm_array = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_output = (SAMPLE_RATE, pcm_array)

    status_html = HTML_SPEAKING if handler.is_speaking else HTML_IDLE
    return _format_chat_history(), audio_output, status_html


def _format_chat_history():
    """Convert handler's chat_history to Gradio Chatbot messages format."""
    if handler is None:
        return []
    messages = []
    for role, content in handler.chat_history:
        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content})
        elif role == "system":
            messages.append({"role": "assistant", "content": f"[SYS] {content}"})
    return messages


# ============================================================
# Build the Gradio UI
# ============================================================
def create_app():
    with gr.Blocks(css=JARVIS_CSS) as app:

        # ---- Header ----
        gr.HTML(HEADER_HTML)

        # ---- Connection buttons ----
        with gr.Row():
            connect_btn = gr.Button(
                "CONNECT", variant="primary", scale=1,
                elem_classes=["jarvis-connect-btn"],
            )
            disconnect_btn = gr.Button(
                "DISCONNECT", variant="stop", scale=1,
                interactive=False,
                elem_classes=["jarvis-disconnect-btn"],
            )

        # ---- Arc Reactor (centered, always visible) ----
        status_html = gr.HTML(value=HTML_DISCONNECTED)

        # ---- Tabs: input method only ----
        with gr.Tabs(elem_classes=["jarvis-tabs"]):

            with gr.Tab("VOICE MODE"):
                webrtc_audio = WebRTC(
                    mode="send-receive",
                    modality="audio",
                    label="REAL-TIME VOICE",
                    elem_classes=["jarvis-audio"],
                )
                audio_output = gr.Audio(
                    label="AI OUTPUT",
                    autoplay=True,
                    visible=False,
                )

            with gr.Tab("TEXT MODE"):
                with gr.Row():
                    text_input = gr.Textbox(
                        placeholder="Enter message... (press Enter to transmit)",
                        label="MESSAGE",
                        scale=5,
                        elem_classes=["jarvis-textbox"],
                    )
                    send_btn = gr.Button(
                        "TRANSMIT", variant="primary", scale=1,
                        elem_classes=["jarvis-send-btn"],
                    )

        # ---- Communication Log (below, always visible) ----
        gr.HTML(LOG_DIVIDER)
        chatbot = gr.Chatbot(
            label="COMMUNICATION LOG",
            height=300,
            elem_id="jarvis-log",
            type="messages",
        )

        # ---- Timer ----
        timer = gr.Timer(value=0.5)

        # ---- Member info ----
        with gr.Accordion("TEST MEMBER DATABASE", open=False, elem_classes=["jarvis-accordion"]):
            gr.Markdown(
                "| NAME | PHONE | DOB | STATUS |\n"
                "|------|-------|-----|--------|\n"
                "| Kim Chulsu | 010-1234-5678 | 1990-05-15 | ACTIVE |\n"
                "| Lee Younghee | 010-2345-6789 | 1985-08-22 | ACTIVE |\n"
                "| Park Minsu | 010-3456-7890 | 1992-12-03 | ACTIVE |\n"
                "\n**TEST**: Name `김철수` / Last 4 `5678` / DOB `19900515`"
            )

        # ---- Event wiring ----
        connect_btn.click(
            fn=connect_handler,
            outputs=[chatbot, status_html, connect_btn, disconnect_btn],
        )

        disconnect_btn.click(
            fn=disconnect_handler,
            outputs=[chatbot, status_html, connect_btn, disconnect_btn],
        )

        webrtc_audio.stream(
            fn=OpenAIVoiceHandler(),
            inputs=[webrtc_audio],
            outputs=[webrtc_audio],
            time_limit=300,
        )

        text_input.submit(
            fn=handle_text_submit,
            inputs=[text_input],
            outputs=[chatbot, text_input],
        )

        send_btn.click(
            fn=handle_text_submit,
            inputs=[text_input],
            outputs=[chatbot, text_input],
        )

        timer.tick(
            fn=poll_updates,
            outputs=[chatbot, audio_output, status_html],
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
