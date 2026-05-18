# 01. 원자화(Atomization) 노트

## 원자화 원칙

1. **하나의 노트 = 하나의 명제(atom)** — 더 잘라낼 수 없는 단위. 다른 명제와 합쳐서 표현하면 두 개로 분리.
2. **출처를 함수처럼** — 같은 명제라도 1심/2심/대법원이 서술하는 방식이 다르면 별개 atom으로. `instance:` 메타데이터로 추적.
3. **Wikilink-first** — 본문에서 다른 atom을 언급할 때는 산문으로 풀어쓰지 말고 `[[atom-id]]`로만 가리킴.
4. **법리(doctrine)와 적용(reasoning)을 분리** — 추상적 룰은 `doctrines/`에, 그 룰을 본 사건에 적용한 판단은 `reasoning/`에. 이 분리가 곧 LLM이 "대법원처럼" 추상화할 수 있는지의 시험대.
5. **사실(fact)과 평가(reasoning)를 분리** — "B는 메일을 열람했다"는 fact, "그러므로 비위행위에 해당한다"는 reasoning.
6. **atom-id 규칙** — `<카테고리>-<3자리번호>-<짧은-슬러그>.md` (예: `D-002-disciplinary-discretion.md`).
7. **메타데이터(YAML front-matter)**:
   ```yaml
   id: F-001-employer-structure
   type: fact | party | procedure | issue | doctrine | reasoning | outcome
   instance: admin | high | supreme | all
   source: 2022구합61595 | 2023누53227 | 2024두64888 | 공통
   tags: [징계해고, 변호사조력권, ...]
   related: [[D-002-disciplinary-discretion]], [[I-001-lawyer-accompaniment]]
   confidence: high | medium | low
   ```

## 디렉터리 구조

```
01_atomized/
├── parties/      P-*  당사자·이해관계자
├── facts/        F-*  사실관계
├── procedure/    PR-* 절차 이력(노동위·법원 단계)
├── issues/       I-*  쟁점
├── doctrines/    D-*  추상 법리
├── reasoning/    R-*  각 심급의 사실 적용·판단
└── outcomes/     O-*  주문·결론
```

## 카테고리 코드

- **P** Party / 당사자
- **F** Fact / 사실
- **PR** Procedure / 절차
- **I** Issue / 쟁점
- **D** Doctrine / 법리
- **R** Reasoning / 적용·판단
- **O** Outcome / 주문

## 시범 케이스 atom 카운트

| 카테고리 | 개수 |
|---|---|
| P 당사자 | 4 |
| F 사실 | 12 |
| PR 절차 | 8 |
| I 쟁점 | 4 |
| D 법리 | 5 |
| R 적용·판단 | 9 |
| O 주문 | 3 |
| **합계** | **45** |

판결문 3건이 45개 atom으로 분해됐고, atom 사이 wikilink는 110+개 형성됨. 이 그래프 자체가
"LLM이 대법원처럼 사고하도록" 훈련시키는 base graph가 됨.
