# <회사> — <직무>

> <상태> · 최종 갱신 <YYYY-MM-DD>
> 채용 경로: <리크루터명 / 리퍼럴 / 직접 지원> · 회사: <한 줄 소개>

<!--
interview-coach 가 **Jobs 행의 Notes** 를 채울 때 쓰는 골격 (2026-10-21 부터 — 이전엔 회사 폴더의 README.md).
Jobs 행이 진입점이고, 문서 인덱스는 Jobs.Documents 관계가 대신한다. 아래 「문서」 표는 그 관계에 어떤
Documents 행(Type · Name)이 있어야 하는지의 예시다. Name 에 회사 접두사를 넣지 않는다 — Company 가 이미 회사다.
-->

## 진행 상황

```
 ✅ 2026-00-00  리크루터 스크리닝                    → 합격
 ✅ 2026-00-00  1차 — 하이어링 매니저 (60분)         → 합격
 ⬜ 미정        2차 — 기술 면접                       ← 준비 중
 ⬜             연봉 협상
```

## 문서 (Jobs.Documents 관계 — Documents DB 행)

| Type | Name | 무엇 |
|---|---|---|
| `jd-analysis` | JD analysis — <직무> | 원본 JD (첨부) + 분석 |
| `research` | Research | 회사·제품·자금·경쟁사 |
| `interview-prep` | Interview — HM 2026-00-00 | 1차 프렙 + 결과 기록 |
| `negotiation` | Comp negotiation | 연봉 전략 |

## 상황별 읽는 순서

```
 기술 면접 준비    Interview — Tech → Research
 연봉 얘기가 오면  Comp negotiation → Research
 회사를 다시 볼 때 Research
```

## 같은 행에서 닿는 것

```
 Jobs.Tailored (관계) / Tailored resume (url)   이 포지션용 튜닝 이력서 + 하위 페이지 submit-kit
 Resume Versions · Current 행                     마스터 이력서 (v<n>, Master version 참조)
 Jobs.Contacts (관계)                             리크루터 · 면접관
```

## 열려 있는 것

```
 프렙 빈칸        <무엇이 비었나 — 사람만 아는 사실>
 회사에 확인 필요  <스폰서십 · base/total 여부 · 에쿼티 · 근무 형태 · 온콜>
```

## 주의

```
 🚫 <언급 금지 — 이해충돌 · 현직장 내부 정보 등>
 🚫 <모순 — 이전 면접이나 제출 이력서와 어긋나는 지점 + 전환 스크립트>
```

<!--
⚠️ 「주의」 섹션을 비워두지 않는다.
현직장이 상대 회사의 고객사이거나, 리크루터가 보낸 이력서가 튜닝본과 다르거나,
이전 라운드에서 한 말과 모순되는 지점이 있으면 반드시 여기 적는다.
이런 사고는 준비 부족보다 치명적이다.
-->
