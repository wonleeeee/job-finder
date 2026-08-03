# Stable ID 명세

중복 제거 보조 키. `scripts/notion_tracker.py stable-id` 가 이 명세를 구현하고,
Python이 없으면 **에이전트가 이 문서를 따라 직접 생성한다.**

## 알고리즘

```
입력:  company · role · posted(YYYY-MM-DD, 없으면 오늘)
출력:  <company-slug>-<role-slug>-<YYYY-MM>

slug(s):
  1. 소문자화
  2. 앞뒤 공백 제거
  3. 영문자·숫자가 아닌 연속 문자를 하이픈 하나로 치환
  4. 앞뒤 하이픈 제거
  5. 40자로 절단
  6. (절단 후) 앞뒤 하이픈 다시 제거
```

## 예시 — 구현이 맞는지 대조할 것

| company | role | posted | 결과 |
|---|---|---|---|
| `Anthropic` | `Senior Backend Engineer` | 2026-04-11 | `anthropic-senior-backend-engineer-2026-04` |
| `Acme Fintech, Inc.` | `Platform Engineer` | 2026-08-01 | `acme-fintech-inc-platform-engineer-2026-08` |
| `X` | `SWE (L5)` | 2026-08-01 | `x-swe-l5-2026-08` |
| `한화큐셀` | `Backend Engineer` | 2026-08-01 | `backend-engineer-2026-08` |

마지막 예시가 중요하다 — **비ASCII는 전부 탈락한다.** 회사명이 통째로 사라질 수 있으므로
한글 회사명은 영문 표기를 쓰거나, stable-id에만 의존하지 말고 아래 조회 방어선을 반드시 쓴다.

## ⚠️ stable-id에만 의존하지 않는다

입력(company·role)을 JD에서 뽑는 단계가 이미 비결정적이다.

```
   JD 원문
     │  "Anthropic" vs "Anthropic PBC"
     ▼  "Senior Backend Engineer" vs "Backend Engineer, Senior"
   추출  ← 여기서 흔들리면
     │
     ▼
   slug()  ← 여기가 결정적이어도 소용없다
```

그래서 **중복 제거의 진짜 방어선은 조회다:**

```
1. stable-id 로 정확 일치 검색       → 있으면 중복
2. 없으면 회사명 + 직무명으로 퍼지 검색  ← 이게 실질적 방어선
3. 후보가 나오면 JD URL 을 대조
4. 그래도 애매하면 새로 저장하되 Notes 에 "유사 건 있음: JOB-n" 을 남긴다
```

1번만 하고 2번을 건너뛰면 같은 공고가 두 번 들어온다.
