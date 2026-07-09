# 원자화 거푸집 — 동결 규약 (Frozen Conventions)

> **이 문서의 규약은 한 번 채택되면 변경하지 않는다.** 변경 시 모든 wikilink drift가 발생하므로
> 변경이 불가피하면 사전에 verify.py로 영향 범위를 확정한 뒤 일괄 마이그레이션해야 한다.
>
> 본 시범 케이스 작성 중 가장 큰 단일 결함이 **네이밍 규약이 사후 변경됨**으로 인한 wikilink drift
> 13건이었다. 본 문서는 그 재발을 영구 차단한다.

---

## 1. atom-id 네이밍 규약

### 1.1 포맷

```
<카테고리>-<3자리 번호>-<영문 슬러그>
```

예: `R-005-stage-distinction-high`, `D-005-lawyer-counsel-right`

### 1.2 카테고리 코드 (확장 후 10종)

| 코드 | 의미 | 예시 |
|---|---|---|
| **P** | Party (당사자) | 원고·피고·보조참가인 |
| **F** | Fact (사실) | 인정 사실, 비위 사실 |
| **PR** | Procedure (절차) | 노동위·법원 단계 |
| **I** | Issue (쟁점) | 핵심 쟁점 |
| **D** | Doctrine (법리) | 추상 룰 |
| **R** | Reasoning (적용·판단) | 룰의 본 사건 적용 |
| **O** | Outcome (주문·결론) | 판결 주문 |
| **L** | Law (적용 법령) | 헌법·법률·시행령 조문 |
| **CIT** | Citation (인용 판례) | 인용된 선례 |
| **A** | Actor (행위자) | 변호사·감사관·이사장 등 |

### 1.3 번호 부여

- 카테고리 내에서 **001부터 순차** 부여.
- 한 번 부여된 번호는 **재사용 금지** (atom을 삭제해도 번호는 결번 처리).
- 신규 atom 작성 시 `scripts/preflight.py`로 다음 번호 사전 등록한 뒤 작성.

### 1.4 슬러그

- **영문 소문자 + 하이픈**만 사용 (한국어·언더스코어·대문자 금지).
- 슬러그 끝에 **instance 접미사 사용 시 일관성 의무**:
  - `-admin` (1심)
  - `-high` (2심)
  - `-supreme` (3심)
  - 합의제 / 전 instance 공통이면 접미사 생략
- **한 번 정한 접미사 규칙은 카테고리 내에서 일관 적용.** (예: R-001은 admin만 다루면 `-admin` 접미.
  도중에 `-admin` 없이 만들기 시작하면 모든 R-* atom에 drift 발생.)

### 1.5 변경 금지 원칙

- atom-id가 한 번 공개되면 **rename 금지**.
- 잘못된 id로 발견된 경우, **소스 atom을 삭제하지 말고** ① 올바른 id로 신규 atom 생성 →
  ② 기존 id atom의 본문에 `superseded_by: <new-id>` 메타 추가 → ③ 모든 wikilink를 일괄
  마이그레이션 → ④ 기존 atom은 stub으로 유지 (검색 무결성).

---

## 2. YAML front-matter 의무 필드 (8개)

```yaml
---
id: <atom-id>                          # 파일명과 일치
type: <category-name>                  # party, fact, procedure, issue, doctrine, reasoning, outcome, law, citation, actor
instance: <admin | high | supreme | all | admin+high | admin+high+supreme>
source: <판결문 사건번호 또는 외부 출처>
tags: [<태그1>, <태그2>, ...]          # 한국어 가능
related: [[atom-id1]], [[atom-id2]]    # 양방향 권장 (one-way도 허용)
confidence: <high | medium | low>      # 정보 확실성
status: <stable | wip | superseded>    # 신설 — 변경 이력 추적
---
```

> **status 필드 신설 이유**: 잘못 작명된 atom을 삭제하지 않고 `superseded` 처리하기 위함.

---

## 3. atom 본문 규약

- 본문은 **한 명제**만 다룬다. 다른 명제는 별개 atom으로.
- 다른 atom을 가리킬 때는 `[[atom-id]]` 만 사용, 산문으로 풀어쓰지 않음.
- 인용·증거 번호(갑/을 호증)는 본문 내 괄호로 명시.
- atom의 첫 줄은 `# <한국어 제목>`.
- 본문 마지막에 `>` 블록으로 **메타 코멘트** (왜 이 atom이 필요한가) 1~3줄 권장.

---

## 4. 관계 동사 (신설 확장)

`related:` 필드 외에 본문에서 다음 관계 동사를 사용 가능:

| 관계 동사 | 의미 | 사용 예 |
|---|---|---|
| `cites` | 외부 권위 인용 | doctrine → citation |
| `refines` | 더 정교한 표현 | R-005 refines R-001 |
| `contradicts` | 모순 | (본 사건엔 미사용) |
| `supersedes` | 대체 | 갱신된 사실 |
| `applies` | 룰의 적용 | reasoning applies doctrine |

> 본 시범 케이스에서는 `related`만 사용했으나, 관계 동사가 명시되면 그래프 의미가 풍부해짐.
> 향후 사건부터 본문에 명시 권장.

---

## 5. 작성 워크플로 (재발방지)

```
1. preflight.py 실행 → 다음 atom-id 사전 등록 + 카테고리 코드 검증
2. atom 본문 작성 (이 컨벤션 준수)
3. verify.py 실행 → wikilink·YAML·관계 검증
4. PASS 시에만 commit
5. FAIL 시 본 컨벤션의 어느 조항을 위반했는지 명시 후 수정
```

### 5.1 작성 단계 자동화 룰 (Pre-commit hook 권장)

- commit 전 `scripts/verify.py` 자동 실행
- 실패 시 commit 차단
- 본 저장소에는 `.githooks/pre-commit` 스텁이 있어 `git config core.hooksPath .githooks`로 활성

---

## 6. 금기 사항 (DO NOT)

| # | 금기 | 이유 |
|---|---|---|
| 1 | atom-id 사후 변경 | wikilink drift 필연 |
| 2 | 본문에 다른 atom의 내용을 산문으로 복제 | DRY 위반, 갱신 시 모순 |
| 3 | `related` 필드 비우기 | 고아 노드 발생 |
| 4 | confidence 없이 단정 | 마케팅 파이프라인 컴플라이언스 위반 위험 |
| 5 | source 없이 사실 인정 | 출처 추적성 상실 |
| 6 | 카테고리 코드를 자의적으로 신설 | 본 컨벤션 §1.2 외 코드 금지 (확장은 본 문서 개정 후) |
| 7 | 한국어 슬러그 사용 | 도구·OS 호환성 |
| 8 | 한 atom에 여러 명제 | 원자화 본질 위반 |

---

## 7. 본 컨벤션 위반 시 처리

- verify.py가 자동 차단.
- 우회 commit 시도 시 reviewer가 본 컨벤션 조항 번호를 인용하여 reject.
- 컨벤션 자체의 갱신은 **모든 atom·wikilink 영향 분석 + 일괄 마이그레이션**을 동반해야 가능.

---

> **마지막 갱신**: 2026-05-18 (시범 케이스 RCA 결과 반영, status 필드 신설, 카테고리 코드 7→10 확장)
