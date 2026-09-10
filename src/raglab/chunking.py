"""Stage 1 — 청킹. 문서를 검색의 최소 단위로 자른다.

⚠⚠ 이 파일의 `TODO` 는 **사용자가 채운다.** (CLAUDE.md §5-T)

──────────────────────────────────────────────────────────────────────────────
왜 이 단계가 첫 코드인가
──────────────────────────────────────────────────────────────────────────────
교본은 RAG 실패 원인 1위를 알고리즘이 아니라 **「파싱 쓰레기」** 로 꼽는다.
그리고 그 다음이 청킹이다. 여기서 깨진 것은 **뒤 단계를 아무리 고쳐도 못 살린다** —
잘린 요금표는 임베딩을 바꿔도, 재순위를 붙여도 복구되지 않는다.

이 코퍼스에는 그 실패가 **일부러** 심어져 있다:
  `data/synthetic/docs/plans_2026.md` 의 요금표는 마크다운 **표**다.
  글자수로 자르면 행 중간이 잘리고, 그 청크를 인용한 답변은 숫자가 전부 틀린다.

──────────────────────────────────────────────────────────────────────────────
이 단계를 마치면 할 수 있게 되는 것
──────────────────────────────────────────────────────────────────────────────
  · 글자수 청킹이 이 코퍼스에서 **무엇을 깨뜨리는지 측정으로 보인다**
  · 구조(헤딩·조·표) 단위로 자르는 코드를 짤 수 있다
  · 각 청크에 「경로」를 붙여 조각만 봐도 출처를 알게 만들 수 있다

⚠ 확인은 `labkit.inspect.show_chunks()` 로 **눈으로** 한다. 테스트 초록색은 이해가 아니다(§7-4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """검색의 최소 단위.

    ⚠⚠ `meta` 를 비워 두지 마라. 교본 §1-2 — **메타데이터는 RAG 의 숨은 절반**이고
      「나중에 넣으려면 전체 재색인」이다. 유효일자·권한등급으로 **검색 단계에서** 거르려면
      지금 실려 있어야 한다.

    Attributes:
        text: 청크 본문
        doc_id: 출처 문서 ID (예: "PLANS-2026")
        path_label: ⚠ 조각만 봐도 출처를 알게 하는 경로.
            예: "[이용약관 > 제4장 요금 > 제21조 국제전화]"
            교본 STEP 3 — 각 청크 앞에 경로를 붙인다
        chunk_id: 문서 내 순번
        meta: 원 문서 메타데이터 (effective_from, acl, superseded_by 등)
    """

    text: str
    doc_id: str
    path_label: str = ""
    chunk_id: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def with_path(self) -> str:
        """경로를 앞에 붙인 본문. 임베딩·검색에 이 형태를 넣는 것이 교본 권고다."""
        return f"{self.path_label}\n{self.text}" if self.path_label else self.text


# ══════════════════════════════════════════════════════════════════════════
#  ① 글자수 청킹 — **일부러 만드는 나쁜 기준선**
# ══════════════════════════════════════════════════════════════════════════

def chunk_by_chars(
    text: str,
    *,
    size: int = 512,
    overlap: int = 64,
) -> list[str]:
    """글자 수로 자른다. **이 코퍼스에서 무엇이 깨지는지 보기 위한 기준선이다.**

    ⚠ 이걸 먼저 짜는 이유: 나쁜 방법을 **직접 돌려 보고 깨지는 것을 눈으로 봐야**
      구조 청킹이 왜 필요한지가 남는다. 설명만 들은 것은 남지 않는다 (§10 원칙 3).

    Args:
        text: 자를 원문
        size: 한 청크의 목표 글자 수
        overlap: 앞 청크와 겹칠 글자 수. 경계에 걸친 문장이 양쪽에서 사라지는 것을 줄인다

    Returns:
        청크 문자열 목록. ⚠ 빈 문자열은 넣지 않는다

    Raises:
        ValueError: overlap 이 size 이상일 때.
            ⚠ 그러면 창이 앞으로 못 나가 **무한 루프**가 된다. 여기서 막아라

    TODO(Stage 1):
        1. `overlap >= size` 면 ValueError. 왜 무한 루프가 되는지 주석으로 적어 둘 것
        2. 0 부터 시작해 `size` 만큼 잘라 담고, 다음 시작점을 `size - overlap` 만큼 전진
        3. 마지막 조각이 공백뿐이면 버린다
        4. ⚠ 짠 뒤 `labkit.inspect.show_chunks()` 로 `plans_2026.md` 를 찍어 보고
           **요금표가 어디서 잘렸는지 눈으로 확인**할 것. 그게 이 함수의 목적이다
    """
    raise NotImplementedError("Stage 1 — chunk_by_chars 를 구현하십시오")


# ══════════════════════════════════════════════════════════════════════════
#  ② 구조 청킹 — 헤딩·표를 지켜서 자른다
# ══════════════════════════════════════════════════════════════════════════

def split_by_heading(text: str) -> list[tuple[str, str]]:
    """마크다운 헤딩(`#`, `##`, `###`)을 경계로 쪼갠다.

    Returns:
        (경로 라벨, 본문) 쌍의 목록.
        경로 라벨은 상위 헤딩을 이어 붙인 것 — 예: "요금제 안내 > 5G 요금제"

    ⚠ 왜 경로가 필요한가: 청크 하나만 검색돼 LLM 에게 건네졌을 때,
      그 조각만 보고는 무슨 문서의 어느 부분인지 알 수 없다.
      교본 STEP 3 — "각 청크 앞에 경로를 붙여 조각만 봐도 출처를 알게 함".

    TODO(Stage 1):
        1. 줄 단위로 훑으며 `#` 개수로 헤딩 깊이를 판정한다
        2. 깊이별 현재 제목을 스택처럼 유지하고, 더 얕은 헤딩을 만나면 아래를 버린다
        3. 헤딩을 만날 때마다 직전까지 모은 본문을 (경로, 본문) 으로 확정한다
        4. ⚠ 첫 헤딩 앞의 본문(서문)을 버리지 마라. 경로 없이라도 담는다
    """
    raise NotImplementedError("Stage 1 — split_by_heading 을 구현하십시오")


def is_table_line(line: str) -> bool:
    """이 줄이 마크다운 표의 일부인가.

    ⚠ 표를 **자르지 않기 위해** 필요하다. 표 한 개 = 청크 한 개가 교본 원칙이다.

    TODO(Stage 1):
        `|` 로 시작하고 `|` 로 끝나는 줄, 또는 구분선(`|---|---|`)을 표로 본다.
        ⚠ 앞뒤 공백을 제거한 뒤 판정할 것
    """
    raise NotImplementedError("Stage 1 — is_table_line 을 구현하십시오")


def chunk_by_structure(
    text: str,
    *,
    doc_id: str,
    meta: dict[str, Any] | None = None,
    max_chars: int = 1200,
) -> list[Chunk]:
    """구조 단위로 자른다. **헤딩을 경계로 하되 표는 절대 쪼개지 않는다.**

    Args:
        max_chars: 이 길이를 넘으면 더 쪼갠다.
            ⚠⚠ 단, **표 중간에서는 쪼개지 않는다.** 그게 이 함수의 존재 이유다

    Returns:
        `Chunk` 목록. `path_label` 과 `meta` 가 채워져 있어야 한다

    ⚠ 왜 max_chars 가 필요한가: 헤딩만으로 자르면 어떤 절은 3,000자가 넘는다.
      너무 긴 청크는 검색 정밀도를 떨어뜨린다(관련 없는 내용이 같이 딸려 온다).
      반대로 너무 짧으면 문맥이 사라진다. **이 둘의 균형이 청킹의 본질이다.**

    TODO(Stage 1):
        1. `split_by_heading` 으로 (경로, 본문) 목록을 얻는다
        2. 각 본문이 `max_chars` 이하면 그대로 `Chunk` 하나
        3. 넘으면 문단(빈 줄) 단위로 나눠 담되,
           ⚠⚠ `is_table_line` 이 참인 연속 구간은 **한 덩어리로 유지**한다
        4. 모든 청크에 `doc_id`·`path_label`·`meta`·`chunk_id` 를 채운다
        5. ⚠ 짠 뒤 `chunk_by_chars` 결과와 나란히 비교하라.
           요금표가 살아 있는지, 길이 분포가 어떻게 달라졌는지
           (`labkit.inspect.show_lengths`)
    """
    raise NotImplementedError("Stage 1 — chunk_by_structure 를 구현하십시오")


def chunk_documents(
    documents: list[Any],
    *,
    max_chars: int = 1200,
) -> list[Chunk]:
    """코퍼스 전체를 청킹한다. `labkit.corpus.load_documents()` 의 결과를 받는다.

    ⚠ 반환 순서가 실행마다 같아야 한다 — 재현성(§13-4).

    TODO(Stage 1):
        각 문서에 `chunk_by_structure` 를 적용해 이어 붙인다.
        `Document.meta` 를 그대로 넘겨 유효일자·권한등급이 청크에 실리게 한다.
    """
    raise NotImplementedError("Stage 1 — chunk_documents 를 구현하십시오")
