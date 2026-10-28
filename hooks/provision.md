# 프로비저닝 — 내 Notion 워크스페이스에 DB 만들기

설치 시 1회 실행한다. **멱등** — 이미 있으면 id만 재확인하고 넘어간다.

이 훅이 없으면 이 프로젝트는 공유가 불가능하다. 포크한 사람이 받는
`notion_databases.json` 은 원저자의 워크스페이스를 가리키는 죽은 포인터이기 때문이다.
그래서 포인터 파일은 커밋되지 않고(`data/` 아래), **각자 이 훅으로 생성한다.**

2026-10-21 부터 Notion 이 **개인 데이터 전부**의 정본이다 (DESIGN.md §8). 파이프라인 DB 4개에
더해 Resume Versions · Tailored · Documents · Outreach Queue 와 Settings 페이지를 만든다.
첨부를 올리는 절차는 `hooks/notion-files.md` 에만 있다.

## 사전 확인

```
1. Notion MCP 가 연결돼 있는가?  아니면 여기서 중단하고 연결을 안내한다.
2. data/notion_databases.json 이 이미 있는가?
   있으면 → 각 database_id · pages.settings.page_id 를 notion-fetch 로 검증
            전부 유효하면 "이미 프로비저닝됨" 보고하고 종료
            깨진 것이 있거나 키가 빠져 있으면 그것만 생성
```

## 1. 워크스페이스 페이지 생성

`Career` (또는 사용자가 고른 이름) 페이지를 만든다. 위치는 사용자에게 묻는다
(개인 워크스페이스 루트가 기본). 아래 DB·페이지는 전부 이 아래에 둔다.

## 2. Jobs DB

파이프라인. **상태 컬럼은 `Status` 하나다** (2026-10-21 단일축 공식화 — DESIGN.md §13).
계약의 worklane/stage 어휘는 이 컬럼으로 접어 쓴다 (CLAUDE.md 의 매핑표).

| 속성 | 타입 | 옵션 / 비고 |
|---|---|---|
| Title | title | JD 원문 직무명 |
| Company | rich_text | |
| **Status** | select | `Saved` `Applying` `Applied` `Phone Screen` `Tech Interview` `Onsite` `Offer` `Rejected` `Ghosted` `Withdrawn` |
| Stable ID | rich_text | 중복 제거 키 |
| Job UID | unique_id | |
| Source | select | `LinkedIn` `Company site` `Referral` `Recruiter` `Indeed` `Wellfound` `Levels.fyi` `Other` |
| Level | select | `Mid` `Senior` `Staff` `Unknown` |
| Sponsorship | select | `Yes` `Likely` `Unknown` `Unlikely` `No` (5값 — contract v2) |
| Location | multi_select | `US-Remote` `Hybrid` `Onsite` + 도시 태그 |
| Match score | number | 0~100 |
| JD URL | url | |
| JD snapshot | rich_text | JD 전문 — 공고는 사라진다 |
| Posted date / Applied date | date | |
| Salary min / max | number (dollar) | |
| Next action | rich_text | |
| Next action date | date | |
| Tailored resume | url | **Tailored 행의 URL** |
| Cover letter | url | |
| Tags | multi_select | |
| Notes | rich_text | 점수 내역 · 주의사항 · submit_method · dismiss_reason · lane 판단 |
| Activity | relation → Activity Log | DUAL |
| Contacts | relation → Contacts | DUAL |
| Target company | relation → Target Companies | DUAL |
| Documents | relation → Documents | DUAL (Documents.Job 의 역관계) |
| Tailored | relation → Tailored | DUAL (Tailored.Job 의 역관계) |
| Outreach | relation → Outreach Queue | DUAL (Outreach Queue.Job 의 역관계) |

### 필수 뷰 3개

```
✅ 승인 대기        filter: Status = Saved
                    sort:   Match score 내림차순
                    ★ 사용자가 매주 여는 유일한 화면. 모바일에서 읽히게 구성한다.
                      보이는 속성: Title · Company · Match score · Sponsorship · Notes

🔥 활성             filter: Status ∉ {Rejected, Ghosted, Withdrawn}
                    group:  Status

📦 내 차례          filter: Status = Applying
                    sort:   Next action date 오름차순
```

## 3. Activity Log DB

이벤트 로그. **append-only.**

| 속성 | 타입 | 비고 |
|---|---|---|
| Summary | title | 한 줄, 사람이 읽는 제목 |
| Timestamp | date | ISO-8601 |
| Event type | select | `Discovered` `Proposed` `Approved` `Dismissed` `Tailored` `Applied` `Recruiter Reach` `Outreach Sent` `Connection Accepted` `Outreach Reply` `Stage Change` `Interview Scheduled` `Interview Done` `Note` `Reject` `Offer` `Withdraw` |
| Agent | select | `Job Hunter` `Briefer` `Resume Tailor` `Applicator` `Outreach` `Interview Coach` `Tracker` `User` |
| From → To | rich_text | Stage Change 전용 |
| Job | relation → Jobs | DUAL |
| Payload | rich_text | 에이전트 원시 출력 JSON (디버깅 · outreach 의 contact_uid) |
| Event UID | unique_id | 정정 시 참조용 |

## 4. Contacts DB

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | |
| Role | select | `Recruiter` `Hiring Manager` `Referrer` `Engineer` `Other` |
| Status | select | `Active` `Cold` `Closed` |
| Company | rich_text | |
| Email / LinkedIn | email / url | |
| Jobs | relation → Jobs | DUAL |
| Outreach | relation → Outreach Queue | DUAL (Outreach Queue.Contact 의 역관계) |
| Notes | rich_text | 선정 이유 · 각도 · 공통점 |
| Last touch / Next touch | date | outreach 가 발송·후속 시 갱신 |
| Contact UID | unique_id | Activity Log Payload 의 `contact_uid` |

## 5. Target Companies DB

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | 회사명 |
| Jobs | relation → Jobs | DUAL (Jobs.Target company) |
| 그 외 | — | job-hunter 가 쓰는 메모·우선순위. 계약 enum 없음 |

## 6. Resume Versions DB — 마스터 이력서의 정본

행 하나 = 버전 하나. **`Current` 가 켜진 행은 정확히 하나**이고, 그 행에 붙은 JSON 이 단일 원천이다.

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | `v23 — 2026-10-15` |
| Version | number | `meta.version` 과 같다. 단조 증가 |
| **Current** | checkbox | 정확히 1행. tracker 감사 항목 |
| Date | date | |
| Schema version | rich_text | `meta.schema_version` |
| Files | files | 사람이 UI 로 올릴 때만. 에이전트는 본문 첨부를 쓴다 |
| Changelog | rich_text | 이 버전에서 바뀐 것 |
| Bullets | number | 불릿 수 (진행률 표시용) |

본문: `<file source=...>` 첨부 4개 — `master_resume.vN.json` · `.md` · `_audit.md` · `_stories.md`.

**프로비저닝 시 첫 행이 필요하다.** `templates/master_resume.example.json` 을 `master_resume.v1.json` 으로
업로드하고 `Current` 를 켠다 (절차: `hooks/notion-files.md`). 이 행이 없으면 `/sync` 가 실패한다.
시드는 예시 데이터임을 사용자에게 알린다.

## 7. Tailored DB — 공고별 튜닝본

행 하나 = stable-id 하나. Jobs.`Tailored resume`(url) 이 이 행을 가리킨다.

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | stable-id |
| Job | relation → Jobs | DUAL (Jobs.Tailored) |
| Company | rich_text | |
| Variant | select | `job-specific` `cluster` `draft` |
| Status | select | `current` `superseded` `submitted` |
| Date | date | |
| Files | files | resume.json · PDF (사람이 UI 로 올릴 때) |
| Master version | number | 어느 마스터 버전에서 파생됐나 |
| Notes | rich_text | |
| Tailored UID | unique_id | |

본문 = `resume.md`. 하위 페이지 = `cover-letter` · `tailoring_notes` · `submit-kit` · `kits/*`.
첨부 = `resume.json` · PDF.

## 8. Documents DB — 프렙 · 리서치 · 협상 · 스윕 · 과정 문서

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | 문서 제목 (회사 접두사 없이 — Company 가 있다) |
| Type | select | `sweep` `jd-analysis` `research` `interview-prep` `debrief` `negotiation` `cheatsheet` `linkedin` `process` `housing` `other` |
| Company | rich_text | |
| Job | relation → Jobs | DUAL (Jobs.Documents) |
| Target company | relation → Target Companies | |
| Date | date | |
| Status | select | `current` `archived` |
| Files | files | HTML · PDF · ICS (사람이 UI 로 올릴 때) |
| Source path | rich_text | 이전 전 로컬 경로 (이력용) |
| Doc UID | unique_id | |

본문 = 문서 마크다운. 150 KB 를 넘으면 첨부로.

## 9. Outreach Queue DB — LinkedIn 아웃리치 큐

| 속성 | 타입 | 비고 |
|---|---|---|
| Name | title | `<이름> @ <회사> · <kind>` |
| Contact | relation → Contacts | DUAL (Contacts.Outreach) |
| Job | relation → Jobs | DUAL (Jobs.Outreach) |
| Angle | select | `posting` `korean` `alumni` `domain` `mutual` |
| Kind | select | `A` `B` `C` |
| Status | select | `proposed` `approved` `sent` `accepted` `replied` `no_response` `blocked` |
| Korean affiliated | checkbox | |
| Mode snapshot | select | `draft` `confirm` `delegated` — 실행 시점의 outreach.mode |
| Proposed / Sent / Next touch / Replied | date | |
| Notes | rich_text | |
| Queue UID | unique_id | |

본문 = 메시지 초안 전문. `proposed → approved` 는 **사용자만** 바꾼다 (폰에서 Status 를 바꾸면 된다).

## 10. Settings 페이지 — 자율성 정책

일반 페이지 하나. 본문은 **```yaml 코드 블록 하나**뿐이다. `templates/autonomy.example.yaml` 을 그대로 넣는다.
`/sync` 가 이 블록을 `data/cache/autonomy.yaml` 로 추출한다. 정책 수정은 이 페이지에서 한다.

## 11. 포인터 기록

`data/notion_databases.json` 에 쓴다. **이 파일은 gitignore 대상이고, 로컬의 유일한 개인 파일이다.**

```json
{
  "workspace_page": { "id": "...", "url": "...", "title": "Career" },
  "databases": {
    "jobs":             { "database_id": "...", "data_source_id": "...", "url": "..." },
    "activity_log":     { "database_id": "...", "data_source_id": "...", "url": "..." },
    "contacts":         { "database_id": "...", "data_source_id": "...", "url": "..." },
    "target_companies": { "database_id": "...", "data_source_id": "...", "url": "..." },
    "documents":        { "database_id": "...", "data_source_id": "...", "url": "..." },
    "tailored":         { "database_id": "...", "data_source_id": "...", "url": "..." },
    "resume_versions":  { "database_id": "...", "data_source_id": "...", "url": "..." },
    "outreach_queue":   { "database_id": "...", "data_source_id": "...", "url": "..." }
  },
  "pages": {
    "settings":         { "page_id": "...", "url": "..." }
  },
  "provisioned_at": "<ISO-8601>",
  "contract_version": 3
}
```

에이전트는 `data_source_id` 로 조회하고(`notion-query-data-sources`) `database_id`/`page_id` 로 fetch 한다.

## 12. 검증

```
<PY> scripts/notion_tracker.py contract
/sync
```

DB 8개와 Settings 의 id가 전부 출력되고, enum 목록이 위 표와 일치하고, `/sync` 가
`data/cache/master_resume.json` · `data/cache/autonomy.yaml` 을 만들면 성공이다.

## 13. 보고

```
✅ 프로비저닝 완료
   Jobs · Activity Log · Contacts · Target Companies
   Resume Versions (v1 시드) · Tailored · Documents · Outreach Queue · Settings
   뷰 3개 설정 (승인 대기 / 활성 / 내 차례)
   포인터: data/notion_databases.json
   캐시:   data/cache/ (/sync 완료)

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
🚫 Files 속성에 upload id 를 넣지 않는다 — 첨부는 본문에 (hooks/notion-files.md).
```
