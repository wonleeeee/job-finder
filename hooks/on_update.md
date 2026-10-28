# 업데이트 훅

`git pull` 이후 실행한다. **등급별로 건드릴 것과 말 것이 다르다.**

```
 ⚙️ engine    ─── 덮어씀. 개선된 에이전트 정의·스코어링·계약이 여기 온다.
 ☁️ remote    ─── 파일이 아니다. 개인 데이터 전부가 여기 있다.
                  계약이 바뀌었으면 Notion DB 속성을 변경해야 하고,
                  마스터 스키마가 올랐으면 hooks/migrate.md 로 새 Resume Versions 행을 만든다.
 🔒 local     ─── 포인터(data/notion_databases.json)뿐. pull 이 닿지 않는다.
                  새 DB 키가 생겼으면 provision 으로 채운다.
 ♻️ cache     ─── /sync 로 다시 받으면 된다. 지워도 된다.
```

## 순서

```
0. /sync
   정본을 data/cache/ 로 내려받는다. 이후 검사는 전부 캐시 기준이다.

1. 마스터 스키마 버전 확인
   data/cache/master_resume.json 의 meta.schema_version
   vs schemas/master_resume.schema.json 이 기대하는 버전
   → 다르면 hooks/migrate.md 실행 (새 Resume Versions 행 + Current 이동)

2. 원격 계약 확인  ★ 스키마 마이그레이션과 다른 문제다
   <PY> scripts/notion_tracker.py contract 의 enum 목록
   vs 실제 Notion DB의 select 옵션
   → 새 옵션이 계약에 추가됐으면 Notion DB에 추가한다
   → 계약에서 사라진 옵션은 자동 삭제하지 않는다.
      그 값을 쓰는 행이 있을 수 있다. 보고만 하고 사용자가 정하게 한다.
   → contract.json 의 storage 절에 새 DB 가 생겼는데 포인터에 키가 없으면 hooks/provision.md

   ⚠️ 원격 변경 전에는 반드시 백업한다. 옵션 삭제는 페이지 이력으로 못 되돌린다:
      <PY> scripts/notion_tracker.py status > <backup.path>/<날짜>-pre-update.txt
      가능하면 전체 행을 JSON으로 덤프해 backup.path 에 남긴다

3. 훅 경로 재확인
   git config core.hooksPath  →  scripts/git-hooks 인지 확인
   (새 clone 이나 설정 초기화 후 풀릴 수 있다)

4. 검증
   <PY> scripts/validate_resume.py data/cache/master_resume.json
   <PY> scripts/notion_tracker.py contract
   <PY> scripts/notion_tracker.py audit     (토큰 있으면)

5. 변경 요약 보고
   무엇이 바뀌었고 사용자가 알아야 할 것이 무엇인지.
   에이전트 동작이 바뀌었으면 특히 명시한다.
```

## 하지 않는 것

```
🚫 data/notion_databases.json 을 자동으로 덮어쓰지 않는다 (키 추가만)
🚫 사용자 확인 없이 Notion DB 속성을 삭제하지 않는다
🚫 기존 산출물(Tailored · Documents 행)을 재생성하지 않는다
🚫 캐시에 쓰지 않는다 — 정본에 쓰고 /sync 로 다시 받는다
```
