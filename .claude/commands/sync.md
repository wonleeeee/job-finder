Notion 정본을 로컬 캐시로 내려받는다. **마스터 이력서나 자율성 정책이 필요한 세션은 이걸 먼저 돈다.**

정본은 Notion 에 있다 (Resume Versions 의 Current 행 · Settings 페이지). 로컬 `data/cache/` 는
재생성 가능한 사본일 뿐이다. 쓰기는 캐시로 가지 않는다 — resume-curator 는 새 버전 행을 올리고,
정책 수정은 Settings 페이지에서 한다.

1. `data/notion_databases.json` 을 읽는다. 없으면 `hooks/provision.md` 를 안내하고 중단.
2. **마스터 이력서**
   - `databases.resume_versions` 를 `Current = __YES__` 로 조회한다 (`notion-query-data-sources`).
     정확히 1행이어야 한다. 0행 또는 2행 이상이면 경고하고 중단 (tracker 감사 항목).
   - 그 행을 `notion-fetch` → 본문의 `master_resume.vN.json` 첨부 참조를 받아
     `data/cache/master_resume.json` 으로 내려받는다 (절차: `hooks/notion-files.md` 다운로드).
     `.md` 는 요청이 있을 때만 (`data/cache/master_resume.md`).
   - `<PY> scripts/validate_resume.py data/cache/master_resume.json` — Python 이 없으면 생략하고 명시.
3. **자율성 정책**
   - `pages.settings` 를 `notion-fetch` → 본문의 ```yaml 코드 블록 하나를 그대로
     `data/cache/autonomy.yaml` 에 쓴다. 블록이 없거나 둘 이상이면 경고.
4. 한 줄 보고: `sync · 이력서 v23 (2026-10-15) · 정책 갱신 2026-10-21 · 캐시 data/cache/`

Notion 에 닿지 못하면 **캐시를 쓰고 그 사실을 말한다** — "캐시 사용 중 (마지막 sync <날짜>)".
캐시도 없으면 그 세션에서 이력서·정책이 필요한 작업은 하지 않는다.

`data/cache/tailored/<id>/` 는 이 명령이 건드리지 않는다. resume-tailor 가 작업할 때 Tailored 행에서 내려받는다.
