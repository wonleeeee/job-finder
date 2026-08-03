설정·의존성·데이터 위생을 점검한다. **플래그만 하고 자동 수정하지 않는다.**

데이터 등급별로 검사 항목이 다르다 (DESIGN.md §5).

## ⚙️ engine

```
git 상태 · 현재 ref
python3 존재 · jsonschema 설치 여부
scripts/ 실행 가능 여부
git config core.hooksPath == scripts/git-hooks    ← 풀려 있으면 재설정 안내
```

## 🔒 local

```
data/master_resume.json 존재 · 스키마 검증 통과
  python3 scripts/validate_resume.py
meta.schema_version 이 현재 스키마와 일치하는가  → 아니면 migrate 안내
data/autonomy.yaml 존재 · 파싱 가능
templates/ 의 예시 데이터가 그대로인가          → 온보딩 미완료 신호

★ git ls-files data/   결과가 비어 있는가
  비어 있지 않으면 심각 경고 — 개인정보가 이미 커밋됐다는 뜻이다.
  이력에서 제거하는 방법을 안내한다 (git filter-repo / BFG).
```

## ☁️ remote

```
Notion MCP 연결
data/notion_databases.json 존재 · 각 database_id 가 유효한가 (notion-fetch 1회)
★ 실제 DB의 select 옵션 ↔ 계약 enum 일치 여부
  python3 scripts/notion_tracker.py contract 와 대조
  사람이 Notion에서 손으로 옵션을 추가하면 에이전트 쓰기가 조용히 실패한다.
  실전에서 가장 자주 깨지는 항목이다.
필수 뷰 3개(승인 대기 / 활성 / 내 차례)가 존재하는가
```

## 📄 artifact

```
python3 scripts/notion_tracker.py audit    (토큰 있으면)
고아 아티팩트: data/tailored/<id>/ 는 있는데 Notion에 해당 Job 이 없음
역방향: worklane=tailored 인데 data/tailored/<id>/ 가 없음
data/docs/<company>/ 에 README.md 가 없는 폴더
```

## 출력

심각도순 펀치 리스트. 각 항목에 **고치는 방법**을 붙인다.

```
🔴 치명   지금 동작을 막는 것 (MCP 미연결, 이력서 검증 실패, data/ 커밋됨)
🟡 경고   기능이 줄어드는 것 (Gmail MCP 없음, submit_method 누락)
🟢 정보   개선 여지 (백업 오래됨, 갭 누적, 고아 아티팩트)
```

문제가 없으면 한 줄로 끝낸다: `OK — 점검 항목 N개 통과`
