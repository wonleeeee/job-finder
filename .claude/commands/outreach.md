LinkedIn 아웃리치를 실행한다. `outreach` 서브에이전트에게 위임하고 그 5줄 요약을 그대로 전달한다.

큐는 Notion **Outreach Queue** DB 다 (포인터 `databases.outreach_queue`). 행 = 사람 × 공고 × 메시지 종류, 본문 = 초안.

인자가 범위를 정한다:
- `/outreach` — 주간 실행: 큐의 `Status=approved` 행 발송 준비(정책 모드대로) → 답장 수집 → 새 공고에 대한 사람 찾기 → `proposed` 행 적재
- `/outreach 찾기 [JOB-n ...]` — 1단계만. 지정 공고(없으면 점수 상위 Saved)의 사람 2~3명을 Contacts 에 적재하고 큐 행(초안 포함)까지
- `/outreach 발송` — 3단계만. 큐의 `approved` 행을 정책 모드(Settings 의 `outreach.mode`, 캐시 `data/cache/autonomy.yaml`)대로 처리
- `/outreach 답장` — 4단계만. 메시지함에서 큐에 있는 사람의 새 답장을 읽어 기록하고 사용자에게 전달
- `/outreach 큐` — Outreach Queue 현황을 Status 별 표로 (이름 · 회사 · 각도 · kind · Sent · Next touch)

실행 전 확인 두 가지:
1. `/sync` 후 `data/cache/autonomy.yaml` 에 `outreach` 블록이 없으면 `templates/autonomy.example.yaml` 의 블록을
   Settings 페이지에 추가하도록 안내하고 draft 모드로만 동작한다.
2. Claude in Chrome 이 연결돼 있지 않으면 1·2단계(검색 제외)와 큐 정리만 하고, 브라우저가 필요한 단계는 "브라우저 연결 후 재실행"으로 남긴다.

승인은 사용자가 Notion 에서 행 `Status` 를 `approved` 로 바꾸거나(폰에서 가능) 대화로 말한다. 에이전트는 `proposed → approved` 를 전이하지 않는다.
발송 단계에서 `confirm` 모드면 행마다 스크린샷과 함께 "보낼까요?"를 묻고, 사용자가 Send 를 누르거나 승인한 뒤에만 다음 행으로 간다.
