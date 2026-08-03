# 설치 훅

허브(또는 사용자)가 이 프로젝트를 처음 설치할 때 실행한다. **멱등**이어야 한다.

## 순서

```
1. PRECHECK ────────────────────────────────────────────────
   Notion MCP 연결 확인          ❌ → 안내 후 중단 (필수 의존성)
   python3 + jsonschema 확인      ❌ → 경고. 검증 없이 진행 가능
   Gmail / Calendar MCP 확인      ❌ → 경고만. 기능이 줄 뿐 깨지지 않는다

2. 커밋 사고 방지 훅 설치 ──────────────────────────────────
   git config core.hooksPath scripts/git-hooks
   → data/ 아래가 스테이징되면 커밋을 막는다

3. SEED ────────────────────────────────────────────────────
   data/master_resume.json  없으면  templates/master_resume.example.json 복사
   data/autonomy.yaml       없으면  templates/autonomy.example.yaml 복사
   data/tailored/ · data/docs/ · data/backups/ 디렉터리 생성
   ⚠️ 이미 있으면 절대 덮어쓰지 않는다

4. PROVISION ───────────────────────────────────────────────
   hooks/provision.md 실행 → Notion DB 생성 + 포인터 기록

5. 검증 ────────────────────────────────────────────────────
   python3 scripts/validate_resume.py
   python3 scripts/notion_tracker.py contract

6. 온보딩 안내 ─────────────────────────────────────────────
   시드된 master_resume.json 은 예시 데이터다. 사용자에게 명확히 알린다.
   → resume-curator 를 불러 초기 온보딩을 시작하도록 안내
   → 예상 소요: 3~5시간, 여러 세션으로 나눠도 된다
```

## 사용자에게 전달할 메시지

```
설치 완료. 다음 순서로 시작하세요.

1. 마스터 이력서 구축      resume-curator 와 대화 (3~5시간, 나눠서 가능)
                           지금 있는 것은 예시 데이터입니다
2. 선호 설정               목표 직무·지역·연봉·제외 목록
3. 자율성 확인             data/autonomy.yaml — 기본은 안전한 쪽입니다
4. 첫 스윕                 job-hunter 에게 "공고 찾아줘"
5. 이후                    매주 월요일 브리핑만 확인하면 됩니다
```
