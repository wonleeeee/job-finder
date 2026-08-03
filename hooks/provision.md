# 프로비저닝 — 내 Notion 워크스페이스에 DB 만들기

설치 시 1회 실행한다. **멱등** — 이미 있으면 id만 재확인하고 넘어간다.

이 훅이 없으면 이 프로젝트는 공유가 불가능하다. 포크한 사람이 받는
`notion_databases.json` 은 원저자의 워크스페이스를 가리키는 죽은 포인터이기 때문이다.
그래서 포인터 파일은 커밋되지 않고(`data/` 아래), **각자 이 훅으로 생성한다.**

## 사전 확인

```
1. Notion MCP 가 연결돼 있는가?  아니면 여기서 중단하고 연결을 안내한다.
2. data/notion_databases.json 이 이미 있는가?
   있으면 → 각 database_id 를 notion-fetch 로 검증
            전부 유효하면 "이미 프로비저닝됨" 보고하고 종료
            깨진 것이 있으면 그것만 재생성
```

## 1. 워크스페이스 페이지 생성

`job-finder` 라는 페이지를 만든다. 위치는 사용자에게 묻는다
(개인 워크스페이스 루트가 기본).

## 2. Jobs DB

파이프라인. **2축을 별도 컬럼으로 만든다. 절대 하나로 합치지 않는다.**

| 속성 | 타입 | 옵션 / 비고 |
|---|---|---|
| Title | title | JD 원문 직무명 |
| Company | rich_text | |
| **worklane** | select | `discovered` `proposed` `dismissed` `tailored` `ready` `needs_human` `submitted` |
| **stage** | select | `lead` `applied` `screening` `interview` `offer` `closed` |
| closed_reason | select | `accepted` `rejected` `ghosted` `withdrawn` |
| dismiss_reason | select | `location` `level` `comp` `domain` `company` `sponsorship` `stack` `no_response` `unspecified` |
| **Approve** | checkbox | ★ 승인 게이트. 사용자가 폰에서 누르는 그 체크박스 |
| submit_method | select | `auto-form` `assisted` `manual` `email` |
| Stable ID | rich_text | 중복 제거 키 |
| Source | select | `LinkedIn` `Company site` `Referral` `Recruiter` `Indeed` `Wellfound` `Levels.fyi` `Other` |
| Level | select | `Mid` `Senior` `Staff` `Unknown` |
| Sponsorship | select | `Yes` `No` `Unknown` |
| Location | multi_select | 지역 태그 |
| Match score | number | 0~100 |
| JD URL | url | |
| JD snapshot | rich_text | JD 전문 — 공고는 사라진다 |
| Posted date | date | |
| Applied date | date | |
| Salary min / max | number | |
| Next action | rich_text | |
| Next action date | date | |
| Tailored resume | rich_text | `data/tailored/<id>/` 경로 |
| Tags | multi_select | |
| Notes | rich_text | 점수 내역 · 주의사항 |
| Activity | relation → Activity Log | DUAL |
| Contacts | relation → Contacts | DUAL |

### 필수 뷰 3개

```
✅ 승인 대기        filter: worklane = proposed
                    sort:   Match score 내림차순
                    ★ 사용자가 매주 여는 유일한 화면. 모바일에서 읽히게 구성한다.
                      보이는 속성: Title · Company · Match score · Sponsorship ·
                                   submit_method · Approve

🔥 활성             filter: worklane ≠ dismissed AND stage ≠ closed
                    group:  stage

📦 내 차례          filter: worklane = needs_human OR worklane = ready
                    sort:   Next action date 오름차순
```

## 3. Activity Log DB

이벤트 로그. **append-only.**

| 속성 | 타입 | 비고 |
|---|---|---|
| Summary | title | 한 줄, 사람이 읽는 제목 |
| Timestamp | date | ISO-8601 |
| Event type | select | `Discovered` `Proposed` `Approved` `Dismissed` `Tailored` `Applied` `Recruiter Reach` `Stage Change` `Interview Scheduled` `Interview Done` `Note` `Reject` `Offer` `Withdraw` |
| Agent | select | `Job Hunter` `Briefer` `Resume Tailor` `Applicator` `Interview Coach` `Tracker` `User` |
| From → To | rich_text | Stage Change 전용 |
| Job | relation → Jobs | DUAL |
| Payload | rich_text | 에이전트 원시 출력 JSON (디버깅) |
| Event UID | rich_text 또는 unique_id | 정정 시 참조용 |

## 4. Contacts DB

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | |
| Role | select | `Recruiter` `Hiring Manager` `Referrer` `Interviewer` `Other` |
| Company | rich_text | |
| Email / LinkedIn | email / url | |
| Jobs | relation → Jobs | DUAL |
| Notes | rich_text | |
| Last contact | date | |

## 5. 포인터 기록

`data/notion_databases.json` 에 쓴다. **이 파일은 gitignore 대상이다.**

```json
{
  "workspace_page": { "id": "...", "url": "..." },
  "databases": {
    "jobs":         { "database_id": "...", "data_source_id": "...", "url": "..." },
    "activity_log": { "database_id": "...", "data_source_id": "...", "url": "..." },
    "contacts":     { "database_id": "...", "data_source_id": "...", "url": "..." }
  },
  "provisioned_at": "<ISO-8601>",
  "contract_version": 1
}
```

## 6. 검증

```
<PY> scripts/notion_tracker.py contract
```

DB 3개의 id가 전부 출력되고 enum 목록이 위 표와 일치하면 성공이다.

## 7. 보고

```
✅ 프로비저닝 완료
   Jobs · Activity Log · Contacts 생성
   뷰 3개 설정 (승인 대기 / 활성 / 내 차례)
   포인터: data/notion_databases.json

   다음 단계: resume-curator 와 함께 마스터 이력서 구축을 시작하세요.
   3~5시간이 들지만 이 프로젝트에서 유일한 큰 투자입니다.
```

## 주의

```
🚫 사용자 확인 없이 기존 DB를 수정하지 않는다.
   같은 이름의 DB가 이미 있으면 그걸 쓸지 새로 만들지 묻는다.
🚫 select 옵션을 임의로 추가하지 않는다.
   계약 정본(schemas/contract.json)에 있는 것만 만든다.
   사람이 Notion에서 손으로 옵션을 추가하면 계약이 어긋나고
   에이전트 쓰기가 조용히 실패한다 — /doctor 가 이걸 잡는다.
```
