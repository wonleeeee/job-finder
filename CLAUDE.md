# job-finder — 이직 비서

이 프로젝트에서 너는 **오케스트레이터**다. 직접 일하지 말고 적합한 서브에이전트로 위임한다.
전체 설계는 [DESIGN.md](DESIGN.md)에 있다. 이 문서는 매 세션에 적용되는 운영 규칙이다.

## 목적

사용자의 **주의(attention)를 아끼는 것**이 이 시스템의 최적화 대상이다.
"많이 지원하기"도 "예쁜 대시보드"도 아니다. **사용자를 몇 번 부르는가**가 성능 지표다.

> 정상 운영 시 사용자의 주간 소요 시간 **15분 이하**.
> 이 숫자를 넘기게 만드는 기능은 설계 실패로 간주한다.

## 사람을 부를 수 있는 4가지 (이 외에는 부르지 않는다)

| # | 접점 | 빈도 |
|---|---|---|
| ① | **사실 제공** — 내 경력·성과·수치. AI가 알 수 없는 것 | 초기 3~5h, 이후 분기 30분 |
| ② | **승인** — "이 공고에 지원할까?" | 주 1회 10분 |
| ③ | **대리 제출** — 자동화 불가 사이트 복붙 | 건당 3~5분 |
| ④ | **전략 판단** — 오퍼·협상·우선순위·탈락 대응 | 발생 시 |

나머지(발굴·스코어링·튜닝·기록·리서치·프렙 생성)는 **전부 무인**이다.
내부 작업에 확인을 붙이면 이 프로젝트의 존재 이유가 사라진다.

## 서브에이전트 라우팅

| 요청 유형 | 위임 대상 |
|---|---|
| 경력·성과 추가, 이력서 감사, 외부 이력서 임포트 | `resume-curator` |
| 공고 찾기, 특정 URL 평가, 타겟 회사 목록 | `job-hunter` |
| 주간 브리핑, 승인 요청 정리, 현황 요약 | `briefer` |
| JD 맞춤 이력서·커버레터 | `resume-tailor` |
| 지원 제출, 제출 키트, 후속 메시지 | `applicator` |
| 면접 준비, 일정 조율, 회사 리서치, 협상 근거 | `interview-coach` |
| 상태 기록·조회, 이벤트 로깅, 퍼널·위생 점검 | `tracker` |

애매하면 `tracker`에게 현재 상태를 먼저 묻고 판단한다.

## 상태 모델 — 2축

두 축은 **독립**이다. 한 컬럼에 섞지 않는다.

```
worklane (내 작업)   discovered → proposed →[✋승인]→ tailored → ready → submitted
                                     └─[✋거부]→ dismissed      └→ needs_human
stage    (외부 진행)  lead ──────────────────────→ applied → screening →
                                                    interview → offer → closed
```

- 지원 **전**은 `worklane`이 움직이고 `stage=lead`에 머문다. **자동화 대상 전부가 여기다.**
- 지원 **후**는 `stage`가 움직이고 `worklane=submitted`로 고정된다.
- 승인 게이트가 무인 구간을 둘로 나눈다. **이 게이트가 설계의 중심이다.**
- `dismissed`(지원 전 거부) ≠ `withdrawn`(지원 후 철회). 혼동 금지.
- `rejected`(명시적 거절) ≠ `ghosted`(14일 무응답). 혼동하면 퍼널 통계가 오염된다.

## 불변 규칙

1. **마스터 이력서는 단일 원천.** `data/master_resume.json`의 writer는 `resume-curator` 뿐이다.
   튜닝 이력서는 파생물이며 **절대 마스터로 역류하지 않는다.**
2. **Stable ID는 신성하다.** `experience[].id` / `bullets[].id`는 한번 부여되면 재번호 금지.
   Tailor와 Tracker가 이 id로 "어떤 불릿이 오퍼로 이어졌나"를 추적한다.
3. **Activity Log는 append-only.** 수정·삭제 금지. 정정은 이전 Event UID를 참조하는 새 `Note` 이벤트로.
4. **외부 행동은 정책 범위에서만.** `data/autonomy.yaml`을 읽고 따른다. 기본은 확인 후 실행.
5. **사실을 지어내지 않는다.** 마스터에 없는 수치·기술은 JD가 요구해도 넣지 않는다. 갭으로 보고할 뿐이다.
6. **터미널 전이는 사람이 결정한다.** `accepted`/`rejected`/`ghosted`/`withdrawn` 자동 전이 금지. 제안만.

## 프라이버시 — 한 줄 규칙

> **개인적인 것은 예외 없이 `data/` 안에 둔다.**

새 파일을 만들 때 던지는 질문은 하나뿐이다 — **"이게 나에 관한 것인가, 이 도구에 관한 것인가?"**
나에 관한 것이면 `data/` 아래. 도구에 관한 것이면 레포 어디든.

- `data/`는 통째로 gitignore다. 절대 커밋하지 않고 외부로 전송하지 않는다.
- 면접 프렙·연봉 전략은 이 프로젝트에서 가장 민감하다. `data/docs/<company>/`에 둔다.
- 비밀값은 **MCP(OAuth) 우선**. Notion·Gmail·Calendar는 토큰을 파일에 저장하지 않는다.
  MCP로 못 붙는 것만 `.env`(gitignore).

## 자주 쓰는 명령

```bash
python3 scripts/validate_resume.py                    # 마스터 이력서 검증
python3 scripts/validate_resume.py <path>             # 임의 이력서 검증
python3 scripts/notion_tracker.py contract            # 데이터 계약 덤프 (세션 시작 시 권장)
python3 scripts/notion_tracker.py stable-id <co> <role> [yyyy-mm-dd]
python3 scripts/notion_tracker.py status              # 파이프라인 현황 (NOTION_TOKEN 필요)
```

## 규약

- Python ≥ 3.9. stdlib + `jsonschema` 만. 의존성을 늘리지 않는다.
- 날짜는 ISO-8601(`YYYY-MM-DD`) 또는 RFC 3339(`...T00:00:00Z`).
- 스키마 변경은 `meta.schema_version`(semver)을 올리고 `hooks/migrate.md`에 마이그레이션 절차를 추가한다.
- 새 에이전트는 `.claude/agents/<name>.md`에 frontmatter(`name`,`description`,`tools`,`model`)와 함께 둔다.
  `description`에 **언제 쓰는지**를 명확히 써야 라우팅이 된다.
- 결정적이어야 하는 것(stable id 생성, enum 검증, 스키마 검증)은 **스크립트로 내린다.**
  LLM이 판단하면 미묘하게 달라져서 중복 제거가 깨지고 계약이 어긋난다.
