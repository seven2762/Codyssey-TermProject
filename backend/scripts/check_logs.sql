-- 로컬 DB 확인용. :user_id에 조회할 사용자 ID를 지정한다.
-- created_at은 시간대 정보 없이 저장된 UTC 시각이다.
SELECT id, user_id, question, answer, created_at
FROM chats
WHERE user_id = :user_id
ORDER BY created_at DESC, id DESC;
