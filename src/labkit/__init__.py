"""labkit — 제공 도구 (배관).

⚠ 여기 있는 코드는 **학습 대상이 아니다.** 사용자가 손으로 짜야 하는 것은 `raglab` 이다.
  (CLAUDE.md §5-T)

  corpus  : 코퍼스 로더 (문서·트리플·개념·골든셋)
  inspect : 중간 결과를 눈으로 보는 도구. ⚠ 블랙박스 한 방 호출 금지 (§7-4)
  report  : HTML 산출물 빌더. ⚠ 직접 HTML 을 조립하지 마라 (§8)
  results : 측정 결과 저장·비교. ⚠ 기준선 없이 저장되지 않는다 (§5-D')
  review  : 복습 카드 스케줄러 (§14). ⚠⚠ 간격 파라미터는 근거 없는 임의값이다
"""

__all__ = ["corpus", "inspect", "report", "results", "review"]
