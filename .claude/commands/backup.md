오프라인 사본을 만든다. **1차 백업은 Notion 이다** — 페이지 버전 이력이 있고, 마스터 이력서는 Resume Versions 행 하나가 버전 하나다.
이 명령은 Notion 이 사라지는 경우에 대비한 **선택적** 2차 사본이다. 일상 백업이 아니다.

1. `/sync` 를 돈다. 캐시(`data/cache/master_resume.json` · `autonomy.yaml`)가 최신이어야 한다.
2. `data/cache/autonomy.yaml` 의 `backup.path` 를 읽는다.
   없으면 사용자에게 묻고, 값은 **Notion Settings 페이지**의 yaml 블록에 적도록 안내한다 (캐시에 쓰지 않는다).
   개인 클라우드 동기화 폴더(iCloud / Drive / Dropbox)를 권장한다.
3. (선택 — 사용자가 "zip 까지" 라고 했을 때만) Resume Versions 의 `Current` 행에서 첨부 4개
   (`master_resume.vN.json` `.md` `_audit.md` `_stories.md`)를 내려받고 (`hooks/notion-files.md`),
   `data/cache/` 와 함께 `job-finder-cache-<YYYY-MM-DD-HHmm>.zip` 으로 묶어 그 경로에 쓴다.
   Tailored · Documents · Outreach Queue 는 묶지 않는다 — 양이 많고 Notion 이력으로 충분하다.
   필요하면 `<PY> scripts/notion_tracker.py export` 로 파이프라인 행을 JSON 덤프해 같이 넣는다.
4. 기존 zip 이 `backup.keep`(기본 10)개를 넘으면 오래된 것부터 정리할지 묻는다.
5. 보고: `sync 완료 · 이력서 v<N> · 정책 <날짜>` (+ zip 경로 · 크기)

`data/backups/` 는 더 이상 없다. 이전 버전은 Resume Versions 의 `Current` 가 꺼진 행들이다 — 되돌리기는
`Current` 체크를 옮기는 것으로 끝난다.

⚠️ zip 에는 개인정보 전부가 들어 있다. 공개 위치에 쓰지 않는다.
   경로가 레포 안이거나 공개 폴더로 보이면 경고하고 확인을 받는다.
