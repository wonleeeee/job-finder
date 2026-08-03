# 데이터 마이그레이션 지침

`schemas/master_resume.schema.json` 이 기대하는 `meta.schema_version` 이
사용자의 `data/master_resume.json` 보다 높을 때 실행한다.

## 원칙

```
1. 비파괴  마이그레이션 전 data/backups/master_resume.<oldVersion>.json 으로 백업
2. 순차    한 번에 한 버전씩 (1.0.0 → 1.1.0 → 2.0.0)
3. 검증    각 단계 후 <PY> scripts/validate_resume.py
4. 보고    완료 후 무엇이 바뀌었는지 사용자에게 요약
5. 중단    어느 단계든 검증 실패 시 백업에서 복구하고 중단. 억지로 진행하지 않는다
```

**Stable ID는 마이그레이션에서도 신성하다.** 필드 이름이 바뀌어도
`experience[].id` 와 `bullets[].id` 는 그대로 유지한다. 이걸 깨면
`data/tailored/` 의 모든 산출물이 마스터를 역참조하지 못하게 된다.

## 원격(Notion) 계약 마이그레이션

로컬 파일과 **다른 절차**다. 백업을 파일 복사로 할 수 없다.

```
1. 덤프    현재 전체 행을 JSON으로 data/backups/<날짜>-notion.json 에 저장
2. 추가    새 select 옵션을 DB에 추가 (추가는 안전)
3. 이행    기존 행의 값을 새 어휘로 변환 (필요한 경우)
4. 삭제    옛 옵션 제거는 사용자 확인 후에만. 그 값을 쓰는 행이 0인지 먼저 확인
5. 검증    <PY> scripts/notion_tracker.py audit
```

## 버전별 변경

### v1.0.0 (최초)

기준 스키마. 마이그레이션 없음.

<!--
스키마를 바꿀 때마다 아래 형식으로 추가한다:

### v1.0.0 → v1.1.0
- 무엇이 왜 바뀌었는지
- 각 항목을 어떻게 변환하는지 (기본값 · 필드 이름 변경 · 삭제 대상)
- Notion 계약도 함께 바뀌는가? 그렇다면 위 원격 절차도 실행
- 되돌리는 방법
-->
