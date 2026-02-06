# TEST 음성 FAQ 서비스 POC

OpenAI Real-time API를 활용한 음성 대 음성 FAQ 시스템

## 요구사항

- Python 3.11
- macOS (마이크 및 스피커 연결 필수)
- OpenAI API 키 (Real-time API 접근 권한 필요)

## 설치

```bash
# 가상환경 활성화
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# macOS에서 pyaudio 설치 시
brew install portaudio
pip install pyaudio
```

## 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일에 실제 API 키 입력
OPENAI_API_KEY=sk-your-api-key-here
```

> **주의**: `.env` 파일에 실제 API 키를 입력하세요. 절대 코드에 키를 하드코딩하지 마세요.

## 실행

```bash
source .venv/bin/activate
python main.py
```

## 사용 방법

1. 실행하면 배너와 테스트 회원 목록이 출력됩니다.
2. Enter를 누르면 Real-time API에 연결됩니다.
3. AI가 먼저 인사합니다: "안녕하세요, TEST FAQ를 담당하는 챗봇입니다."
4. 마이크로 말하면 음성 대 음성으로 대화가 진행됩니다.
5. 종료: `Ctrl+C`

## 테스트 회원 정보

| 이름 | 전화번호 | 생년월일 |
|------|----------|----------|
| 김철수 | 010-1234-5678 | 1990-05-15 |
| 이영희 | 010-2345-6789 | 1985-08-22 |
| 박민수 | 010-3456-7890 | 1992-12-03 |

## Function Calling

- `search_member_by_name`: 이름으로 회원 검색
- `verify_member`: 본인 인증 (이름, 전화번호 뒷4자리, 생년월일)
- `process_withdrawal`: 회원 탈퇴 처리
