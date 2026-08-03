승인 대기 건을 대화로 처리한다. (Notion 체크박스 대신 쓰는 경로)

`briefer` 서브에이전트에게 위임한다.

1. `worklane=proposed` 인 행을 점수순으로 번호를 매겨 압축 목록으로 보여준다.
   한 건 = 한 줄. 회사 · 직무 · 점수 · 연봉 · 지역 · 스폰서십 · submit_method.
2. 사용자 응답을 해석한다:
   - `1,3,5` / `1 3 5` / `다 좋아` / `전부` → 승인
   - `2번 패스` / `2는 연봉 때문에` → 거부 + 사유
   - `2번은 제출까지 맡김` → 승인 + 해당 행에 autonomy override 기록
3. 승인 → `worklane: tailored` 대기로 넘기고 `resume-tailor` 를 트리거한다.
   거부 → `worklane: dismissed` + `dismiss_reason`. 행은 삭제하지 않는다.
4. 각각 Activity Log에 이벤트를 남긴다.
5. 결과를 한 줄로 확인한다: `승인 3 · 거부 2 · 튜닝 시작됨`

사유를 주지 않은 거부는 되묻지 말고 `unspecified` 로 기록한다.
접점을 늘리지 않는 것이 이 프로젝트의 원칙이다.
