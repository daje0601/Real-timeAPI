"""
OpenAI Real-time API 클라이언트 모듈 (공식 라이브러리 사용)
"""
import asyncio
import base64
import json
import pyaudio
from openai import AsyncOpenAI
from member_db import TOOLS, execute_function

# 오디오 설정
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 24000  # Real-time API는 24kHz 사용

# 디버그 모드
DEBUG = False


class RealtimeClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.connection = None
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.is_running = False
        self.is_playing = False
        self.audio_queue = asyncio.Queue()

    def start_audio_streams(self):
        """오디오 입출력 스트림을 시작합니다."""
        self.input_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        self.output_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK
        )

    async def send_audio(self):
        """마이크 입력을 전송합니다."""
        read_size = int(SAMPLE_RATE * 0.02)  # 20ms chunks

        while self.is_running:
            try:
                if self.input_stream and not self.is_playing:
                    data = self.input_stream.read(read_size, exception_on_overflow=False)
                    encoded = base64.b64encode(data).decode("utf-8")
                    await self.connection.input_audio_buffer.append(audio=encoded)

                await asyncio.sleep(0.01)
            except Exception as e:
                if self.is_running:
                    print(f"오디오 전송 오류: {e}")
                break

    async def play_audio(self):
        """오디오 큐에서 데이터를 재생합니다."""
        while self.is_running:
            try:
                audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                self.output_stream.write(audio_data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"오디오 재생 오류: {e}")

    async def handle_events(self):
        """서버 이벤트를 처리합니다."""
        async for event in self.connection:
            if DEBUG:
                print(f"[DEBUG] Event: {event.type}")

            if event.type == "session.created":
                print("✓ 세션이 생성되었습니다.")

            elif event.type == "session.updated":
                print("✓ 세션 설정 완료")
                # 초기 인사 요청
                await self.send_initial_greeting()

            elif event.type == "input_audio_buffer.speech_started":
                if DEBUG:
                    print("[DEBUG] 음성 입력 시작")
                self.is_playing = False
                # 오디오 큐 비우기
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except:
                        break

            elif event.type == "input_audio_buffer.speech_stopped":
                if DEBUG:
                    print("[DEBUG] 음성 입력 종료")

            elif event.type == "response.audio.delta":
                # 음성 응답 수신
                self.is_playing = True
                audio_bytes = base64.b64decode(event.delta)
                await self.audio_queue.put(audio_bytes)

            elif event.type == "response.audio.done":
                self.is_playing = False
                # AI 응답 후 입력 버퍼 비우기 (이전 소음 제거)
                await self.connection.input_audio_buffer.clear()

            elif event.type == "response.created":
                # AI 응답 시작 시 줄바꿈
                print("\n🤖 ", end="", flush=True)

            elif event.type == "response.audio_transcript.delta":
                # AI 응답 텍스트 출력
                print(f"\033[94m{event.delta}\033[0m", end="", flush=True)

            elif event.type == "response.audio_transcript.done":
                print()  # 줄바꿈

            elif event.type == "conversation.item.input_audio_transcription.completed":
                # 사용자 음성 인식 결과 (출력하지 않음)
                pass

            elif event.type == "response.function_call_arguments.done":
                await self.handle_function_call(event)

            elif event.type == "error":
                print(f"\n❌ 오류: {event.error.message}")
                if DEBUG:
                    print(f"   코드: {event.error.code}")

    async def handle_function_call(self, event):
        """Function calling을 처리합니다."""
        call_id = event.call_id
        name = event.name
        arguments = json.loads(event.arguments)

        print(f"\n⚙️  함수 호출: {name}")
        print(f"   인자: {arguments}")

        # 함수 실행
        result = execute_function(name, arguments)
        print(f"   결과: {result}")

        # 결과 전송
        await self.connection.conversation.item.create(
            item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False)
            }
        )

        # 응답 생성 요청
        await self.connection.response.create()

    async def send_initial_greeting(self):
        """AI가 먼저 인사하도록 요청합니다."""
        print("\n🎤 말씀해 주세요. (종료: Ctrl+C)\n")

        # AI가 먼저 인사하도록 응답 생성 요청
        await self.connection.response.create()

    async def run(self):
        """클라이언트를 실행합니다."""
        self.is_running = True

        try:
            print("🔗 API 연결 중...")

            async with self.client.beta.realtime.connect(
                model="gpt-realtime"
            ) as conn:
                self.connection = conn
                print("✓ API 연결 완료")

                # 세션 설정
                await conn.session.update(
                    session={
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
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.95,  # 0.0~1.0, 거의 최대치
                            "prefix_padding_ms": 200,
                            "silence_duration_ms": 1200  # 말 끝난 후 대기 시간
                        },
                        "tools": TOOLS
                    }
                )

                # 오디오 스트림 시작
                self.start_audio_streams()

                # 태스크 실행
                await asyncio.gather(
                    self.send_audio(),
                    self.play_audio(),
                    self.handle_events()
                )

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
        except Exception as e:
            print(f"\n연결 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def cleanup(self):
        """리소스를 정리합니다."""
        self.is_running = False

        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()

        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()

        self.audio.terminate()
