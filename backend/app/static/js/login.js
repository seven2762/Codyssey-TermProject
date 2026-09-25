/**
 * AskMate 로그인 화면 전용 스크립트 (login.js)
 * POST /api/login 호출 및 검증/오류 처리
 */

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    if (!form) return;

    const usernameInput = document.getElementById("loginUsername");
    const passwordInput = document.getElementById("loginPassword");
    const submitBtn = document.getElementById("loginSubmitBtn");
    const alertBox = document.getElementById("loginAlert");

    // URL에 ?registered=1 파라미터가 있으면 회원가입 완료 안내 표시
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("registered") === "1") {
        alertBox.className = "alert alert-success";
        alertBox.textContent = "회원가입이 완료되었습니다! 발급받은 아이디와 비밀번호로 로그인해 주세요.";
        alertBox.style.display = "flex";
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value; // 비밀번호는 원본 그대로 전송 (docs/API.md)

        if (!username || !password) {
            alertBox.className = "alert alert-danger";
            alertBox.textContent = "아이디와 비밀번호를 모두 입력해 주세요.";
            alertBox.style.display = "flex";
            return;
        }

        // 버튼 비활성화 및 스피너 표시
        submitBtn.disabled = true;
        const btnText = submitBtn.querySelector(".btn-text");
        const btnSpinner = submitBtn.querySelector(".btn-spinner");
        if (btnText) btnText.style.display = "none";
        if (btnSpinner) btnSpinner.style.display = "inline";
        alertBox.style.display = "none";

        const res = await apiRequest("/api/login", {
            method: "POST",
            body: { username, password },
        });

        if (res.ok) {
            window.location.assign("/chat");
        } else {
            alertBox.className = "alert alert-danger";
            alertBox.textContent = getErrorMessage(res.data, "사용자명 또는 비밀번호가 올바르지 않습니다.");
            alertBox.style.display = "flex";

            submitBtn.disabled = false;
            if (btnText) btnText.style.display = "inline";
            if (btnSpinner) btnSpinner.style.display = "none";
            passwordInput.value = "";
            passwordInput.focus();
        }
    });
});
