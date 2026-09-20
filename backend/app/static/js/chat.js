document.addEventListener('DOMContentLoaded', () =&gt; {
    setupInputEvents();
});

function setupInputEvents() {
    const input = document.getElementById('chat-input');
    const counter = document.getElementById('char-counter');
    if (!input || !counter) return;

    input.addEventListener('input', () =&gt; {
        if (input.value.length &gt; 1000) {
            input.value = input.value.substring(0, 1000);
        }
        counter.textContent = `${input.value.length} / 1,000자`;
    });

    input.addEventListener('keydown', (e) =&gt; {
        if (e.key === 'Enter' &amp;&amp; !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });
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

    // 1. 사용자 질문 말풍선 생성 (textContent 사용으로 XSS 방지)
    appendMessage('user', question);
    input.value = '';

    const counter = document.getElementById('char-counter');
    if (counter) counter.textContent = '0 / 1,000자';

    // 2. AI 대기 상태 말풍선
    const loadingId = appendMessage('ai', '⏳ AI가 답변을 생성하는 중입니다...', 'loading-msg');
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });

        removeMessage(loadingId);

        if (!response.ok) {
            const errData = await response.json().catch(() =&gt; ({}));
            let errorText = '현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)';
            if (errData.detail) {
                if (typeof errData.detail === 'string') {
                    errorText = errData.detail;
                } else if (Array.isArray(errData.detail)) {
                    errorText = errData.detail.map(i =&gt; i.msg || JSON.stringify(i)).join(', ');
                }
            }
            appendMessage('ai', errorText, 'error-bubble');
        } else {
            const data = await response.json();
            appendMessage('ai', data.answer);
            if (typeof loadHistoryIndex === 'function') loadHistoryIndex();
        }
    } catch (error) {
        removeMessage(loadingId);
        appendMessage('ai', '현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)', 'error-bubble');
    }
    scrollToBottom();
}

function appendMessage(sender, text, extraClass = '') {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return null;

    const row = document.createElement('div');
    const msgId = 'msg-' + Date.now();
    row.id = msgId;
    row.className = `message-row ${sender}`;

    const bubble = document.createElement('div');
    bubble.className = `bubble ${extraClass}`;

    // textContent를 사용하여 XSS 공격 완벽 방지
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
            <div>
                <h3>💡 무엇이든 물어보세요!</h3>
                <p>AskMate는 로그인 후 AI와 연속적인 대화를 나누고 기록을 관리할 수 있습니다.</p>
            </div>
        `;
    }
}
