`data/` 스냅샷을 지정 경로에 저장한다.

`data/` 는 gitignore라 git이 백업 역할을 하지 않는다. 이 명령이 그 자리를 메운다.

1. `data/autonomy.yaml` 의 `backup.path` 를 읽는다.
   없으면 사용자에게 묻고 그 값을 파일에 기록한다.
   개인 클라우드 동기화 폴더(iCloud / Drive / Dropbox)를 권장한다 —
   백업과 다기기 동기화가 동시에 해결된다.
2. `data/` 전체를 `job-finder-data-<YYYY-MM-DD-HHmm>.zip` 으로 묶어 그 경로에 쓴다.
   `data/backups/` 자체는 아카이브에서 제외한다 (중첩 방지).
3. Notion 상태도 함께 덤프한다 (원격은 파일 복사로 백업할 수 없으므로):
   `python3 scripts/notion_tracker.py status`
   토큰이 있으면 전체 행 JSON 덤프까지.
4. 기존 백업이 10개를 넘으면 오래된 것부터 정리할지 묻는다.
5. 보고: 경로 · 크기 · 포함된 항목 수 (이력서 v-N · 튜닝본 N건 · 회사 폴더 N개)

⚠️ 백업 아카이브에는 개인정보 전부가 들어 있다. 공개 위치에 쓰지 않는다.
   경로가 레포 안이거나 공개 폴더로 보이면 경고하고 확인을 받는다.
