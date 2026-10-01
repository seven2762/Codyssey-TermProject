// 회원가입 폼에서 호출할 API 예시. 요청·응답 규격: docs/API.md
async function signupUser(username, password) {
    const response = await fetch("/api/signup", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json();

    if (!response.ok) {
        // 입력 검증(422)은 배열, 중복 가입(409) 등은 문자열이다.
        const message = Array.isArray(data.detail)
            ? data.detail.map((error) => error.msg).join("\n")
            : data.detail;
        throw new Error(message);
    }

    return data; // { id, username }. 자동 로그인되지 않는다.
}

/* 회원가입 폼의 async submit 핸들러에서 사용:
event.preventDefault();
try {
    const user = await signupUser(username, password);
    // 가입 완료 안내를 표시하거나 /login으로 이동한다.
} catch (error) {
    // error.message를 textContent로 화면에 표시한다.
}
*/
