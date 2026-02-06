"""
회원 데이터베이스 관리 모듈 (CSV 기반)
"""
import csv
import os
from datetime import datetime
from typing import Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "members.csv")


def load_members() -> list[dict]:
    """CSV에서 회원 목록을 로드합니다."""
    members = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            members.append(row)
    return members


def save_members(members: list[dict]) -> None:
    """회원 목록을 CSV에 저장합니다."""
    if not members:
        return
    fieldnames = members[0].keys()
    with open(DATA_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(members)


def search_member_by_name(name: str) -> dict:
    """
    이름으로 회원을 검색합니다.

    Args:
        name: 검색할 회원 이름

    Returns:
        검색 결과를 담은 딕셔너리
    """
    members = load_members()
    found = [m for m in members if m["name"] == name]

    if not found:
        return {
            "success": False,
            "message": f"'{name}' 님을 찾을 수 없습니다.",
            "member": None
        }

    member = found[0]
    if member["status"] == "withdrawn":
        return {
            "success": False,
            "message": f"'{name}' 님은 이미 탈퇴한 회원입니다.",
            "member": None
        }

    return {
        "success": True,
        "message": f"'{name}' 님의 정보를 찾았습니다.",
        "member": {
            "member_id": member["member_id"],
            "name": member["name"],
            "phone": member["phone"][-4:],  # 마지막 4자리만 표시
            "email": member["email"],
            "registered_at": member["registered_at"]
        }
    }


def verify_member(name: str, phone_last_4: str, birth_date: str) -> dict:
    """
    본인 인증을 수행합니다.

    Args:
        name: 회원 이름
        phone_last_4: 전화번호 뒷 4자리
        birth_date: 생년월일 (YYYYMMDD 또는 YYYY-MM-DD)

    Returns:
        인증 결과를 담은 딕셔너리
    """
    members = load_members()
    found = [m for m in members if m["name"] == name]

    if not found:
        return {
            "success": False,
            "verified": False,
            "message": f"'{name}' 님을 찾을 수 없습니다.",
            "member_id": None
        }

    member = found[0]

    if member["status"] == "withdrawn":
        return {
            "success": False,
            "verified": False,
            "message": f"'{name}' 님은 이미 탈퇴한 회원입니다.",
            "member_id": None
        }

    # 전화번호 뒷 4자리 확인
    actual_phone_last_4 = member["phone"].replace("-", "")[-4:]
    if phone_last_4.replace("-", "")[-4:] != actual_phone_last_4:
        return {
            "success": True,
            "verified": False,
            "message": "전화번호가 일치하지 않습니다.",
            "member_id": None
        }

    # 생년월일 확인
    normalized_birth = birth_date.replace("-", "").replace(".", "").replace("/", "")
    actual_birth = member["birth_date"].replace("-", "")
    if normalized_birth != actual_birth:
        return {
            "success": True,
            "verified": False,
            "message": "생년월일이 일치하지 않습니다.",
            "member_id": None
        }

    return {
        "success": True,
        "verified": True,
        "message": "본인 인증이 완료되었습니다.",
        "member_id": member["member_id"]
    }


def process_withdrawal(member_id: str, reason: Optional[str] = None) -> dict:
    """
    회원 탈퇴를 처리합니다.

    Args:
        member_id: 탈퇴할 회원 ID
        reason: 탈퇴 사유 (선택)

    Returns:
        처리 결과를 담은 딕셔너리
    """
    members = load_members()

    for member in members:
        if member["member_id"] == member_id:
            if member["status"] == "withdrawn":
                return {
                    "success": False,
                    "message": "이미 탈퇴 처리된 회원입니다."
                }

            member["status"] = "withdrawn"
            save_members(members)

            return {
                "success": True,
                "message": f"{member['name']} 님의 회원 탈퇴가 완료되었습니다. 그동안 이용해 주셔서 감사합니다.",
                "withdrawn_at": datetime.now().isoformat()
            }

    return {
        "success": False,
        "message": "해당 회원을 찾을 수 없습니다."
    }


# Function Calling을 위한 도구 정의
TOOLS = [
    {
        "type": "function",
        "name": "search_member_by_name",
        "description": "회원 이름으로 회원 정보를 검색합니다. 회원이 존재하는지 확인할 때 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "검색할 회원의 이름 (예: 김철수)"
                }
            },
            "required": ["name"]
        }
    },
    {
        "type": "function",
        "name": "verify_member",
        "description": "회원 본인 인증을 수행합니다. 이름, 전화번호 뒷 4자리, 생년월일로 인증합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "회원 이름"
                },
                "phone_last_4": {
                    "type": "string",
                    "description": "전화번호 뒷 4자리 (예: 5678)"
                },
                "birth_date": {
                    "type": "string",
                    "description": "생년월일 (예: 19900515 또는 1990-05-15)"
                }
            },
            "required": ["name", "phone_last_4", "birth_date"]
        }
    },
    {
        "type": "function",
        "name": "process_withdrawal",
        "description": "본인 인증이 완료된 회원의 탈퇴를 처리합니다. 반드시 verify_member로 본인 인증을 먼저 완료해야 합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "member_id": {
                    "type": "string",
                    "description": "탈퇴할 회원의 ID (예: M001)"
                },
                "reason": {
                    "type": "string",
                    "description": "탈퇴 사유 "
                }
            },
            "required": ["member_id"]
        }
    }
]


# Function name to actual function mapping
FUNCTION_MAP = {
    "search_member_by_name": search_member_by_name,
    "verify_member": verify_member,
    "process_withdrawal": process_withdrawal
}


def execute_function(name: str, arguments: dict) -> dict:
    """Function calling 결과를 실행합니다."""
    if name in FUNCTION_MAP:
        return FUNCTION_MAP[name](**arguments)
    return {"error": f"Unknown function: {name}"}
