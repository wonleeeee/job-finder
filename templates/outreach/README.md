# outreach 템플릿

> **2026-10-21:** 큐와 초안은 Notion **Outreach Queue** DB 로 옮겨갔다. `queue.example.yaml` 은 더 이상 복사해 쓰는
> 시드가 아니라 **필드 레퍼런스**다 (같은 이름이 DB 속성이다). 로컬 `data/outreach/` 는 없다.

`outreach` 에이전트가 쓰는 골격이다. 개인 데이터는 없다 — 전부 자리표시자다.

```
templates/outreach/
├── README.md            이 파일
├── messages.md          메시지 골격 3종 (A 연결 노트 · B 본 메시지 · C 후속) + 각도별 변형
└── queue.example.yaml   큐 항목의 필드 레퍼런스 → Notion Outreach Queue 행의 속성과 1:1

Notion Outreach Queue    (포인터 databases.outreach_queue — 사람 이름·메시지가 들어간다)
├── 행 속성              Contact · Job · Angle · Kind · Status · Korean affiliated · Mode snapshot ·
│                        Proposed · Sent · Next touch · Replied · Notes · Queue UID
└── 행 본문              메시지 초안 (구 drafts/<contact-uid>-<job-uid>.md)
```

정책은 Notion Settings 페이지의 `outreach` 블록(캐시 `data/cache/autonomy.yaml`),
어휘(이벤트 타입·각도·큐 상태)는 `schemas/contract.json` 에 있다. DB 속성표는 `hooks/provision.md` §9.
