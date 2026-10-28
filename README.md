# 🧭 job-finder — 이직 비서

> 이직 준비의 반복적인 부분을 AI가 무인으로 처리하고,
> 사용자는 **사람만 할 수 있는 네 가지**에만 시간을 쓰게 하는 개인 비서.
> [Claude Code](https://claude.com/claude-code) 기반. [AI Hub](https://github.com/wonleeeee/all-in-one)의 하위 프로젝트로 설치하거나 단독으로 쓸 수 있다.

---

## 문제

이직 준비가 힘든 이유는 어려워서가 아니라 **반복** 때문이다.

공고를 뒤지고, 이력서를 공고마다 고치고, 같은 폼에 같은 답을 스무 번 쓰고,
어디까지 진행됐는지 스프레드시트로 관리하는 일. 전부 기계적이다.
그러다 보면 정작 중요한 것 — 내 강점을 정확히 서술하는 일, 이 회사가 나에게 맞는지
판단하는 일, 면접에서 잘 말하는 일 — 에 쓸 시간이 남지 않는다.

**이 프로젝트는 그 비중을 뒤집는다.**

---

## 사용자가 하는 일은 네 가지뿐

```
 ① 사실 제공    내 경력·성과·수치           초기 3~5시간, 이후 분기 30분
 ② 승인         "이 공고에 지원할까?"        주 1회 10분
 ③ 대리 제출    자동화 안 되는 사이트만      건당 3~5분
 ④ 전략 판단    오퍼·협상·우선순위           발생 시
 ─────────────────────────────────────────────────────────────
 목표: 정상 운영 시 주간 15분 이하
```

나머지는 전부 AI가 무인으로 한다 — 공고 발굴·필터·스코어링, JD 파싱, 회사 리서치,
이력서 튜닝, 커버레터 초안, 지원 폼 작성, 상태 추적, 정체 감지, 받은메일 감시,
면접 일정 조율, 프렙 문서 생성, 협상 근거 조사, 주간 브리핑 작성.

---

## 어떻게 도는가

```
 매일 03:00  ─ 무인, 알림 없음 ────────────────────────────────
   공고 스윕 → 필터 → 스코어링 → 적재
   받은메일 감시 → 면접 제안·탈락·오퍼 감지
                                    │ 일주일치 누적
                                    ▼
 매주 월 08:00 ─ 📬 주간 브리핑 ── 유일한 정기 접점 ───────────
   [1] 승인 요청   신규 후보 5~10건 · 점수순 · 1줄 피치
   [2] 진행 현황   퍼널 · 이번 주 변화 · 다가오는 면접
   [3] 내 차례     자동화 불가 제출 (키트 준비 완료) · 회신 필요 메일
   [4] 정체 경고   10일+ 무응답 건
   [5] 자산 관리   이력서 갭 · 분기별 "지난 3개월 뭐 했어?"
                                    │ 사용자 10분: 체크박스
                                    ▼
 승인 직후 ─ 무인, 수 분 내 ────────────────────────────────────
   이력서 튜닝 → 제출 방식 판정 → 자동 제출 또는 제출 키트 생성
                                    │
                                    ▼
 이벤트 구동 ─ 수시 ────────────────────────────────────────────
   면접 확정 → D-3에 프렙 문서 자동 생성
   오퍼 도착 → 즉시 알림 + 시장가·협상 근거 리서치
```

---

## 파이프라인 — 2축

지원 **전**(내 작업)과 지원 **후**(회사의 진행)는 성격이 다르다. 축을 나눈다.

```
 worklane   discovered → proposed →[✋승인]→ tailored → ready → submitted
 (내 작업)                    └─[✋거부]→ dismissed          └→ needs_human
            └──────────── AI 무인 구간 ────────────┘

 stage      lead ──────────────────────→ applied → screening → interview
 (외부 진행)                                          → offer → closed
```

승인 게이트 하나가 무인 구간을 둘로 나눈다. **이게 설계의 중심이다.**

---

## 에이전트 8

| 에이전트 | 하는 일 | 소유(쓰기) |
|---|---|---|
| **resume-curator** | 마스터 이력서 구축·유지 | Notion **Resume Versions** (유일 writer — 새 버전 행 + `Current`) |
| **job-hunter** | 공고 발굴·필터·스코어링 | Jobs 신규행, 스윕 리포트 (Documents `sweep`) |
| **briefer** | 주간 브리핑·승인 요청 | 브리핑, `proposed` 승격 |
| **resume-tailor** | JD 맞춤 이력서·커버레터 | Notion **Tailored** 행 (행 = stable-id) |
| **applicator** | 제출·제출 키트·후속 | 외부 행동, `submitted`/`needs_human`, Tailored 하위 페이지 `submit-kit` |
| **outreach** | LinkedIn 아웃바운드 — 사람 찾기·메시지·발송 준비·답장 | Contacts, Notion **Outreach Queue** |
| **interview-coach** | 일정 조율·프렙·협상 근거 | Notion **Documents** 행 (research · interview-prep · negotiation · debrief) |
| **tracker** | 상태·이벤트 로그·데이터 계약 | Jobs 상태, Activity Log, DB 위생 |

---

## 데이터와 프라이버시

```
 ⚙️ engine   CLAUDE.md · .claude/agents/ · schemas/ · scripts/ · templates/ · hooks/
             → 평문 커밋. 개인정보 0. 이 레포에 있는 전부.
 ☁️ remote   Notion (MCP OAuth) = 개인 데이터 전부.
             Jobs · Activity Log · Contacts · Target Companies · Resume Versions ·
             Tailored · Documents · Outreach Queue + Settings 페이지(자율성 정책)
 🔒 local    data/notion_databases.json — DB 포인터. 유일한 개인 파일. gitignore.
 ♻️ cache    data/cache/ (/sync 가 내려받은 이력서·정책·튜닝 작업본) · .cache/h1b/ (공공 데이터)
             → 지워도 된다. gitignore.
```

**한 줄 규칙: 개인 데이터는 Notion 에, 로컬은 포인터와 캐시뿐.**

그래서 `.gitignore`가 두 줄이고, 파일마다 "이건 민감한가"를 판단할 일이 없다.
레포에 개인정보가 애초에 존재하지 않으므로 **공개해도 안전하고, 포크한 사람은
복호화나 키 배포 없이 즉시 쓸 수 있다.** 다기기도 자연히 해결된다 — 어느 기기든
clone 하고 Notion 에 로그인하면 같은 상태다.

세션은 `/sync` 로 시작한다. Notion 의 정본(Resume Versions 의 `Current` 행, Settings 페이지)을
`data/cache/` 로 내려받고, 에이전트는 그 사본을 읽는다. 쓰기는 캐시로 가지 않는다.

비밀값은 MCP(OAuth) 우선 — Notion·Gmail·Calendar는 토큰을 파일에 저장하지 않는다.

---

## 설치

### AI Hub의 하위 프로젝트로 (권장)

```
허브 프로젝트에서:  /install job-finder
```

허브가 clone → **Notion DB·Settings 자동 생성**(프로비저닝, 시드 포함) → 잠금 기록까지 처리한다.

### 단독으로

```bash
git clone https://github.com/wonleeeee/job-finder.git
cd job-finder

# 1. 커밋 사고 방지 훅 설치
git config core.hooksPath scripts/git-hooks

# 2. Claude Code 실행 → Notion MCP 로그인

# 3. 둘 중 하나
#    새로 시작:  hooks/provision.md 를 따라 내 Notion 에 DB 8개 + Settings 생성
#                (템플릿 이력서·정책이 시드로 올라간다)
#    기존 기기:  data/notion_databases.json 을 복사해 온다 (내용은 id 뿐)

# 4. /sync  → data/cache/ 에 이력서·정책이 내려온다
#    → resume-curator 와 함께 마스터 이력서 구축 시작
```

### 요구사항

| | 용도 | 없으면 |
|---|---|---|
| **Notion MCP** | 파이프라인 상태 · 승인 UI | 동작 불가 |
| Gmail MCP | 받은메일 감시 | 상태 갱신을 수동으로 |
| Calendar MCP | 일정 대조·등록 | 일정 조율 초안만 |
| 브라우저 자동화 | 지원 폼 작성 | 전부 수동 제출 경로로 |
| Python 3 *(선택)* | 스키마 검증 · 계약 감사 · 원격 백업 | 에이전트가 대행 (정밀도 하락) |
| curl *(선택)* | Notion 첨부 업로드·다운로드 | 작은 텍스트는 MCP 로, PDF 는 사용자가 올림 |

**Notion MCP만 필수다.** 나머지는 없으면 기능이 줄어들 뿐 깨지지 않는다.

Python은 **선택적 강화**다. 없어도 전부 동작하고, 있으면 기계적 보증을 받는다.

```
 python3 있음 ──► 🟢 스키마·불변식 통과 여부가 확정적. 원격 전체 백업 가능.
 python3 없음 ──► 🟡 에이전트가 계약(schemas/contract.json)을 직접 읽고 대조.
                     동작은 하되 감사에서 놓칠 수 있고, 원격 전체 덤프는 불가.
```

> ⚠️ Windows 주의: `python3.exe` 는 존재하지 않는다(`python.exe` + `py` 런처뿐).
> 게다가 Microsoft Store 스텁이 `python3` 이름을 가로채고 아무것도 출력하지 않는다.
> `/doctor` 는 PATH 존재 여부가 아니라 **실제 실행**으로 판정한다.

---

## 구조

```
job-finder/
├── CLAUDE.md              오케스트레이터 운영 규칙
├── DESIGN.md              설계 문서 (목적·원칙·결정 로그)
├── project.yaml           허브 매니페스트
├── .claude/
│   ├── agents/            서브에이전트 8
│   └── commands/          /sync /brief /approve /outreach /backup /doctor
├── schemas/               데이터 계약 — contract.json 이 정본(코드 아님). storage 절에 "어디에 무엇이 사는지"
├── scripts/               선택적 도구 (검증·감사·원격 백업·H-1B 조회·렌더)
├── templates/             시드·예시 (가짜 데이터)
├── hooks/                 설치·업데이트·마이그레이션·프로비저닝·첨부 절차
├── .cache/                ♻️ gitignore — 공공 데이터 (h1b/)
└── data/                  🔒 gitignore — notion_databases.json + cache/ 뿐
```

---

## 상태

초기 골격 (P0). 로드맵은 [DESIGN.md §12](DESIGN.md) 참조.

```
 P0  기반           ✅ 규약·에이전트 정의·스키마·계약
 P1  승인 게이트     ⬜ ★ 임계점 — 여기까지면 "AI가 찾고 나는 체크만"
 P2  주기 실행       ⬜ 예약 에이전트 + 받은메일 감시
 P3  제출 자동화     ⬜ 제출 키트 + 브라우저 자동화
 P4  인터뷰          ⬜ 일정 조율 + D-3 자동 프렙
 P5  학습 루프       ⬜ 거부 사유 → 선호 자동 조정
```

## 라이선스

MIT
