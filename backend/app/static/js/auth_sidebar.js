// 담당 C: 사용자 인증, 로그인/회원가입 모달, 사이드바 대화 기록 관리 담당

let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
    bindGlobalEvents();
    checkAuthStatus();
});

function bindGlobalEvents() {
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            if (typeof resetChatWindow === 'function') resetChatWindow();
        });
    }

    const guestOverlay = document.getElementById('guest-input-overlay');
    if (guestOverlay) {
        guestOverlay.addEventListener('click', () => openModal('login-modal'));
    }

    document.querySelectorAll('[data-close]').forEach((btn) => {
        btn.addEventListener('click', () => closeModal(btn.dataset.close));
    });

    const signupLink = document.getElementById('signup-link');
    if (signupLink) {
        signupLink.addEventListener('click', (e) => {
            e.preventDefault();
            switchModal('login-modal', 'signup-modal');
        });
    }

    const loginLink = document.getElementById('login-link');
    if (loginLink) {
        loginLink.addEventListener('click', (e) => {
            e.preventDefault();
            switchModal('signup-modal', 'login-modal');
        });
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);

    const signupForm = document.getElementById('signup-form');
    if (signupForm) signupForm.addEventListener('submit', handleSignup);
}

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/me', { method: 'GET' });
        if (response.ok) {
            const data = await response.json();
            if (data && data.username) {
                currentUser = data.username;
                setLoggedInUI(currentUser);
                loadHistoryIndex();
                return;
            }
        }
    } catch (e) {
        // 에러 시 UI를 비로그인 상태로 자연스럽게 표시한다.
    }
    setGuestUI();
}

function setLoggedInUI(username) {
    const statusEl = document.getElementById('header-user-status');
    if (statusEl) statusEl.textContent = `${username}님 접속 중`;

    const profileEl = document.getElementById('user-profile-area');
    if (profileEl) {
        profileEl.innerHTML = '';

        const userSpan = document.createElement('span');
        userSpan.innerHTML = `👤 <strong>${escapeHTML(username)}</strong>`;

        const logoutLink = document.createElement('a');
        logoutLink.href = '#';
        logoutLink.className = 'btn-link';
        logoutLink.textContent = '로그아웃';
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            handleLogout();
        });

        profileEl.appendChild(userSpan);
        profileEl.appendChild(logoutLink);
    }

    const overlay = document.getElementById('guest-input-overlay');
    if (overlay) overlay.style.display = 'none';

    const input = document.getElementById('chat-input');
    if (input) input.disabled = false;

    const btn = document.getElementById('send-btn');
    if (btn) btn.disabled = false;
}

function setGuestUI() {
    currentUser = null;
    const statusEl = document.getElementById('header-user-status');
    if (statusEl) statusEl.textContent = '비로그인 상태';

    const profileEl = document.getElementById('user-profile-area');
    if (profileEl) {
        profileEl.innerHTML = '';
        const msgSpan = document.createElement('span');
        msgSpan.textContent = '로그인이 필요합니다';

        const loginLink = document.createElement('a');
        loginLink.href = '#';
        loginLink.className = 'btn-link';
        loginLink.textContent = '로그인';
        loginLink.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('login-modal');
        });

        profileEl.appendChild(msgSpan);
        profileEl.appendChild(loginLink);
    }

    const overlay = document.getElementById('guest-input-overlay');
    if (overlay) overlay.style.display = 'flex';

    const input = document.getElementById('chat-input');
    if (input) input.disabled = true;

    const btn = document.getElementById('send-btn');
    if (btn) btn.disabled = true;

    const historyList = document.getElementById('history-list');
    if (historyList) {
        historyList.innerHTML = '<p>로그인 후 기록 확인 가능</p>';
    }
}

function escapeHTML(str) {
    return String(str).replace(/[&<>"']/g, (m) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
}

async function loadHistoryIndex() {
    if (!currentUser) return;
    const historyList = document.getElementById('history-list');
    if (!historyList) return;

    try {
        const response = await fetch('/api/me/chats', { method: 'GET' });
        if (!response.ok) {
            historyList.innerHTML = '<p>이전 대화가 없습니다.</p>';
            return;
        }

        const chats = await response.json().catch(() => []);
        historyList.innerHTML = '';

        if (!Array.isArray(chats) || chats.length === 0) {
            historyList.innerHTML = '<p>이전 대화가 없습니다.</p>';
            return;
        }

        chats.forEach(chat => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.textContent = `💬 ${chat.question}`;
            item.addEventListener('click', () => {
                const welcome = document.getElementById('welcome-card');
                if (welcome) welcome.remove();
                if (typeof appendMessage === 'function') {
                    appendMessage('user', chat.question);
                    appendMessage('ai', chat.answer || '답변 없음');
                    scrollToBottom();
                }
            });
            historyList.appendChild(item);
        });
    } catch (e) {
        historyList.innerHTML = '<p>대화 기록을 불러오지 못했습니다.</p>';
    }
}

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'flex';
}
function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}
function switchModal(fromId, toId) {
    closeModal(fromId);
    openModal(toId);
}

async function handleLogin(e) {
    e.preventDefault();
    const uInput = document.getElementById('login-username');
    const pInput = document.getElementById('login-password');
    const errBox = document.getElementById('login-error-msg');

    if (!errBox || !uInput || !pInput) return;

    errBox.style.display = 'none';
    pInput.classList.remove('input-error');

    try {
        // postJSON 헬퍼 사용 — CSRF 헤더 자동 포함
        const response = await postJSON('/api/login', {
            username: uInput.value.trim(),
            password: pInput.value
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            let msg = '⚠️ 아이디 또는 비밀번호가 올바르지 않습니다.';
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    msg = data.detail.map(item => item.msg || JSON.stringify(item)).join(', ');
                } else if (typeof data.detail === 'string') {
                    msg = data.detail;
                }
            }
            errBox.textContent = msg;
            errBox.style.display = 'block';
            pInput.classList.add('input-error');
            pInput.value = '';
            pInput.focus();
            return;
        }

        closeModal('login-modal');
        uInput.value = '';
        pInput.value = '';
        checkAuthStatus();
    } catch (err) {
        errBox.textContent = '⚠️ 네트워크 오류가 발생했습니다.';
        errBox.style.display = 'block';
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const uInput = document.getElementById('signup-username');
    const pInput = document.getElementById('signup-password');
    const pcInput = document.getElementById('signup-password-confirm');
    const errBox = document.getElementById('signup-error-msg');

    if (!errBox || !uInput || !pInput || !pcInput) return;

    errBox.style.display = 'none';

    if (pInput.value !== pcInput.value) {
        errBox.textContent = '⚠️ 비밀번호가 일치하지 않습니다.';
        errBox.style.display = 'block';
        return;
    }

    try {
        // postJSON 헬퍼 사용 — CSRF 헤더 자동 포함
        const response = await postJSON('/api/signup', {
            username: uInput.value.trim(),
            password: pInput.value
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            let msg = '⚠️ 회원가입 실패. 다시 시도해 주세요.';
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    msg = data.detail.map(item => item.msg || JSON.stringify(item)).join(', ');
                } else if (typeof data.detail === 'string') {
                    msg = data.detail;
                }
            }
            errBox.textContent = msg;
            errBox.style.display = 'block';
            return;
        }

        alert('회원가입이 완료되었습니다! 로그인해 주세요.');
        uInput.value = '';
        pInput.value = '';
        pcInput.value = '';
        switchModal('signup-modal', 'login-modal');
    } catch (err) {
        errBox.textContent = '⚠️ 네트워크 오류가 발생했습니다.';
        errBox.style.display = 'block';
    }
}

async function handleLogout() {
    try {
        // postJSON 헬퍼 사용 — CSRF 헤더 자동 포함
        const response = await postJSON('/api/logout');
        if (response.status !== 204 && response.ok) {
            await response.json().catch(() => ({}));
        }
    } catch (e) {
        console.error('로그아웃 요청 처리 중 오류:', e);
    }
    setGuestUI();
    if (typeof resetChatWindow === 'function') resetChatWindow();
}