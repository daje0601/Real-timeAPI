#!/usr/bin/env python3
"""
음성 기반 회원 탈퇴 서비스 POC
OpenAI Real-time API를 활용한 음성 대 음성 회원탈퇴 시스템
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def check_requirements():
    """필수 요구사항을 확인합니다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정해주세요.")
        sys.exit(1)
    return api_key


def print_banner():
    """시작 배너를 출력합니다."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🎙️  TEST 음성 FAQ 서비스                                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_member_list():
    """테스트용 회원 목록을 출력합니다."""
    from member_db import load_members

    print("\n📋 테스트용 회원 목록:")
    print("-" * 60)
    print(f"{'이름':<10} {'전화번호':<15} {'생년월일':<12} {'상태':<10}")
    print("-" * 60)

    members = load_members()
    for m in members:
        status_emoji = "✅" if m["status"] == "active" else "❌"
        print(f"{m['name']:<10} {m['phone']:<15} {m['birth_date']:<12} {status_emoji} {m['status']}")

    print("-" * 60)
    print("\n💡 테스트 예시: '김철수' / 뒷번호 '5678' / 생년월일 '19900515'\n")


async def main():
    """메인 함수"""
    from realtime_client import RealtimeClient

    print_banner()
    api_key = check_requirements()
    print_member_list()

    print("🔊 마이크와 스피커가 연결되어 있는지 확인해주세요.")
    print("   시작하려면 Enter를 누르세요. (취소: Ctrl+C)")

    try:
        input()
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
        return

    print("\n🚀 서비스 시작 중...\n")

    client = RealtimeClient(api_key)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
