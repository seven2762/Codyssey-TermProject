/**
 * AskMate 회원가입 화면 전용 스크립트 (signup.js)
 * POST /api/signup 호출, 클라이언트 검증, 중복(409) 처리
 */

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("signupForm");
    if (!form) return;

    const usernameInput = document.getElementById("signupUsername");
    const passwordInput = document.getElementById("signupPassword");
    const passwordConfirmInput = document.getElementById("signupPasswordConfirm");
    const passwordMatchHint = document.getElementById("passwordMatchHint");
    const submitBtn = document.getElementById("signupSubmitBtn");
    const alertBox = document.getElementById("signupAlert");

    // 비밀번호 실시간 일치 검증 힌트
    function checkPasswordMatch() {
        const pw = passwordInput.value;
        const confirm = passwordConfirmInput.value;
        if (!confirm) {
            passwordMatchHint.textContent = "";
            passwordMatchHint.className = "form-hint";
            return;
        }
        if (pw === confirm) {
            passwordMatchHint.textContent = "✓ 비밀번호가 일치합니다.";
            passwordMatchHint.className = "form-hint hint-success";
        } else {
            passwordMatchHint.textContent = "✗ 비밀번호가 일치하지 않습니다.";
            passwordMatchHint.className = "form-hint hint-error";
        }
    }

    passwordInput.addEventListener("input", checkPasswordMatch);
    passwordConfirmInput.addEventListener("input", checkPasswordMatch);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const rawUsername = usernameInput.value.trim();
        const username = rawUsername.toLowerCase(); // 소문자로 통일 (docs/FRONTEND.md)
        const password = passwordInput.value; // 비밀번호는 trim() 금지
        const passwordConfirm = passwordConfirmInput.value;

        // 클라이언트 유효성 검사
        const usernamePattern = /^[a-zA-Z0-9_]{3,30}$/;
        if (!usernamePattern.test(username)) {
            alertBox.className = "alert alert-danger";
            alertBox.textContent = "아이디는 3~30자의 영문, 숫자, 밑줄(_)만 사용할 수 있습니다.";
            alertBox.style.display = "flex";
            usernameInput.focus();
            return;
        }

        if (password.length < 8 || password.length > 128) {
            alertBox.className = "alert alert-danger";
            alertBox.textContent = "비밀번호는 8자 이상 128자 이하로 입력해 주세요.";
            alertBox.style.display = "flex";
            passwordInput.focus();
            return;
        }

        if (password !== passwordConfirm) {
            alertBox.className = "alert alert-danger";
            alertBox.textContent = "비밀번호와 비밀번호 확인 입력값이 일치하지 않습니다.";
            alertBox.style.display = "flex";
            passwordConfirmInput.focus();
            return;
        }

        // 제출 중 상태 변경
        submitBtn.disabled = true;
        const btnText = submitBtn.querySelector(".btn-text");
        const btnSpinner = submitBtn.querySelector(".btn-spinner");
        if (btnText) btnText.style.display = "none";
        if (btnSpinner) btnSpinner.style.display = "inline";
        alertBox.style.display = "none";

        // 요청에는 username과 password만 보냄 (docs/FRONTEND.md)
        const res = await apiRequest("/api/signup", {
            method: "POST",
            body: { username, password },
        });

        if (res.status === 201) {
            // 회원가입 성공: 자동 로그인하지 않고 로그인 화면으로 이동
            alertBox.className = "alert alert-success";
            alertBox.textContent = "회원가입이 완료되었습니다! 로그인 페이지로 이동합니다...";
            alertBox.style.display = "flex";
            setTimeout(() => {
                window.location.assign("/login?registered=1");
            }, 600);
        } else {
            alertBox.className = "alert alert-danger";
            if (res.status === 409) {
                alertBox.textContent = "이미 사용 중인 사용자명입니다.";
            } else {
                alertBox.textContent = getErrorMessage(res.data, "회원가입에 실패했습니다.");
            }
            alertBox.style.display = "flex";

            submitBtn.disabled = false;
            if (btnText) btnText.style.display = "inline";
            if (btnSpinner) btnSpinner.style.display = "none";
        }
    });
});
