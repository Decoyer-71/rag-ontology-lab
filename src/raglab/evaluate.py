"""Stage 5 — 평가. 얼마나 맞히는지 재고, 틀린 것을 A·B·C 로 쪼갠다.

⚠⚠ 이 파일의 `TODO` 는 **사용자가 채운다.** (CLAUDE.md §5-T)

──────────────────────────────────────────────────────────────────────────────
왜 이 단계가 있는가
──────────────────────────────────────────────────────────────────────────────
교본은 RAG 실패 1순위를 **「골든셋 없이 튜닝한다」** 로 꼽습니다.
체감으로 판단하면 튜닝이 미신이 됩니다. 그래서 채점표를 먼저 만들었고(Stage 0),
여기서 그 채점표로 **숫자를 냅니다.**

그리고 더 중요한 것 — **"답이 틀렸다"는 진단이 아닙니다.**
반드시 원인을 셋으로 쪼갭니다:

    A 검색 실패  — 정답 청크가 후보에 못 들어왔다  → 하이브리드·재순위·청킹 재조정
    B 자료 부재  — 문서에 답이 아예 없다            → ⚠ 문서를 만들어야 한다. RAG로는 못 고친다
    C 생성 실패  — 찾고도 잘못 썼다                 → 프롬프트·컨텍스트 축소

교본 경험칙: **초기 프로젝트 실패의 60~70%가 A** 입니다.
모델을 바꿔서 해결하려는 시도는 이 통계를 모를 때 나오는 대표적 낭비입니다.

──────────────────────────────────────────────────────────────────────────────
⚠⚠ 이 단계에서 가장 조심할 것 — 골든셋 오염 (CLAUDE.md §5-E')
──────────────────────────────────────────────────────────────────────────────
  · 튜닝은 `split="dev"` 로만 한다. `holdout` 은 단계가 닫힐 때 한 번만 연다
  · **Recall@5 가 0.95 이상이면 축하가 아니라 경보다.** 오염을 먼저 의심하라
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass
class EvalResult:
    """한 질문의 평가 결과.

    Attributes:
        qid: 골든셋 문항 ID
        retrieved: 검색된 청크/문서 ID 목록 (순위 순)
        gold: 정답 근거 ID 목록 (`must_cite`)
        hit_rank: 정답이 처음 나온 순위(1부터). 못 찾았으면 None
        failure_type: "A" | "B" | "C" | None(성공)
    """

    qid: str
    retrieved: list[str]
    gold: list[str]
    hit_rank: int | None = None
    failure_type: str | None = None


# ══════════════════════════════════════════════════════════════════════════
#  ① 지표
# ══════════════════════════════════════════════════════════════════════════

def recall_at_k(results: Sequence[EvalResult], k: int) -> float:
    """Recall@k — 정답 근거가 상위 k 개 안에 들어온 질문의 비율.

    Returns:
        [0, 1] 비율

    ⚠⚠ **분모가 무엇인지 분명히 하라** (CLAUDE.md §4).
      분모는 **골든셋 문항 수**다. 검색된 문서 수를 분모로 쓰면 그건 정밀도(precision)다.
      이름과 실제 계산이 어긋나는 것이 이 도메인의 전형적 결함이다.

    ⚠ `must_cite` 가 여러 개인 문항을 어떻게 셀 것인가:
      하나만 찾아도 성공인가, 전부 찾아야 성공인가?
      **결정하고 주석에 이유를 적어라.** 이 코퍼스의 비교종합 유형(G-020 등)은
      두 문서를 전부 봐야 답이 되므로, 이 선택이 수치를 크게 바꾼다.

    ⚠ `must_cite` 가 **빈 문항**(관계형·부재형)은 어떻게 할 것인가?
      Recall 계산에서 제외하는 것이 맞다. 제외하면 **분모가 달라진다** — 그것도 보고하라.

    TODO(Stage 5):
        위 세 결정을 내리고 구현한다.
    """
    raise NotImplementedError("Stage 5 — recall_at_k 를 구현하십시오")


def mean_reciprocal_rank(results: Sequence[EvalResult]) -> float:
    """MRR — 정답이 나온 순위의 역수 평균.

    ⚠ Recall 과 무엇이 다른가: Recall 은 "찾았나"만 보고, MRR 은 **"몇 번째로 찾았나"** 를 본다.
      정답이 1위인 것과 20위인 것은 사용자 체감이 전혀 다르다.
      **둘 다 봐야 한다** — 하나만 보고하는 것이 §5-D' 가 막으려는 병이다.

    ⚠ 못 찾은 질문의 기여를 0 으로 둘 것인가, 분모에서 뺄 것인가?
      **결정하고 주석에 적어라.** 0 으로 두는 것이 관행이지만 그 이유를 알고 써라.

    TODO(Stage 5):
        `hit_rank` 가 있으면 `1/hit_rank`, 없으면 위 결정대로. 평균을 낸다.
    """
    raise NotImplementedError("Stage 5 — mean_reciprocal_rank 를 구현하십시오")


# ══════════════════════════════════════════════════════════════════════════
#  ② 기준선 — ⚠ 이걸 못 이기면 실패한 검색기다 (CLAUDE.md §5-D')
# ══════════════════════════════════════════════════════════════════════════

def baseline_first_k(chunk_ids: Sequence[str], k: int = 5) -> list[str]:
    """아무 계산 없이 **앞에서 k 개**. 가장 멍청한 기준선.

    ⚠ 왜 필요한가: 정교한 검색기가 이걸 못 이기면 그 검색기는 아무 일도 안 한 것이다.
      기준선 없는 성능 보고는 결함이다.

    TODO(Stage 5): 앞에서 k 개를 돌려준다. (⚠ 이 함수는 쉽다. 중요한 건 **쓰는 것**이다)
    """
    raise NotImplementedError("Stage 5 — baseline_first_k 를 구현하십시오")


def baseline_random_k(chunk_ids: Sequence[str], k: int = 5, *, seed: int = 42) -> list[str]:
    """무작위 k 개.

    ⚠⚠ **시드를 반드시 고정한다.** 실행마다 값이 바뀌면 기준선이 기준이 아니다(§13-4 재현성).

    TODO(Stage 5): 고정 시드로 k 개를 뽑는다.
    """
    raise NotImplementedError("Stage 5 — baseline_random_k 를 구현하십시오")


# ══════════════════════════════════════════════════════════════════════════
#  ③ 평가 실행
# ══════════════════════════════════════════════════════════════════════════

def evaluate(
    questions: Sequence[dict[str, Any]],
    search_fn: Callable[[str], list[str]],
    *,
    k: int = 5,
) -> list[EvalResult]:
    """골든셋 전체를 돌려 결과 목록을 만든다.

    Args:
        questions: `labkit.corpus.load_golden_set(split="dev")` 의 결과
        search_fn: 질의 문자열을 받아 청크/문서 ID 목록을 순위 순으로 돌려주는 함수
        k: 상위 몇 개까지 볼 것인가

    ⚠ `must_cite` 의 형식은 `"TERMS-2026#제21조"` 처럼 **문서ID#절** 이다.
      청크 ID 와 어떻게 대조할지 **결정하고 주석에 적어라** —
      문서 ID 만 맞으면 성공인가, 절까지 맞아야 하는가?
      느슨하게 보면 수치가 후해지고, 엄격하게 보면 청킹 방식에 따라 불공평해진다.

    TODO(Stage 5):
        각 질문에 `search_fn` 을 돌리고 `EvalResult` 를 만든다. `hit_rank` 를 채운다.
    """
    raise NotImplementedError("Stage 5 — evaluate 를 구현하십시오")


# ══════════════════════════════════════════════════════════════════════════
#  ④ ⚠⚠ A·B·C 실패 분해 — 이 단계의 본체
# ══════════════════════════════════════════════════════════════════════════

def classify_failure(
    result: EvalResult,
    question: dict[str, Any],
    *,
    wide_k: int = 20,
    wide_retrieved: Sequence[str] | None = None,
) -> str | None:
    """실패 원인을 A·B·C 로 분류한다.

    Args:
        wide_retrieved: 더 넓게(k=20) 검색했을 때의 결과.
            ⚠ **A 와 C 를 가르는 데 필요하다** — 좁게는 못 찾았는데 넓게는 찾았다면
            검색 자체는 되는데 순위가 문제인 것이다

    Returns:
        "A" | "B" | "C" | None(성공)

    판정 기준:
        B (자료 부재) — 골든셋의 `type` 이 "부재" 이거나 `must_cite` 가 비어 있다.
                       ⚠⚠ **이건 RAG 로 못 고친다.** 문서를 만들어야 한다.
                          여기에 튜닝 시간을 쓰는 것이 가장 흔한 낭비다
        A (검색 실패) — 정답 청크가 후보 k 개 안에 없다
        C (생성 실패) — 후보에는 들어왔는데 답이 틀렸다
                       ⚠ 이 프로젝트는 생성(LLM 호출)이 선택이므로,
                          생성 없이 평가할 때는 C 를 판정할 수 없다.
                          **그 사실을 반환값이 아니라 주석·리포트에 명시하라**

    ⚠⚠ **"틀렸다"로 뭉뚱그리지 마라.** 셋은 처방이 완전히 다르고,
      그 사실을 아는 것이 이 프로젝트에서 배우는 가장 값진 것이다(§13-2).

    TODO(Stage 5):
        위 기준으로 분류한다. 판정 불가한 경우를 어떻게 표시할지 결정하라.
    """
    raise NotImplementedError("Stage 5 — classify_failure 를 구현하십시오")


def failure_report(results: Sequence[EvalResult]) -> dict[str, Any]:
    """A·B·C 분포와 문항 목록.

    Returns:
        `{"A": [...qid], "B": [...], "C": [...], "success": [...],
          "counts": {...}, "n_total": int}`

    ⚠ **분모(n_total)를 반드시 담아라** (§4). 비율만 있는 보고는 결함이다.

    ⚠ 이 결과가 다음 단계의 방향을 정한다:
      A 가 많으면 → 검색을 고친다 (하이브리드·재순위·청킹)
      B 가 많으면 → ⚠ 코퍼스에 공백이 있다. 튜닝으로 못 고친다
      C 가 많으면 → 프롬프트·컨텍스트를 고친다

    TODO(Stage 5):
        집계해서 위 형태로 돌려준다.
    """
    raise NotImplementedError("Stage 5 — failure_report 를 구현하십시오")
