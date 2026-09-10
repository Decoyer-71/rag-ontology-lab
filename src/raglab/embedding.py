"""Stage 2 — 임베딩. 의미를 숫자 배열로 바꾼다. TF-IDF 를 numpy 로 직접.

⚠⚠ 이 파일의 `TODO` 는 **사용자가 채운다.** (CLAUDE.md §5-T)

──────────────────────────────────────────────────────────────────────────────
트랜스포머를 아는 사람에게
──────────────────────────────────────────────────────────────────────────────
여러분이 아는 그 임베딩이 맞습니다. 다만 **토큰 하나가 아니라 문단 하나**를
벡터 하나로 누른 것이고, 여기서는 신경망 대신 **글자 통계**로 그 벡터를 만듭니다.

왜 신경망부터 안 쓰는가:
  신경망 임베딩은 "왜 이 문서가 검색됐는가"를 **손으로 따라갈 수 없습니다.**
  TF-IDF 는 각 차원이 **단어 하나**라서, 어떤 단어가 얼마나 기여했는지 눈으로 볼 수 있습니다.
  먼저 이 투명한 버전으로 「벡터 = 좌표」를 손에 익히고,
  **Stage 9 에서 신경망으로 교체해 개선폭을 잽니다.** 그때 비교 대상이 있어야 합니다.

──────────────────────────────────────────────────────────────────────────────
이 단계를 마치면 할 수 있게 되는 것
──────────────────────────────────────────────────────────────────────────────
  · TF·IDF 각 항이 **무엇을 보정하려고** 있는지 설명할 수 있다
  · 문서-단어 행렬을 만들고 어떤 단어가 왜 높은 가중치를 받았는지 짚을 수 있다
  · ⚠ TF-IDF 가 **원리적으로 못 잇는 것**(환불 ↔ 청약철회)을 이 코퍼스에서 재현할 수 있다

⚠ 확인은 `labkit.inspect.show_vector()` 로 **눈으로** 한다.
"""
from __future__ import annotations

import numpy as np


# ══════════════════════════════════════════════════════════════════════════
#  ① 토크나이즈
# ══════════════════════════════════════════════════════════════════════════

def tokenize(text: str) -> list[str]:
    """텍스트를 검색 단위 토큰으로 자른다.

    ⚠⚠ 한국어에서 이 함수가 이 프로젝트의 **가장 큰 근사(approximation)** 다.
      공백으로만 자르면 조사가 붙는다 — "요금제는" ≠ "요금제" ≠ "요금제를".
      제대로 하려면 형태소 분석기가 필요하지만 이 venv 에는 없다(§2).

    ⚠ **그 사실을 아는 채로 그렇게 하는 것**과 모르고 하는 것은 다르다.
      Stage 5 에서 이 근사가 어떤 질의를 망가뜨리는지 **측정으로** 확인한다.

    TODO(Stage 2):
        1. 소문자화한다 (영문 코드 `LTE-S-33` 대소문자 흔들림 대비)
        2. 한글·영문·숫자만 남기고 나머지는 공백으로 바꾼다
           ⚠ 단, 요금제 코드의 하이픈(`5G-STD-69`)을 살릴지 죽일지 **결정하고 주석에 이유를 적어라**.
              이 선택이 Stage 4 의 코드조회 성능을 좌우한다
        3. 공백으로 나누고 빈 토큰을 버린다
        4. ⚠ 1글자 토큰을 버릴지도 결정 사항이다. 버리면 "폰"·"돈" 같은 질의가 죽는다
    """
    raise NotImplementedError("Stage 2 — tokenize 를 구현하십시오")


def build_vocabulary(token_lists: list[list[str]], *, min_df: int = 1) -> list[str]:
    """전체 문서에서 어휘 목록을 만든다. **벡터의 각 차원이 여기 단어 하나에 대응한다.**

    Args:
        min_df: 최소 문서 빈도. 이 미만으로 나타나는 단어는 버린다

    Returns:
        ⚠⚠ **정렬된** 어휘 목록. 순서가 실행마다 바뀌면 벡터가 달라지고
          측정이 재현되지 않는다(§13-4). `set` 을 그대로 list 로 만들지 마라

    TODO(Stage 2):
        1. 각 단어가 **몇 개 문서에** 나타나는지 센다 (문서 빈도, DF)
           ⚠ 총 등장 횟수가 아니다. 한 문서에 10번 나와도 DF 는 1이다
        2. `min_df` 이상인 단어만 남긴다
        3. **정렬해서** 반환한다
    """
    raise NotImplementedError("Stage 2 — build_vocabulary 를 구현하십시오")


# ══════════════════════════════════════════════════════════════════════════
#  ② TF-IDF
# ══════════════════════════════════════════════════════════════════════════

def compute_tf(token_lists: list[list[str]], vocab: list[str]) -> np.ndarray:
    """단어 빈도(Term Frequency) 행렬.

    Returns:
        `(문서 수, 어휘 수)` 배열.
        ⚠ **행이 문서, 열이 단어다.** 이 방향을 헷갈리면 뒤 계산이 전부 틀린다

    ⚠ 정규화를 할 것인가: 긴 문서는 모든 단어의 빈도가 높다. 그대로 두면 긴 문서가 유리해진다.
      문서 길이로 나눌지 결정하고 **주석에 이유를 적어라.**
      (BM25 는 이 문제를 더 정교하게 다룬다 — Stage 4)

    TODO(Stage 2):
        1. 어휘를 `{단어: 열 인덱스}` 로 만든다 (매번 `vocab.index()` 를 부르면 느리다)
        2. `np.zeros((n_docs, n_vocab))` 를 만들고 세어 채운다
        3. 정규화 여부를 결정하고 적용한다
    """
    raise NotImplementedError("Stage 2 — compute_tf 를 구현하십시오")


def compute_idf(token_lists: list[list[str]], vocab: list[str]) -> np.ndarray:
    """역문서빈도(Inverse Document Frequency).

    Returns:
        `(어휘 수,)` 배열

    ⚠⚠ **IDF 가 무엇을 보정하는가** — 이 질문에 답할 수 있어야 이 단계가 닫힌다.
      "요금"은 거의 모든 문서에 있다. 그런 단어가 일치했다는 것은 정보가 거의 없다.
      반대로 "청약철회"가 일치했다면 그건 강한 신호다. **IDF 는 그 차이를 값으로 만든다.**

    ⚠ 분모가 0 이 될 수 있다(어휘에 있는데 DF 가 0 인 경우는 없지만, 방어적으로).
      그리고 **모든 문서에 나오는 단어**의 IDF 가 0 이 되면 그 단어는 점수에 기여하지 못한다.
      그게 의도인지 아닌지 결정하고 주석에 적어라 — 흔히 `log(N/df) + 1` 로 완화한다.

    TODO(Stage 2):
        1. 단어별 문서 빈도 df 를 센다
        2. `log(전체 문서 수 / df)` 형태로 계산한다. 스무딩 여부를 결정한다
        3. ⚠ `np.log` 에 0 이 들어가지 않게 하라
    """
    raise NotImplementedError("Stage 2 — compute_idf 를 구현하십시오")


class TfidfVectorizer:
    """TF-IDF 벡터라이저. `fit` 으로 어휘·IDF 를 배우고 `transform` 으로 벡터를 만든다.

    ⚠⚠ **fit 은 문서 집합에서, transform 은 질의에도 쓴다.**
      질의를 `fit` 에 넣으면 안 된다 — 질의의 단어가 어휘에 섞이고 IDF 가 오염된다.
      지도학습의 데이터 누수와 같은 형태다(§5-E').
    """

    def __init__(self, *, min_df: int = 1) -> None:
        self.min_df = min_df
        self.vocab: list[str] = []
        self.idf: np.ndarray | None = None

    def fit(self, texts: list[str]) -> "TfidfVectorizer":
        """문서 집합에서 어휘와 IDF 를 배운다.

        TODO(Stage 2):
            1. 각 텍스트를 `tokenize`
            2. `build_vocabulary` 로 `self.vocab`
            3. `compute_idf` 로 `self.idf`
            4. `self` 를 반환 (메서드 체이닝)
        """
        raise NotImplementedError("Stage 2 — TfidfVectorizer.fit 을 구현하십시오")

    def transform(self, texts: list[str]) -> np.ndarray:
        """텍스트를 TF-IDF 벡터로 바꾼다.

        Returns:
            `(텍스트 수, 어휘 수)` 배열

        Raises:
            RuntimeError: `fit` 하기 전에 부른 경우

        ⚠ 어휘에 없는 단어는 **조용히 버려진다.** 질의가 전부 미등록 단어면
          0 벡터가 나오고, 그 상태로 코사인을 계산하면 0/0 이다.
          → Stage 3 에서 그 경우를 어떻게 다룰지 결정해야 한다

        TODO(Stage 2):
            1. `fit` 여부를 확인하고 아니면 RuntimeError
            2. TF 를 구하고 IDF 를 곱한다 (브로드캐스팅 방향에 주의)
            3. ⚠ `(n, v) * (v,)` 가 의도한 대로 열 방향으로 곱해지는지 **직접 찍어 확인**할 것
        """
        raise NotImplementedError("Stage 2 — TfidfVectorizer.transform 을 구현하십시오")

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        """편의 함수. ⚠ **질의에는 쓰지 마라** — 위의 누수 주의 참고."""
        return self.fit(texts).transform(texts)
