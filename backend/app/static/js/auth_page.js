// 담당 C: 로그인 및 회원가입 전용 클라이언트 스크립트

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }
});

/**
 * 공용 POST JSON 요청 헬퍼
 * CSRF 방어용 'X-Requested-With' 헤더를 필수로 포함합니다.
 */
async function postJSON(url, body) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: body === undefined ? undefined : JSON.stringify(body),
    });
}

/**
 * 로그인 폼 제출 처리
 */
async function handleLogin(e) {
    e.preventDefault();
    const uInput = document.getElementById('login-username');
    const pInput = document.getElementById('login-password');
    const errBox = document.getElementById('login-error-msg');
    const submitBtn = document.getElementById('login-btn');

    if (!uInput || !pInput || !errBox) return;

    errBox.style.display = 'none';
    errBox.textContent = '';
    uInput.classList.remove('input-error');
    pInput.classList.remove('input-error');

    const username = uInput.value.trim();
    const password = pInput.value;

    if (!username || !password) {
        errBox.textContent = '⚠️ 아이디와 비밀번호를 모두 입력해 주세요.';
        errBox.style.display = 'block';
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '로그인 중...';
    }

    try {
        const response = await postJSON('/api/login', { username, password });

        if (response.ok) {
            // 로그인 성공 시 백엔드가 서빙하는 채팅 메인 화면으로 이동
            window.location.assign('/chat');
            return;
        }

        const data = await response.json().catch(() => ({}));
        let msg = '⚠️ 로그인에 실패했습니다. 다시 시도해 주세요.';

        if (response.status === 401) {
            msg = '⚠️ 아이디 또는 비밀번호가 올바르지 않습니다.';
            pInput.classList.add('input-error');
            pInput.value = '';
            pInput.focus();
        } else if (response.status === 422) {
            if (Array.isArray(data.detail)) {
                msg = data.detail.map(item => item.msg || JSON.stringify(item)).join(', ');
            } else if (typeof data.detail === 'string') {
                msg = data.detail;
            }
        } else if (data.detail && typeof data.detail === 'string') {
            msg = data.detail;
        }

        errBox.textContent = msg;
        errBox.style.display = 'block';
    } catch (err) {
        errBox.textContent = '⚠️ 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
        errBox.style.display = 'block';
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '로그인';
        }
    }
}

/**
 * 회원가입 폼 제출 처리
 */
async function handleSignup(e) {
    e.preventDefault();
    const uInput = document.getElementById('signup-username');
    const pInput = document.getElementById('signup-password');
    const pcInput = document.getElementById('signup-password-confirm');
    const errBox = document.getElementById('signup-error-msg');
    const submitBtn = document.getElementById('signup-btn');

    if (!uInput || !pInput || !pcInput || !errBox) return;

    errBox.style.display = 'none';
    errBox.textContent = '';
    uInput.classList.remove('input-error');
    pInput.classList.remove('input-error');
    pcInput.classList.remove('input-error');

    const username = uInput.value.trim();
    const password = pInput.value;
    const passwordConfirm = pcInput.value;

    // 클라이언트 1차 유효성 검증
    const usernameRegex = /^[a-zA-Z0-9_]{3,30}$/;
    if (!usernameRegex.test(username)) {
        errBox.textContent = '⚠️ 아이디는 3~30자의 영문, 숫자, 밑줄(_)만 사용 가능합니다.';
        errBox.style.display = 'block';
        uInput.classList.add('input-error');
        uInput.focus();
        return;
    }

    if (password.length < 15 || password.length > 128) {
        errBox.textContent = '⚠️ 비밀번호는 15자 이상 128자 이하로 입력해 주세요.';
        errBox.style.display = 'block';
        pInput.classList.add('input-error');
        pInput.focus();
        return;
    }

    if (password !== passwordConfirm) {
        errBox.textContent = '⚠️ 비밀번호와 비밀번호 확인이 일치하지 않습니다.';
        errBox.style.display = 'block';
        pcInput.classList.add('input-error');
        pcInput.focus();
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '회원가입 처리 중...';
    }

    try {
        const response = await postJSON('/api/signup', { username, password });

        if (response.ok) {
            alert('회원가입이 완료되었습니다! 로그인해 주세요.');
            window.location.assign('/login');
            return;
        }

        const data = await response.json().catch(() => ({}));
        let msg = '⚠️ 회원가입에 실패했습니다. 다시 시도해 주세요.';

        if (response.status === 409) {
            msg = '⚠️ 이미 사용 중인 아이디입니다.';
            uInput.classList.add('input-error');
            uInput.focus();
        } else if (response.status === 422) {
            if (Array.isArray(data.detail)) {
                msg = data.detail.map(item => item.msg || JSON.stringify(item)).join(', ');
            } else if (typeof data.detail === 'string') {
                msg = data.detail;
            }
        } else if (data.detail && typeof data.detail === 'string') {
            msg = data.detail;
        }

        errBox.textContent = msg;
        errBox.style.display = 'block';
    } catch (err) {
        errBox.textContent = '⚠️ 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
        errBox.style.display = 'block';
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '회원가입';
        }
    }
}
