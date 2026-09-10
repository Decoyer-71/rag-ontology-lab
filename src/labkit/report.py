"""HTML 산출물 빌더 — 학습 대상이 아닌 배관이다. (CLAUDE.md §8)

⚠⚠ 직접 HTML 문자열을 조립하지 마라. 규격이 어긋나고 `guard_claim` 훅에 막힌다.

규격 (§8):
    자기완결   — CSS·그림 전부 파일 안에. 외부 CDN·폰트 요청 금지
    테마       — 밝음/어두움 양쪽 (prefers-color-scheme)
    반응형     — 넓은 표는 자기 컨테이너 안에서 가로 스크롤. 본문은 가로 스크롤 금지
    한국어     — 본문 존댓말. 전문용어는 첫 등장 시 괄호로 원어
    근거 등급  — ✅측정 / ⚠파생 / ⚠⚠추론 / ⚠2차 + 상단 범례
    ⚠⚠ 합성 표기 — synthetic=True 면 최상단 배너
    ⚠⚠ 「한계」 절 — 없으면 빌드 자체가 실패한다

⚠ 마지막 두 항목은 **선택이 아니다.** 합성 수치가 실세계 성능으로 읽히거나
  한계를 모른 채 인용되면 그 문서는 틀린 것보다 나쁘다 (§3-S · §13-5).
"""
from __future__ import annotations

import html
import pathlib
from dataclasses import dataclass
from typing import Sequence

# ── 근거 등급 (CLAUDE.md §4) ────────────────────────────────────────────────
GRADES = {
    "measured": ("✅측정", "이 PC 에서 실제로 돌려 나온 값"),
    "derived": ("⚠파생", "측정값에 연산을 가한 것"),
    "inferred": ("⚠⚠추론", "측정하지 않고 근거로 미룬 것"),
    "secondary": ("⚠2차", "남의 문서·논문·블로그가 출처"),
}

_CSS = """
:root{
  --bg:#fbfbfa; --fg:#1f2328; --muted:#5c6370; --line:#e3e5e8;
  --card:#ffffff; --accent:#2f6f4f; --warn:#8a5a00; --danger:#a33;
  --code-bg:#f4f5f6;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#15171a; --fg:#e6e8ea; --muted:#9aa1a9; --line:#2b2f35;
    --card:#1c1f23; --accent:#6fbf95; --warn:#d9a441; --danger:#e07a7a;
    --code-bg:#212529;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",
  "Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  overflow-x:hidden;}
.wrap{max-width:860px;margin:0 auto;padding:0 20px 80px}
h1{font-size:1.9rem;line-height:1.35;margin:0 0 .3em}
h2{font-size:1.35rem;margin:2.4em 0 .6em;padding-bottom:.3em;border-bottom:1px solid var(--line)}
h3{font-size:1.08rem;margin:1.8em 0 .5em}
p,li{overflow-wrap:break-word}
.sub{color:var(--muted);margin:0 0 2em}
.banner{border-radius:8px;padding:14px 18px;margin:20px 0;
  border:1px solid var(--warn);background:color-mix(in srgb,var(--warn) 12%,transparent);}
.banner b{color:var(--warn)}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 28px;padding:0;list-style:none}
.legend li{font-size:.82rem;color:var(--muted);border:1px solid var(--line);
  border-radius:99px;padding:3px 12px;background:var(--card)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:1em 0}
table{border-collapse:collapse;width:100%;min-width:440px;font-size:.92rem}
th,td{border:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
th{background:var(--card);font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums}
code,pre{background:var(--code-bg);border-radius:5px;font-size:.88em;
  font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
code{padding:1px 5px}
pre{padding:14px 16px;overflow-x:auto}
figure{margin:1.6em 0}
figure svg{max-width:100%;height:auto;display:block}
figcaption{color:var(--muted);font-size:.85rem;margin-top:.6em}
.limit{border-left:3px solid var(--danger);padding:2px 0 2px 18px;margin:1.2em 0}
footer{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--muted);font-size:.85rem}
"""


@dataclass
class Section:
    """리포트 한 절.

    Args:
        title: 절 제목
        body_html: 이미 HTML 인 본문 (표·그림 포함). 이스케이프하지 않는다
    """

    title: str
    body_html: str


def esc(s: object) -> str:
    return html.escape(str(s))


def table(headers: Sequence[str], rows: Sequence[Sequence[object]],
          numeric_cols: Sequence[int] = ()) -> str:
    """표를 만든다. ⚠ 넓은 표는 자기 컨테이너 안에서 가로 스크롤한다 (§8 반응형).

    ⚠⚠ 모든 비율에 분모를 붙여라 (§4). 이 함수는 그걸 검사하지 못한다 — 쓰는 쪽 책임이다.
    """
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = "".join(
            f'<td class="num">{esc(c)}</td>' if i in numeric_cols else f"<td>{esc(c)}</td>"
            for i, c in enumerate(r)
        )
        trs.append(f"<tr>{tds}</tr>")
    return (f'<div class="scroll"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def figure(svg: str, caption: str) -> str:
    """인라인 SVG 그림. ⚠ 외부 이미지 파일을 쓰지 마라 (§8 오프라인).

    ⚠ 색을 하드코딩하면 어두운 테마에서 안 보인다. `currentColor` 를 쓴다.
    """
    return f"<figure>{svg}<figcaption>{esc(caption)}</figcaption></figure>"


def grade(kind: str, text: str) -> str:
    """근거 등급을 붙인 문장 (§4)."""
    mark, _ = GRADES.get(kind, ("⚠⚠추론", ""))
    return f"<p><code>{mark}</code> {esc(text)}</p>"


def build_report(
    *,
    out_path: pathlib.Path | str,
    title: str,
    subtitle: str,
    sections: Sequence[Section],
    limitations: Sequence[str],
    reproduce: str,
    synthetic: bool = True,
) -> pathlib.Path:
    """자기완결 HTML 리포트 하나를 만든다.

    Args:
        sections: 본문 절들. §8 구조 ①~⑤ 를 담는다
        limitations: ⚠⚠ 「한계와 오용 경고」(§8 구조 ⑥). **빈 목록이면 예외를 던진다**
        reproduce: 재현 방법(§8 구조 ⑦). 실제로 도는 명령을 적는다
        synthetic: 합성 데이터를 썼는가. True 면 최상단 배너 (§3-S)

    Raises:
        ValueError: limitations 가 비었을 때.
            ⚠ 「한계」 절이 없는 문서는 위험하다. 빌드를 막는 것이 맞다 (§8 구조 ⑥).

    Returns:
        쓴 파일 경로
    """
    if not limitations:
        raise ValueError(
            "⛔ 「한계」 절이 비어 있습니다 (CLAUDE.md §8 구조 ⑥).\n"
            "   이 방법이 언제 틀린 답을 내는지를 적으십시오.\n"
            "   잘 되는 예제만 있는 문서가 가장 해롭습니다 (§10 원칙 3)."
        )

    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    banner = ""
    if synthetic:
        banner = (
            '<div class="banner"><b>⚠ 합성 데이터 기반입니다.</b> '
            "이 문서의 한빛텔레콤·요금제·고객·수치는 전부 교육용 가상 설정이며 "
            "실재하는 회사나 상품이 아닙니다. "
            "여기 실린 어떤 수치도 실세계 RAG 성능으로 읽으면 안 됩니다.</div>"
        )

    legend = "".join(f"<li><code>{m}</code> {esc(d)}</li>" for m, d in GRADES.values())

    body = []
    for s in sections:
        body.append(f"<h2>{esc(s.title)}</h2>\n{s.body_html}")

    lim = "".join(f'<div class="limit">{esc(x)}</div>' for x in limitations)

    doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
<h1>{esc(title)}</h1>
<p class="sub">{esc(subtitle)}</p>
{banner}
<ul class="legend">{legend}</ul>
{"".join(body)}
<h2>한계와 오용 경고</h2>
{lim}
<h2>재현 방법</h2>
<pre><code>{esc(reproduce)}</code></pre>
<footer>
rag-ontology-lab · RAG·온톨로지 학습 실습실 ·
자기완결 HTML (외부 요청 없음) · 근거 등급은 CLAUDE.md §4 를 따릅니다
</footer>
</div>
</body>
</html>
"""
    out.write_text(doc, encoding="utf-8")
    return out
