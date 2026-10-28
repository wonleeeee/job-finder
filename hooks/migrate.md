# 데이터 마이그레이션 지침

`schemas/master_resume.schema.json` 이 기대하는 `meta.schema_version` 이
사용자의 마스터 이력서(`/sync` 후 `data/cache/master_resume.json`)보다 높을 때 실행한다.

## 원칙

```
1. 비파괴  마이그레이션은 새 Resume Versions 행이다. 이전 행은 그대로 남는다 (행=버전).
           Current 를 옮기기 전까지 정본은 바뀌지 않는다.
2. 순차    한 번에 한 버전씩 (1.0.0 → 1.1.0 → 2.0.0)
3. 검증    각 단계 후 <PY> scripts/validate_resume.py data/cache/master_resume.json
4. 보고    완료 후 무엇이 바뀌었는지 사용자에게 요약
5. 중단    어느 단계든 검증 실패 시 Current 를 옮기지 않고 중단. 억지로 진행하지 않는다
```

**Stable ID는 마이그레이션에서도 신성하다.** 필드 이름이 바뀌어도
`experience[].id` 와 `bullets[].id` 는 그대로 유지한다. 이걸 깨면
Tailored DB 의 모든 튜닝본이 마스터를 역참조하지 못하게 된다.

## 원격(Notion) 계약 마이그레이션

로컬 파일과 **다른 절차**다. 백업을 파일 복사로 할 수 없다.

```
1. 덤프    현재 전체 행을 JSON으로 backup.path (Settings 의 backup 블록) 아래 <날짜>-notion.json 에 저장
           (Notion 페이지 이력도 있지만 옵션 삭제는 이력으로 못 되돌린다)
2. 추가    새 select 옵션을 DB에 추가 (추가는 안전)
3. 이행    기존 행의 값을 새 어휘로 변환 (필요한 경우)
4. 삭제    옛 옵션 제거는 사용자 확인 후에만. 그 값을 쓰는 행이 0인지 먼저 확인
5. 검증    <PY> scripts/notion_tracker.py audit
```

## 버전별 변경

### v1.0.0 (최초)

기준 스키마. 마이그레이션 없음.

## 계약(contract.json) 버전별 변경

`meta.schema_version`(마스터 이력서)과 **별개**인 `contractVersion`(Notion 계약)의 이력이다.

### contract v1 → v2 — 2축 전환 + 레인

> **2026-10-21 결정: 이 절의 (가) 컬럼 추가·값 이행은 적용하지 않는다.** Jobs 는 `Status` 단일 컬럼으로
> 남는다 ("Status 단일축 공식화" — DESIGN.md §13). 아래 매핑표는 반대 방향으로 쓴다 — 계약의
> worklane/stage 를 Notion `Status` 로 접을 때의 기준이다. `Sponsorship` 5값은 적용됐다.
> 레인(`lane`·`judgment`)은 컬럼이 아니라 Notes 에 적는다.

두 가지가 한 회차에 들어간다. **원격 스키마를 두 번 건드릴 이유가 없다.**

**(가) 2축 전환** — 단일 `Status` → `worklane` + `stage`

**(나) 레인** — 대량 지원을 LLM 판단으로 굴리기 위한 어휘

#### 추가할 Notion 속성 (전부 가산 — 안전)

| 속성 | 타입 | 옵션 |
|---|---|---|
| `worklane` | select | discovered, proposed, dismissed, tailored, ready, needs_human, submitted |
| `stage` | select | lead, applied, screening, interview, offer, closed |
| `dismiss_reason` | select | location, level, comp, domain, company, sponsorship, stack, no_response, unspecified |
| `closed_reason` | select | accepted, rejected, ghosted, withdrawn |
| `submit_method` | select | auto-form, assisted, manual, email |
| `lane` | select | conviction, volume, longshot |
| `judgment` | text | LLM 판단 근거 (레인 배정·스폰서십 해소) |

#### 기존 속성 변경

- `Sponsorship` select 에 **`Likely` · `Unlikely` 추가.** 기존 Yes/No/Unknown 행은 그대로 둔다.
  의미가 바뀐 것은 `Unknown` 하나다 — "불명 확정"이 아니라 **"아직 해소 안 함"**이다.
  기존 Unknown 행은 job-hunter 가 재판정 대상으로 집어간다. 값을 일괄 변환하지 않는다.

#### 값 이행

`Status` → 2축 매핑:

| Status | worklane | stage |
|---|---|---|
| Saved | discovered | lead |
| Applying | ready | lead |
| Applied | submitted | applied |
| Phone Screen | submitted | screening |
| Tech Interview / Onsite | submitted | interview |
| Offer | submitted | offer |
| Rejected / Ghosted | submitted | closed |
| Withdrawn | **`Applied date` 유무로 갈린다** ↓ | |

`Withdrawn` 은 단일축 시절에 두 가지 뜻으로 섞여 쓰였다. **`Applied date` 가 없으면 지원 전 거부**
이므로 `dismissed`/`lead` 이고, 있으면 지원 후 철회이므로 `submitted`/`closed` + `closed_reason=withdrawn` 이다.
이걸 뭉개면 퍼널 통계가 오염된다.

`lane` 과 `judgment` 은 **이행하지 않고 비워 둔다.** 레인은 발굴 시점이 아니라 제안 시점에
배정되므로, 기존 행은 다음 스윕에서 job-hunter 가 채운다.

#### 검증

이행 후 불변식 3종을 확인한다 — `axis-coupling` · `dismiss-reason-required` · `closed-reason-required`.
레인 관련 3종(`lane-requires-judgment` · `longshot-must-be-cheap` · `hard-no-excludes`)은
`lane` 이 전부 비어 있으므로 이 회차에서는 자동 통과한다.

#### 되돌리기

옛 `Status` 컬럼을 **삭제하지 않는다.** 새 축과 병존시킨 채 한 사이클 돌려보고,
검증이 끝난 뒤 사용자 확인을 받아 별도로 제거한다. 이게 유일한 롤백 경로다.

#### 완료 후

`data/notion_databases.json` 의 `contract_version` 을 `2` 로 채우고 `_pending` 키를 지운다.

<!--
스키마를 바꿀 때마다 아래 형식으로 추가한다:

### v1.0.0 → v1.1.0
- 무엇이 왜 바뀌었는지
- 각 항목을 어떻게 변환하는지 (기본값 · 필드 이름 변경 · 삭제 대상)
- Notion 계약도 함께 바뀌는가? 그렇다면 위 원격 절차도 실행
- 되돌리는 방법
-->

### contract v2 → v3 — 아웃바운드 아웃리치 어휘

LinkedIn 에서 **내가 먼저 연락하는** 흐름(`outreach` 에이전트)을 기록하기 위한 추가다. 전부 가산이라 안전하다.

> **원격 부분 적용 완료 — 2026-10-21.** Activity Log 의 Event type 3개 · Agent `Outreach` 추가됨.
> worklane/stage 컬럼은 추가하지 않았다 (위 v1→v2 의 단일축 결정). Contacts 에는 Outreach Queue 로의
> 관계(`Outreach`)가 생겼는데, 이는 아래 "data/ → Notion 이전"의 산물이고 v3 어휘와는 별개다.
> 아래 "이행 전 임시 표기"와 "로컬" 절은 역사 기록이다.

#### 추가할 Notion 옵션 (가산 — 안전)

| DB | 속성 | 추가 옵션 |
|---|---|---|
| Activity Log | `Event type` (select) | `Outreach Sent` · `Connection Accepted` · `Outreach Reply` |
| Activity Log | `Agent` (select) | `Outreach` |

Contacts 는 속성을 바꾸지 않는다. 각도(`outreach_angle`)·메시지 종류는 **Notes 와 Payload** 에 적는다.
Activity Log 에는 Contact 관계가 없으므로 불변식 `outreach-event-needs-contact` 가 Payload 의 `contact_uid` 를 요구한다.
(Contact 관계 속성 추가는 선택 사항이다 — 추가하면 `Contacts.Activity` 역관계가 생겨 DB 가 넓어진다. v3 에서는 넣지 않는다.)

#### 이행 전 임시 표기

옵션이 추가되기 전에는 outreach 에이전트가 `Event type=Note` 로 쓰고 Summary 앞에
`[outreach:sent]` `[outreach:accepted]` `[outreach:reply]` 를 붙인다. 이행 시 그 접두어를 보고
Event type 을 바꾸고 접두어를 지운다 (append-only 원칙의 예외 — 정정이 아니라 어휘 이행이다. 이행 자체를 `Note` 로 1건 남긴다).

#### 로컬 (역사 — 2026-10-21 이후에는 해당 없음)

- 당시 `data/autonomy.yaml` 에 `outreach` 블록을 추가했다 (`templates/autonomy.example.yaml` 참조). 기본 `mode: confirm`.
  → 지금은 Settings 페이지의 yaml 블록에 있다.
- 당시 `data/outreach/queue.yaml` 을 만들었다 (`templates/outreach/queue.example.yaml`).
  → 지금은 Outreach Queue DB 다.

#### 되돌리기

옵션은 지우지 않고 두면 된다. 사용 행이 0인지 확인한 뒤에만 제거한다.

#### 완료 후

`data/notion_databases.json` 의 `contract_version` 을 `3` 으로. (적용됨)

---

## 저장소 이전 — 2026-10-21 `data/` → Notion

계약 버전은 그대로 3 이다. 바뀐 것은 어휘가 아니라 **개인 데이터가 사는 곳**이다 (DESIGN.md §8, §13).

### 무엇이 어디로

| 이전 (로컬) | 이후 (Notion) | 로컬에 남는 것 |
|---|---|---|
| `data/master_resume.json` `.md` `_audit.md` `_stories.md` | **Resume Versions** 행 (`v23 — 2026-10-15`, `Current` ✔) 의 본문 첨부 4개 | `data/cache/master_resume.json` (/sync 사본) |
| `data/backups/master_resume.v*.json` 등 | Resume Versions 의 이전 버전 행들 (`Current` ✘) | 없음 |
| `data/autonomy.yaml` | **Settings** 페이지의 ```yaml 블록 | `data/cache/autonomy.yaml` (/sync 사본) |
| `data/tailored/<id>/` | **Tailored** 행 (행=stable-id, 본문 resume.md, 하위 페이지 cover-letter · tailoring_notes · submit-kit · kits/*, 첨부 resume.json · PDF). Jobs.`Tailored resume` 가 행 URL 을 가리킨다 | `data/cache/tailored/<id>/` (작업 사본, 필요 시) |
| `data/tailored/*/render_*.py` `build_*.py` (엔진 코드 사본) | — | **`data/render/`** (개인 정보가 코드에 박혀 있어 엔진에 둘 수 없다 · gitignore. 범용화 전까지) |
| `data/docs/**` | **Documents** 행 (Type · Company · Job 관계 · Source path 에 옛 경로) | 없음 |
| `data/outreach/queue.yaml` + `drafts/*.md` | **Outreach Queue** 행 (본문=초안) | 없음 |
| `data/h1b/` (DOL LCA · USCIS, ~470MB 공공 데이터) | — | **`.cache/h1b/`** 로 이동 (`scripts/h1b_sponsors.py` 갱신됨) |
| `data/notion_databases.json` | — | 그대로. 키 추가: `documents` `tailored` `resume_versions` `outreach_queue` `pages.settings` |
| `data/plan-*.md` `migration-map-*.json` | Documents 행 (Type `process`) | 없음 |

### 원격 스키마 변경 (이 회차에 함께)

- Jobs: `Tailored resume` 를 url 로, 관계 `Documents` · `Tailored` · `Outreach` 추가. **worklane/stage 는 추가하지 않음.**
- Contacts: 관계 `Outreach` 추가.
- Activity Log: v3 옵션 적용 (위).

### 이전 직전 백업

`<백업 폴더>/job-finder-data-pre-notion-migration-2026-10-21.zip` — 이전 직전의 `data/` 전체.
개인정보 전부가 들어 있다. 공개 위치로 옮기지 않는다.

### 되돌리기

파일 복사가 아니다.

```
1. 마스터 이력서   Resume Versions 의 원하는 행 → 첨부 4개 다운로드 (hooks/notion-files.md)
2. 정책            Settings 페이지의 yaml 블록을 복사
3. 튜닝본 · 문서   해당 행을 notion-fetch 로 본문을 내보내고 첨부를 다운로드
4. 전체 롤백       위 zip 을 풀고 엔진을 2026-10-20 커밋으로 되돌린다 (git checkout)
```

Notion 의 페이지 버전 이력이 본문의 되돌리기를 담당한다. 첨부 교체는 이력에 남지 않으므로
Resume Versions 는 **행을 덮어쓰지 않고 새 행을 만든다** — 그래서 버전이 행이다.

### 완료 후

`data/` 에 `notion_databases.json` 과 `cache/` 외의 파일이 남아 있으면 `/doctor` 가 경고한다.
확인 후 삭제는 사용자가 한다 (zip 이 있으므로 안전).
