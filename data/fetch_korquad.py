"""KorQuAD 1.0 내려받기 — Stage 10 (합성 → 실데이터 이식) 용.

⚠⚠ 라이선스: CC BY-ND 2.0 KR — **재배포·파생 금지**
    받은 파일은 `data/external/` 에 저장되고 `.gitignore` 로 추적에서 제외된다.
    ⛔ 저장소에 커밋하면 라이선스 위반이다. `.gitignore` 의 `data/external/` 줄을 지우지 마라.
    (CLAUDE.md §6 지뢰 7 · data/DATA_CARD.md §2)

⚠ 왜 저장소에 안 넣고 스크립트로 받는가
    ND(No Derivatives)는 파생물 배포를 금지한다. 원본을 그대로 재배포하는 것도
    「배포」에 해당하므로, 저장소는 **받는 방법만** 제공한다.
    이 파일 자체는 우리가 쓴 코드이므로 커밋해도 된다.

실행:
    .venv/Scripts/python.exe data/fetch_korquad.py

⚠ 표준 라이브러리만 쓴다(`urllib`). requests 는 이 venv 에 없다 (CLAUDE.md §2).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "external" / "korquad"

# KorQuAD 1.0 공식 배포 파일. SQuAD 와 같은 JSON 스키마다.
FILES = {
    "KorQuAD_v1.0_train.json": "https://korquad.github.io/dataset/KorQuAD_v1.0_train.json",
    "KorQuAD_v1.0_dev.json": "https://korquad.github.io/dataset/KorQuAD_v1.0_dev.json",
}

LICENSE_NOTE = """KorQuAD 1.0
출처: https://korquad.github.io/
라이선스: CC BY-ND 2.0 KR (https://creativecommons.org/licenses/by-nd/2.0/kr/)

⚠⚠ ND = No Derivatives. 재배포·파생물 배포가 금지됩니다.
   이 디렉터리의 파일을 git 에 커밋하지 마십시오.
   가공한 청크·인덱스도 파생물이므로 커밋 대상이 아닙니다.
"""


def download(url: str, dest: pathlib.Path) -> bool:
    """한 파일을 받는다. 이미 있으면 건너뛴다.

    ⚠ 진행률을 찍는 이유: train 파일이 약 38MB 라 조용히 멈춘 것처럼 보인다.
    """
    if dest.exists():
        print(f"  이미 있음 (건너뜀): {dest.name}  {dest.stat().st_size / 1e6:.1f}MB")
        return True

    print(f"  받는 중: {dest.name}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rag-ontology-lab/0.1"})
        with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            got = 0
            while chunk := resp.read(1 << 16):
                f.write(chunk)
                got += len(chunk)
                if total:
                    pct = got * 100 // total
                    print(f"\r    {pct:3d}%  {got / 1e6:.1f}/{total / 1e6:.1f}MB", end="")
        print()
        tmp.replace(dest)
        return True
    except urllib.error.URLError as e:
        print(f"\n  ⛔ 실패: {e}")
        print("     · 인터넷 연결을 확인하십시오")
        print("     · 배포 URL 이 바뀌었을 수 있습니다 → https://korquad.github.io/ 에서 확인")
        tmp.unlink(missing_ok=True)
        return False


def summarize(path: pathlib.Path) -> None:
    """받은 파일의 실제 규모를 찍는다.

    ⚠ 「1,560건이라더라」가 아니라 **실제로 세서** 보고한다 (CLAUDE.md §4 진실의 원천).
    """
    data = json.loads(path.read_text(encoding="utf-8"))["data"]
    n_doc = len(data)
    n_par = sum(len(d["paragraphs"]) for d in data)
    n_qa = sum(len(p["qas"]) for d in data for p in d["paragraphs"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    print(f"  ✅ {path.name}")
    print(f"     문서 {n_doc:,} · 문단 {n_par:,} · QA쌍 {n_qa:,} · sha256 {digest}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LICENSE_NOTICE.txt").write_text(LICENSE_NOTE, encoding="utf-8")

    print("KorQuAD 1.0 내려받기")
    print("⚠⚠ CC BY-ND 2.0 KR — 재배포 금지. data/external/ 은 .gitignore 에 있습니다.\n")

    ok = True
    for name, url in FILES.items():
        ok = download(url, OUT / name) and ok

    if not ok:
        print("\n⛔ 일부 파일을 받지 못했습니다. Stage 10 은 이 데이터가 있어야 진행됩니다.")
        return 1

    print("\n실측 규모:")
    for name in FILES:
        summarize(OUT / name)

    print(f"\n저장 위치: {OUT}")
    print("⚠ 이 디렉터리를 git 에 추가하지 마십시오.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
