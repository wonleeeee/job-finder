# 업데이트 훅

`git pull` 이후 실행한다. **등급별로 건드릴 것과 말 것이 다르다.**

```
 ⚙️ engine    ─── 덮어씀. 개선된 에이전트 정의·스코어링·계약이 여기 온다.
 🔒 local     ─── 안 건드림. data/ 는 gitignore 라 pull 이 닿지 않는다.
                  단 schema_version 이 올랐으면 hooks/migrate.md 실행.
 ☁️ remote    ─── 파일이 아니다. 계약이 바뀌었으면 Notion DB 속성을 변경해야 한다.
 📄 artifact  ─── 안 건드림. 재생성은 사용자가 명시적으로 요청할 때만.
```

## 순서

```
1. 로컬 스키마 버전 확인
   data/master_resume.json 의 meta.schema_version
   vs schemas/master_resume.schema.json 이 기대하는 버전
   → 다르면 hooks/migrate.md 실행

2. 원격 계약 확인  ★ 로컬 마이그레이션과 다른 문제다
   python3 scripts/notion_tracker.py contract 의 enum 목록
   vs 실제 Notion DB의 select 옵션
   → 새 옵션이 계약에 추가됐으면 Notion DB에 추가한다
   → 계약에서 사라진 옵션은 자동 삭제하지 않는다.
      그 값을 쓰는 행이 있을 수 있다. 보고만 하고 사용자가 정하게 한다.

   ⚠️ 원격 변경 전에는 반드시 백업한다. 파일 복사로 되돌릴 수 없기 때문이다:
      python3 scripts/notion_tracker.py status > data/backups/<날짜>-pre-update.txt
      가능하면 전체 행을 JSON으로 덤프해 data/backups/ 에 남긴다

3. 훅 경로 재확인
   git config core.hooksPath  →  scripts/git-hooks 인지 확인
   (새 clone 이나 설정 초기화 후 풀릴 수 있다)

4. 검증
   python3 scripts/validate_resume.py
   python3 scripts/notion_tracker.py contract
   python3 scripts/notion_tracker.py audit     (토큰 있으면)

5. 변경 요약 보고
   무엇이 바뀌었고 사용자가 알아야 할 것이 무엇인지.
   에이전트 동작이 바뀌었으면 특히 명시한다.
```

## 하지 않는 것

```
🚫 data/ 아래 무엇도 자동으로 덮어쓰지 않는다
🚫 사용자 확인 없이 Notion DB 속성을 삭제하지 않는다
🚫 기존 산출물(tailored/ · docs/)을 재생성하지 않는다
```
