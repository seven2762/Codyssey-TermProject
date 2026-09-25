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
            let errorText = '현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)';
            if (errData.detail) {
                if (typeof errData.detail === 'string') {
                    errorText = errData.detail;
                } else if (Array.isArray(errData.detail)) {
                    errorText = errData.detail.map(i => i.msg || JSON.stringify(i)).join(', ');
                }
            }
            appendMessage('ai', errorText, 'error-bubble');
            return;
        }

        const data = await response.json();
        appendMessage('ai', data.answer);
        if (typeof loadHistoryIndex === 'function') loadHistoryIndex();
    } catch (error) {
        removeMessage(loadingId);
        appendMessage('ai', `프론트엔드 mock 응답: “${question}”에 대한 답변을 준비 중입니다. 백엔드 API가 연결되면 실제 응답으로 교체됩니다.`, 'error-bubble');
    }
    scrollToBottom();
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
