# Notion 첨부 파일 — 올리고 내리는 법

개인 데이터가 Notion 으로 옮겨간 뒤(2026-10-21) 마스터 이력서 JSON · 튜닝본 PDF · 프렙 문서의
HTML/ICS 는 전부 **Notion 페이지 본문에 붙은 첨부**다. 이 문서가 그 기계적 절차의 유일한 정본이다.
에이전트는 여기만 참조하고, 절차를 각자 문서에 다시 쓰지 않는다.

## 업로드 (로컬 파일 → Notion 페이지)

```
1. mcp__claude_ai_Notion__notion-create-file-upload(filename)
     → upload_url · upload_headers.authorization · id

2. Bash (curl):
     curl -k -s -X POST "<upload_url>" \
       -H "authorization: Bearer <upload_headers.authorization>" \
       -F "file=@<로컬 경로>"
     기대: HTTP 200, 응답 status = "uploaded"
     · upload_url 은 1시간 뒤 만료된다. 만료되면 1 부터 다시.
     · -k 는 사내 프록시가 TLS 를 재서명하기 때문이다 (TLS 를 재서명하는 사내망). 집 PC 에서는 없어도 된다.

3. 페이지 본문에 배치 (notion-create-pages 또는 notion-update-page 의 content):
     마크다운:  <file source="file-upload://<id>" />
     HTML:      <embed source="file-upload://<id>" />
```

```
🚫 Files 속성에 upload id 를 넣지 않는다.
   API 가 "File not found" 로 거부한다. 첨부는 언제나 페이지 본문에 산다.
   Files 속성은 사람이 Notion UI 에서 끌어다 놓는 용도로만 남겨 둔다.
```

## 다운로드 (Notion 페이지 → 로컬)

```
1. mcp__claude_ai_Notion__notion-fetch(page)
     → 본문 마크다운에서 notion-file-block://... 참조를 복사한다
2. mcp__claude_ai_Notion__notion-get-file-download-urls(references)
     → 서명된 URL (수 분 내 만료)
3. Bash:  curl -k -o <로컬 경로> "<서명 URL>"
```

만료되면 2 부터 다시. 내려받은 파일은 `data/cache/` 또는 `.cache/` 아래에만 둔다 — 둘 다 gitignore 이고 재생성 가능하다.

## 텍스트 첨부의 지름길

200 KiB 이하의 텍스트(JSON · MD · YAML)는 `mcp__claude_ai_Notion__notion-create-attachment` 에 `content` 를
직접 넘겨도 된다. curl 왕복이 없다. 그보다 크면 위 업로드 절차.

## 본문 크기

페이지 본문은 **~150 KB 아래**로 유지한다. 그 이상은 본문에 넣지 말고 첨부로 올린다.
(마스터 이력서 JSON · 긴 스윕 리포트 · stories 파일이 여기에 해당한다.)

## 어디에 무엇이 붙는가

| DB / 페이지 | 본문 | 첨부 |
|---|---|---|
| Resume Versions 행 | 변경 요약 | `master_resume.vN.json` `.md` `_audit.md` `_stories.md` — **Current 행의 JSON 이 단일 원천** |
| Tailored 행 | `resume.md` | `resume.json` · PDF · (하위 페이지: cover-letter · tailoring_notes · submit-kit · kits/*) |
| Documents 행 | 문서 마크다운 | HTML · PDF · ICS |
| Outreach Queue 행 | 메시지 초안 | 없음 |
| Settings 페이지 | ```yaml 코드 블록 하나 (autonomy 정책) | 없음 |

`curl` 이 없는 환경에서는 텍스트 첨부만 가능하다(위 지름길). 바이너리(PDF)는 사용자가 Notion UI 로 올린다 — 실패가 아니라 인계다.
