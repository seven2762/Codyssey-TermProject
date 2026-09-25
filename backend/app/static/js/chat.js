// 공용 POST 헬퍼 — CSRF 헤더(X-Requested-With)를 자동으로 포함한다.
// 서버 CSRF 검사 정책은 docs/AUTH.md 참고.
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

document.addEventListener('DOMContentLoaded', () => {
    setupInputEvents();
});

function setupInputEvents() {
    const input = document.getElementById('chat-input');
    const counter = document.getElementById('char-counter');
    if (!input || !counter) return;

    const updateCounter = () => {
        if (input.value.length > 1000) {
            input.value = input.value.substring(0, 1000);
        }
        counter.textContent = `${input.value.length} / 1,000자`;
    };

    input.addEventListener('input', updateCounter);

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });

    // 전송 버튼 클릭 이벤트 연동
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendQuestion);
    }
}

async function sendQuestion() {
    const input = document.getElementById('chat-input');
    if (!input) return;

    const question = input.value.trim();
    if (!question) {
        alert('질문을 입력해 주세요.');
        return;
    }

    const welcomeCard = document.getElementById('welcome-card');
    if (welcomeCard) welcomeCard.remove();

    appendMessage('user', question);
    input.value = '';

    const counter = document.getElementById('char-counter');
    if (counter) counter.textContent = '0 / 1,000자';

    const loadingId = appendMessage('ai', '⏳ AI가 답변을 생성하는 중입니다...', 'loading-msg');
    scrollToBottom();

    try {
        const response = await postJSON('/api/chat', { question: question });

        removeMessage(loadingId);

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            // 상태 코드별 에러 메시지 분기 처리
            handleChatError(response.status, errData);
            return;
        }

        const data = await response.json();
        appendMessage('ai', data.answer);
        if (typeof loadHistoryIndex === 'function') loadHistoryIndex();
    } catch (error) {
        removeMessage(loadingId);
        // mock 응답 제거 → 실제 에러 문구 표시
        appendMessage('ai', '⚠️ 네트워크 오류가 발생했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.', 'error-bubble');
    }
    scrollToBottom();
}

// 상태 코드별 에러 처리 분기
function handleChatError(status, errData) {
    const detail = errData.detail;
    let errorText;

    switch (status) {
        case 504:
        case 502:
            errorText = '⚠️ AI 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.';
            break;
        case 500:
            errorText = (typeof detail === 'string') ? detail : '⚠️ 서버 오류가 발생했습니다.';
            break;
        case 422:
            errorText = '⚠️ 입력이 올바르지 않습니다. 내용을 확인해 주세요.';
            break;
        case 401:
            errorText = '⚠️ 로그인이 필요합니다. 로그인 후 다시 시도해 주세요.';
            if (typeof openModal === 'function') openModal('login-modal');
            break;
        case 403:
            errorText = '⚠️ 요청이 차단되었습니다. 페이지를 새로고침해 주세요.';
            break;
        default:
            if (detail) {
                if (typeof detail === 'string') {
                    errorText = detail;
                } else if (Array.isArray(detail)) {
                    errorText = detail.map(i => i.msg || JSON.stringify(i)).join(', ');
                }
            } else {
                errorText = '⚠️ 알 수 없는 오류가 발생했습니다.';
            }
    }

    appendMessage('ai', errorText, 'error-bubble');
}

function appendMessage(sender, text, extraClass = '') {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return null;

    const row = document.createElement('div');
    const msgId = 'msg-' + Date.now() + '-' + Math.random().toString(16).slice(2);
    row.id = msgId;
    row.className = `message-row ${sender}`;

    const bubble = document.createElement('div');
    bubble.className = `bubble ${extraClass}`;
    bubble.textContent = text;

    row.appendChild(bubble);
    chatBox.appendChild(row);
    return msgId;
}

function removeMessage(msgId) {
    const el = document.getElementById(msgId);
    if (el) el.remove();
}

function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

function resetChatWindow() {
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.innerHTML = `
            <div id="welcome-card" class="welcome-card">
                <h3>💡 무엇이든 물어보세요!</h3>
                <p>AskMate는 로그인 후 AI와 연속적인 대화를 나누고 기록을 관리할 수 있습니다.</p>
            </div>
        `;
    }
}
