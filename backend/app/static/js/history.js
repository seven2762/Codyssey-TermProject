/**
 * AskMate 대화 기록 화면 전용 스크립트 (history.js)
 * GET /api/me/chats 호출, 최신순 렌더링, 한국어 시각 포맷팅, XSS 방지
 */

document.addEventListener("DOMContentLoaded", () => {
    const listContainer = document.getElementById("historyListContainer");
    if (!listContainer) return;

    const loadingState = document.getElementById("historyLoading");
    const emptyState = document.getElementById("historyEmpty");
    const errorAlert = document.getElementById("historyError");
    const errorMessage = document.getElementById("historyErrorMessage");
    const retryBtn = document.getElementById("historyRetryBtn");
    const refreshBtn = document.getElementById("historyRefreshBtn");
    const itemsContainer = document.getElementById("historyItems");
    const countText = document.getElementById("historyCountText");

    async function fetchHistory() {
        loadingState.style.display = "flex";
        emptyState.style.display = "none";
        listContainer.style.display = "none";
        errorAlert.style.display = "none";

        const res = await apiRequest("/api/me/chats", { method: "GET" });

        loadingState.style.display = "none";

        if (res.status === 401) {
            window.location.assign("/login");
            return;
        }

        if (!res.ok) {
            errorMessage.textContent = getErrorMessage(res.data, "대화 기록을 불러오지 못했습니다.");
            errorAlert.style.display = "flex";
            return;
        }

        const chats = res.data;
        if (!Array.isArray(chats) || chats.length === 0) {
            emptyState.style.display = "flex";
            return;
        }

        // 기록 렌더링
        countText.textContent = `총 ${chats.length}건의 대화`;
        itemsContainer.innerHTML = "";

        chats.forEach((item, index) => {
            const card = document.createElement("div");
            card.className = "history-card";

            // 헤더 (시간 표시)
            const header = document.createElement("div");
            header.className = "history-card-header";

            const timeSpan = document.createElement("span");
            try {
                timeSpan.textContent = new Date(item.created_at).toLocaleString("ko-KR", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                });
            } catch (e) {
                timeSpan.textContent = item.created_at;
            }

            const idSpan = document.createElement("span");
            idSpan.textContent = `#${chats.length - index}`;

            header.appendChild(timeSpan);
            header.appendChild(idSpan);

            // 질문 블록 (textContent로 안전 삽입)
            const qBlock = document.createElement("div");
            qBlock.className = "history-block";

            const qLabel = document.createElement("div");
            qLabel.className = "history-label label-question";
            qLabel.textContent = "👤 질문";

            const qText = document.createElement("div");
            qText.className = "history-text question-text";
            qText.textContent = item.question;

            qBlock.appendChild(qLabel);
            qBlock.appendChild(qText);

            // 답변 블록 (textContent로 안전 삽입)
            const aBlock = document.createElement("div");
            aBlock.className = "history-block";

            const aLabel = document.createElement("div");
            aLabel.className = "history-label label-answer";
            aLabel.textContent = "🤖 AI 답변";

            const aText = document.createElement("div");
            aText.className = "history-text answer-text";
            aText.textContent = item.answer;

            aBlock.appendChild(aLabel);
            aBlock.appendChild(aText);

            card.appendChild(header);
            card.appendChild(qBlock);
            card.appendChild(aBlock);

            itemsContainer.appendChild(card);
        });

        listContainer.style.display = "flex";
    }

    if (refreshBtn) refreshBtn.addEventListener("click", fetchHistory);
    if (retryBtn) retryBtn.addEventListener("click", fetchHistory);

    // 페이지 진입 시 최초 1회 데이터 로드
    fetchHistory();
});
