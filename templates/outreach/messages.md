# 아웃리치 메시지 골격

세 종류만 있다. `{…}` 는 마스터 이력서·JD·Contacts·Settings(`outreach.identity`)에서 채운다. **마스터에 없는 사실·숫자는 채우지 않는다.**
첫 메시지(A·B)에는 비자·H-1B·스폰서십을 쓰지 않는다.

## A. 연결 요청 노트 — 300자 이내

공고 하나 + 질문 하나. 자기소개는 한 구절.

```
Hi {first_name} — I'm {identity.intro_en} working on {one-phrase current domain}.
I saw {Company}'s {JD title} opening{, which you posted / on your team}. One quick question:
{one concrete question about the role or team — not "is it still open"}.
Would appreciate connecting.
— {identity.signoff}
```

각도별 첫 문장 교체:
- `posting` 그대로.
- `korean` (`identity.heritage.language`, 예: 한국어) `안녕하세요 {직함} {성}님, {identity.intro_ko}입니다. {Company} {직무} 공고를 보고 연락드립니다. 한 가지만 여쭙고 싶습니다 — {질문}.`
- `alumni` `Fellow {identity.schools 중 상대와 겹치는 학교} alum here —`
- `domain` `{identity.domain_line}`
- `mutual` `We're both connected with {mutual_name} —`

## B. 본 메시지 — 수락 후, 80~120단어

JD 의 요구 **하나** ↔ 마스터의 증거 **하나**. 요청은 **하나**.

```
Thanks for connecting, {first_name}.

The {JD title} posting asks for {one requirement quoted or paraphrased from the JD}.
That's close to what I do now: {one bullet from master_resume, numbers only if they are in master}.

I'm applying through the careers site this week. If you have 15 minutes in the next two weeks,
I'd value hearing how the team {one specific thing about the team's work}.
{OR: If a referral is possible on your side, I'd be glad to send a short summary.}

Either way, thanks for reading.
— {identity.signoff}
```

증거 후보: `identity.evidence` (마스터 불릿 id) · `identity.evidence_extra`.
AI 각도면 `identity.evidence_ai` 만. `identity.banned_claims` 의 수치·주장은 쓰지 않는다.

## C. 후속 — +7일, 한 번만

새 정보 하나를 들고 간다. 재촉 문구 없음.

```
Hi {first_name}, quick follow-up. I submitted my application for {JD title} on {date}{; req {id}}.
If a 15-minute chat isn't possible, even a one-line pointer on who owns hiring for the team would help.
Thanks either way.
— {identity.signoff}
```

## 답장이 왔을 때 (사용자 발송 — 에이전트는 초안만)

- 비자를 물으면: `I'm currently on an H-1B; a transfer isn't subject to the cap lottery, so it runs on the normal hiring timeline.`
- 연봉을 물으면: 희망 연봉은 건별 결정 규칙을 따른다 — 공개 레인지가 있으면 그 안에서, 없으면 `Open to discussing based on the role's range and total compensation.`
- 일정 제안이 오면: Google Calendar 로 가능한 슬롯 3개를 뽑아 초안에 넣는다.
