// 담당자 B: 사용자 인증, 로그인/회원가입 모달, 사이드바 대화 기록 관리 전담

let currentUser = null;

document.addEventListener('DOMContentLoaded', () =&gt; {
    checkAuthStatus();
});

// 1. 인증 상태 확인 (GET /api/me)
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            const data = await response.json();
            currentUser = data.username;
            setLoggedInUI(currentUser);
            loadHistoryIndex();
        } else {
            setGuestUI();
        }
    } catch (e) {
        setGuestUI();
    }
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
        logoutLink.onclick = (e) =&gt; { e.preventDefault(); handleLogout(); };

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
        loginLink.onclick = (e) =&gt; { e.preventDefault(); openModal('login-modal'); };

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

// XSS 방지용 문자열 탈출 함수
function escapeHTML(str) {
    return String(str).replace(/[&amp;&lt;&gt;"']/g, (m) =&gt; ({
        '&amp;': '&amp;', '&lt;': '&lt;', '&gt;': '&gt;', '"': '"', "'": '''
    }[m]));
}

// 2. 사이드바 대화 기록 불러오기 (GET /api/me/chats)
async function loadHistoryIndex() {
    if (!currentUser) return;
    const historyList = document.getElementById('history-list');
    if (!historyList) return;

    try {
        const response = await fetch('/api/me/chats');
        if (!response.ok) return;

        const chats = await response.json();
        historyList.innerHTML = '';

        if (!Array.isArray(chats) || chats.length === 0) {
            historyList.innerHTML = '<p>이전 대화가 없습니다.</p>';
            return;
        }

        chats.forEach(chat =&gt; {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.textContent = `💬 ${chat.question}`;
            item.onclick = () =&gt; {
                const welcome = document.getElementById('welcome-card');
                if (welcome) welcome.remove();
                if (typeof appendMessage === 'function') {
                    appendMessage('user', chat.question);
                    appendMessage('ai', chat.answer);
                    scrollToBottom();
                }
            };
            historyList.appendChild(item);
        });
    } catch (e) {
        console.error('목록 로딩 실패:', e);
    }
}

// 모달 조작
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

// 3. 로그인 처리 (POST /api/login, 422 validation array 대응)
async function handleLogin(e) {
    e.preventDefault();
    const uInput = document.getElementById('login-username');
    const pInput = document.getElementById('login-password');
    const errBox = document.getElementById('login-error-msg');

    if (!errBox || !uInput || !pInput) return;

    errBox.style.display = 'none';
    pInput.classList.remove('input-error');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: uInput.value.trim(), password: pInput.value })
        });

        if (!response.ok) {
            const data = await response.json().catch(() =&gt; ({}));
            let msg = '⚠️ 아이디 또는 비밀번호가 올바르지 않습니다.';
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    msg = data.detail.map(item =&gt; item.msg || JSON.stringify(item)).join(', ');
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

// 4. 회원가입 처리 (POST /api/signup, 422 validation array 대응)
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
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: uInput.value.trim(), password: pInput.value })
        });

        if (!response.ok) {
            const data = await response.json().catch(() =&gt; ({}));
            let msg = '⚠️ 회원가입 실패. 다시 시도해 주세요.';
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    msg = data.detail.map(item =&gt; item.msg || JSON.stringify(item)).join(', ');
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

// 5. 로그아웃 처리 (POST /api/logout, 204 No Content 대응)
async function handleLogout() {
    try {
        const response = await fetch('/api/logout', { method: 'POST' });
        // 204 No Content 시 json() 파싱 시도를 차단합니다.
        if (response.status !== 204 &amp;&amp; response.ok) {
            await response.json().catch(() =&gt; ({}));
        }
    } catch (e) {
        console.error('로그아웃 요청 처리 중 오류:', e);
    }
    setGuestUI();
    if (typeof resetChatWindow === 'function') resetChatWindow();
}