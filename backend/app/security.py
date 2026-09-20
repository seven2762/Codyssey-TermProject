"""비밀번호 해시. 무작위 salt 생성은 Argon2 라이브러리에 맡긴다."""

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """평문 비밀번호를 Argon2 해시로 변환한다."""
    return password_hasher.hash(password)
