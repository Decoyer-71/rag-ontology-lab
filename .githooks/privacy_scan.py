"""개인정보·비밀값 관문 — 공개 저장소로 올라가기 **전에** 막는다. (CLAUDE.md §15-5)

⚠⚠ 왜 필요한가
  이 저장소는 공개이고, 커밋하면 곧바로 원격으로 올라간다(post-commit 자동 푸시).
  한 번 올라간 커밋은 이력 재작성 + 강제 푸시 없이는 지워지지 않고, 그래도 사본이 남는다.
  그래서 사후 경고가 아니라 **올라가기 전 차단**이다.

무엇을 막고 무엇을 안 막는가 — 사용자 결정 (2026-09-11)
  막는다    계좌·카드·휴대전화·주민등록번호 형식 · 비밀번호 대입·URL 속 자격증명 · API 키·토큰·개인키 ·
            계정명이 든 경로 · **남의** 이메일 · 로컬 금지어
  안 막는다 **내 커밋 이메일**(git config user.email) — 커밋 신원으로도, 본문에 있어도.
            이미 공개 이력 전부에 있고, 사용자가 「계좌·전화·비밀번호와 달리 노출돼도 되는 값」으로 판단했다.

검사 지점 (.githooks/ 의 git 훅이 부른다)
  pre-commit  → staged   스테이징된 추가 줄과 새 경로
  commit-msg  → message  커밋 메시지
  pre-push    → push     올라갈 커밋 전부의 추가 줄·메시지 — 두 번째 방어선
  수동        → tree     추적 중인 파일 전체 감사 (`tree --all` — 아직 추적 안 된 새 파일까지. 커밋 전 점검용)
  수동        → selftest 규칙 단위 시험

⚠ 규칙은 「무엇이 개인정보인가」의 근사다. 놓치는 것도, 오탐도 있다.
  오탐은 `.githooks/privacy-allow.txt` 에 그 문자열을 적어 푼다 — 커밋되므로 리뷰에 보인다.
  PC 고유 금지어(실명·전화 등)는 `.git/info/privacy-denylist` 에 적는다 — 커밋되지 않는다.

⚠⚠ fail-closed — 검사기가 죽으면 **막는다.** 통과시키는 오류는 공개 사고가 된다.

⚠⚠ 이 파일에 실제 개인정보를 적지 마라. 시험용 가짜 값도 **실행 중에 조립**한다 —
  글자 그대로 적으면 이 파일을 커밋하는 순간 스스로에게 걸린다.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOW_FILE = HERE / "privacy-allow.txt"
ZERO_SHA = "0" * 40
MAX_SHOWN = 40

# RFC 2606 · RFC 6761 예약 도메인 — 실재하는 사람의 주소일 수 없어 시험·예시용으로 허용한다
RESERVED_TLDS = {"example", "invalid", "test", "localhost"}
RESERVED_DOMAINS = {"example.com", "example.net", "example.org"}
ALLOW_EMAILS = {"noreply@anthropic.com", "git@github.com"}
NOREPLY_SUFFIX = "@users.noreply.github.com"
# `logo@2x.png` 같은 파일명이 이메일로 읽히는 오탐을 막는다
FILE_EXT_TLDS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "pdf", "py", "md",
    "json", "yaml", "yml", "txt", "csv", "html", "css", "js", "ts", "ps1",
}
# 계정명이 흔한 단어면 본문 전체가 오탐이 된다 — 그런 이름은 계정명 규칙에서 뺀다
COMMON_NAMES = {"user", "users", "admin", "administrator", "owner", "guest", "home", "pc", "dev", "test"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


@dataclass(frozen=True)
class Rule:
    rid: str
    desc: str
    pattern: re.Pattern[str]
    # 형식만으로는 오탐이 많은 규칙은 한 번 더 거른다 (True = 진짜로 본다)
    check: Callable[[str], bool] | None = None


@dataclass(frozen=True)
class Finding:
    where: str
    rid: str
    desc: str
    token: str


# ── 형식 검증 ────────────────────────────────────────────────────────────────

def luhn_ok(num: str) -> bool:
    """카드번호 체크섬(Luhn). 무작위 숫자열의 약 90%를 걸러 오탐을 줄인다."""
    total = 0
    for i, ch in enumerate(reversed(num)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def is_card(tok: str) -> bool:
    digits = re.sub(r"\D", "", tok)
    return 15 <= len(digits) <= 16 and digits[0] in "3456" and luhn_ok(digits)


def is_account(tok: str) -> bool:
    """한국 계좌번호는 은행마다 자릿수·묶음이 달라 형식 하나로 못 잡는다 — 넓게 잡고 흔한 오탐을 뺀다."""
    groups = tok.split("-")
    if not 10 <= sum(len(g) for g in groups) <= 14:
        return False
    # 2026-09-11-0930 같은 날짜·시각
    return not (re.fullmatch(r"(?:19|20)\d\d", groups[0]) and re.fullmatch(r"0[1-9]|1[0-2]", groups[1]))


STATIC_RULES: tuple[Rule, ...] = (
    Rule("github-token", "GitHub 토큰",
         re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})")),
    Rule("anthropic-key", "Anthropic API 키", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    Rule("openai-key", "OpenAI API 키", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{32,}")),
    Rule("hf-token", "Hugging Face 토큰", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    Rule("aws-key", "AWS 액세스 키", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Rule("google-key", "Google API 키", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    Rule("slack-token", "Slack 토큰", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    Rule("private-key", "개인키 블록", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    # 값이 자리표시자(<…> · ${…} · *** · 환경변수 읽기)면 통과한다. 한글 설명문은 값으로 치지 않는다(ASCII 만)
    Rule("password", "비밀번호 대입",
         re.compile(r"(?i)(?:\b(?:password|passwd|passphrase|pwd)|비밀번호|비번|암호)\s*[:=]\s*['\"]?"
                    r"(?!(?:os\.environ|os\.getenv|getenv|input\(|none\b|null\b|true\b|false\b|password\b|passwd\b)"
                    r"|[<{$%*(\[])[\x21-\x7e]{4,}")),
    Rule("url-credential", "URL 에 든 아이디·비밀번호",
         re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:@'\"<>]+:[^\s/@'\"<>]+@")),
    # 하이픈 없는 13자리는 잡지 않는다 — 밀리초 타임스탬프가 전부 오탐이 된다
    Rule("kr-rrn", "주민등록번호 형식",
         re.compile(r"(?<!\d)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])-[1-8]\d{6}(?!\d)")),
    Rule("kr-mobile", "휴대전화 번호 형식", re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    # 0 으로 시작하는 묶음(전화·지역번호)은 계좌로 보지 않는다 — 전화는 위 규칙이 따로 본다
    Rule("bank-account", "계좌번호 형식",
         re.compile(r"(?<![\d-])[1-9]\d{1,5}(?:-\d{2,7}){2,3}(?![\d-])"), is_account),
    Rule("card-number", "카드번호 형식(체크섬 통과)",
         re.compile(r"(?<![\d-])(?:\d{4}[- ]){3}\d{4}(?![\d-])|(?<![\d-])\d{15,16}(?![\d-])"), is_card),
    # `C:\Users\<사용자>` · `%USERPROFILE%` 같은 자리표시자는 통과한다.
    # ⚠ 개인정보만의 문제가 아니다 — 이 경로는 **다른 PC 에서 깨진다**(루트가 PC 마다 다르다, §2)
    Rule("user-path", "사용자 폴더 경로 — 계정명이 드러나고 다른 PC 에서 깨진다",
         re.compile(r"\b[A-Za-z]:[\\/]+Users[\\/]+(?![<%$({]|(?:Public|Default|All Users|USERNAME)\b)"
                    r"[^\\/\s\"'<>`|]+")),
    Rule("user-path-posix", "사용자 폴더 경로 — 계정명이 드러나고 다른 PC 에서 깨진다",
         re.compile(r"(?<![A-Za-z0-9])/[a-z]/Users/(?![<%$({])[^/\s\"'<>`|]+")),
)


# ── git ──────────────────────────────────────────────────────────────────────

def git_run(*args: str) -> tuple[int, str]:
    """git 을 부르고 (종료코드, 표준출력)을 돌려준다. 한글 경로가 8진수로 깨지지 않게 quotePath 를 끈다."""
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", errors="replace")


def git_out(*args: str) -> str:
    return git_run(*args)[1]


# ── 규칙 ─────────────────────────────────────────────────────────────────────

def email_allowed(addr: str) -> bool:
    """누구의 주소도 아닌 것 — noreply · 예약 도메인 · 파일명 오탐."""
    a = addr.strip().lower()
    if a in ALLOW_EMAILS or a.endswith(NOREPLY_SUFFIX):
        return True
    domain = a.rsplit("@", 1)[-1]
    tld = domain.rsplit(".", 1)[-1]
    if tld in RESERVED_TLDS or tld in FILE_EXT_TLDS:
        return True
    return any(domain == d or domain.endswith("." + d) for d in RESERVED_DOMAINS)


def _word(term: str) -> re.Pattern[str]:
    """영숫자 경계로 감싼 대소문자 무시 패턴. `cvcv` 가 `cvcvx` 안에서 잡히는 오탐을 막는다."""
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return [s.strip() for s in text.splitlines() if s.strip() and not s.lstrip().startswith("#")]


def read_allow() -> set[str]:
    return set(read_lines(ALLOW_FILE))


def read_denylist() -> list[str]:
    rel = git_out("rev-parse", "--git-path", "info/privacy-denylist").strip()
    return read_lines(Path(rel)) if rel else []


def dynamic_rules() -> list[Rule]:
    """이 PC 에서만 아는 값으로 규칙을 만든다 — 계정명 · 로컬 금지어.

    ⚠ 이 값들은 **실행 중에만** 존재한다. 파일에 적으면 그 자체로 공개된다.
    """
    rules: list[Rule] = []
    name = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if len(name) >= 3 and name.lower() not in COMMON_NAMES:
        rules.append(Rule("local-account", "이 PC 의 계정명", _word(name)))
    for term in read_denylist():
        rules.append(Rule("denylist", "금지어(.git/info/privacy-denylist)", re.compile(re.escape(term), re.IGNORECASE)))
    return rules


def load_rules() -> tuple[list[Rule], set[str]]:
    """규칙과 허용 목록. ⭐ 내 커밋 이메일은 실행 중에 허용 목록에 넣는다 — 사용자 결정(2026-09-11)."""
    allow = read_allow()
    own = git_out("config", "user.email").strip()
    if own:
        allow.add(own.lower())
    return [*STATIC_RULES, *dynamic_rules()], allow


# ── 검사 ─────────────────────────────────────────────────────────────────────

def scan_text(where: str, text: str, rules: list[Rule], allow: set[str]) -> list[Finding]:
    found: list[Finding] = []
    for m in EMAIL_RE.finditer(text):
        tok = m.group(0)
        if not email_allowed(tok) and tok not in allow and tok.lower() not in allow:
            found.append(Finding(where, "email", "이메일 주소(내 커밋 이메일 아님)", tok))
    for rule in rules:
        for m in rule.pattern.finditer(text):
            tok = m.group(0)
            if tok in allow or (rule.check and not rule.check(tok)):
                continue
            found.append(Finding(where, rule.rid, rule.desc, tok))
    return found


def scan_diff(diff: str, label: str, rules: list[Rule], allow: set[str]) -> list[Finding]:
    """`--unified=0` diff 에서 **추가된 줄과 새 경로**만 검사한다. 지우는 줄은 공개를 늘리지 않는다."""
    found: list[Finding] = []
    path = "?"
    lineno = 0
    in_header = False
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            in_header = True
            continue
        if in_header:
            if raw.startswith("+++ "):
                p = raw[4:]
                path = p[2:] if p.startswith("b/") else p
                if path != "/dev/null":
                    found += scan_text(f"{label}{path} (경로)", path, rules, allow)
            elif raw.startswith("rename to "):
                found += scan_text(f"{label}{raw[10:]} (경로)", raw[10:], rules, allow)
            m = HUNK_RE.match(raw)
            if m:
                in_header = False
                lineno = int(m.group(1))
            continue
        m = HUNK_RE.match(raw)
        if m:
            lineno = int(m.group(1))
            continue
        if raw.startswith("+"):
            found += scan_text(f"{label}{path}:{lineno}", raw[1:], rules, allow)
            lineno += 1
    return found


def mask(tok: str) -> str:
    """보고에 값을 통째로 찍지 않는다 — 보고 자체가 로그·대화에 남기 때문이다."""
    if len(tok) <= 6:
        return "*" * len(tok)
    return f"{tok[:2]}…{tok[-2:]} ({len(tok)}자)"


def report(found: list[Finding], blocked_what: str) -> int:
    seen: set[tuple[str, str, str]] = set()
    uniq: list[Finding] = []
    for f in found:
        key = (f.where, f.rid, f.token)
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    if not uniq:
        return 0
    err = sys.stderr
    print(f"[privacy] ⛔ 공개 저장소에 올라가면 안 되는 값 {len(uniq)}건 — {blocked_what} (CLAUDE.md §15-5)", file=err)
    for f in uniq[:MAX_SHOWN]:
        print(f"  {f.where}  [{f.rid}] {f.desc}: {mask(f.token)}", file=err)
    if len(uniq) > MAX_SHOWN:
        print(f"  … 외 {len(uniq) - MAX_SHOWN}건", file=err)
    print("  ■ 고치는 법: 값을 지우거나 자리표시자(<사용자> 등)로 바꾼 뒤 다시 시도합니다", file=err)
    print("  ■ 오탐이면: 그 문자열을 .githooks/privacy-allow.txt 에 한 줄로 적습니다 — 커밋되어 리뷰에 보입니다", file=err)
    print("  ⚠ 우회(--no-verify)는 사용자만 판단합니다", file=err)
    return 1


# ── 모드 ─────────────────────────────────────────────────────────────────────

def mode_staged() -> int:
    rules, allow = load_rules()
    diff = git_out("diff", "--cached", "--no-color", "--no-ext-diff", "--unified=0", "--diff-filter=d")
    return report(scan_diff(diff, "", rules, allow), "커밋을 막았습니다")


def mode_message(path: str) -> int:
    rules, allow = load_rules()
    found: list[Finding] = []
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("# ------------------------ >8"):
            break
        if line.startswith("#"):
            continue
        found += scan_text(f"커밋 메시지:{i}", line, rules, allow)
    return report(found, "커밋을 막았습니다")


def mode_push() -> int:
    """pre-push 표준입력(`<로컬 ref> <로컬 sha> <원격 ref> <원격 sha>`)의 범위를 **커밋마다** 검사한다.

    ⚠ 합쳐진 diff 하나로 보면 안 된다 — 중간 커밋이 넣고 다음 커밋이 지운 값도 이력에는 공개된다.
    """
    rules, allow = load_rules()
    found: list[Finding] = []
    for line in sys.stdin.read().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _lref, lsha, _rref, rsha = parts
        if lsha == ZERO_SHA:
            continue  # 원격 브랜치 삭제 — 올라가는 내용이 없다
        known = rsha != ZERO_SHA and git_run("cat-file", "-e", f"{rsha}^{{commit}}")[0] == 0
        rc, revs = git_run("rev-list", f"{rsha}..{lsha}") if known else git_run("rev-list", lsha, "--not", "--remotes")
        if rc != 0:
            return report([Finding("푸시 범위", "range", "검사 범위를 정하지 못했습니다", lsha)], "푸시를 막았습니다")
        for sha in revs.split():
            short = sha[:8]
            for i, msg_line in enumerate(git_out("show", "-s", "--format=%B", sha).splitlines(), 1):
                found += scan_text(f"{short} 메시지:{i}", msg_line, rules, allow)
            diff = git_out("show", "--format=", "--no-color", "--no-ext-diff", "--unified=0",
                           "--diff-merges=first-parent", sha)
            found += scan_diff(diff, f"{short} ", rules, allow)
    return report(found, "푸시를 막았습니다")


def mode_tree(include_untracked: bool = False) -> int:
    rules, allow = load_rules()
    found: list[Finding] = []
    paths = git_out("ls-files", "-z").split("\0")
    if include_untracked:
        paths += git_out("ls-files", "-z", "--others", "--exclude-standard").split("\0")
    for p in paths:
        if not p:
            continue
        found += scan_text(f"{p} (경로)", p, rules, allow)
        try:
            data = Path(p).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue  # 바이너리
        for i, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            found += scan_text(f"{p}:{i}", line, rules, allow)
    rc = report(found, "감사 결과입니다(막은 것은 없음)")
    if rc == 0:
        scope = "추적 중인 파일 + 새 파일" if include_untracked else "추적 중인 파일"
        print(f"[privacy] ✅ {scope} 전체에서 걸린 값 없음")
    return rc


def mode_selftest() -> int:
    """규칙 단위 시험. ⚠ 가짜 값은 전부 **조립**한다 — 이 파일이 스스로에게 걸리지 않도록."""
    at = "@"
    cases: list[tuple[str, str, bool]] = [
        ("이메일(남의 주소)", "연락 " + "some.one" + at + "gmail" + ".com", True),
        ("이메일(GitHub noreply)", "12345+someone" + at + "users.noreply.github.com", False),
        ("이메일(Anthropic noreply)", "Co-Authored-By: Claude <noreply" + at + "anthropic.com>", False),
        ("이메일(예약 도메인)", "a" + at + "example.invalid", False),
        ("파일명 오탐(logo@2x.png)", "logo" + at + "2x.png", False),
        ("파이썬 데코레이터", "    " + at + "pytest.mark.breaks", False),
        ("GitHub 토큰", "token=" + "ghp_" + "A1b2" * 9, True),
        ("Anthropic 키", "sk-ant-" + "x" * 30, True),
        ("Hugging Face 토큰", "hf_" + "Ab3" * 11, True),
        ("AWS 키", "AKIA" + "ABCDEFGHIJKLMNOP", True),
        ("개인키 블록", "-----BEGIN " + "RSA PRIVATE KEY-----", True),
        ("비밀번호 대입", "password=" + "hunter22", True),
        ("비밀번호(한글 키)", "비밀번호: " + "abcd1234", True),
        ("비밀번호 자리표시자는 통과", "비밀번호: " + "<사용자만 입력>", False),
        ("비밀번호 환경변수 읽기는 통과", "password = " + "os.environ['PW']", False),
        ("비밀번호 한글 설명문은 통과", "비밀번호" + "가 노출되는 것과 다르다", False),
        ("URL 속 자격증명", "https://" + "user:s3cret" + at + "db.internal/x", True),
        ("일반 URL 은 통과", "https://" + "github.com/Decoyer-71/rag-ontology-lab", False),
        ("주민번호 형식", "주민번호 " + "900101" + "-" + "1234567", True),
        ("하이픈 없는 13자리는 통과", "ts=" + "1757571234567", False),
        ("휴대전화", "연락처 " + "010" + "-1234-" + "5678", True),
        ("계좌번호", "입금 " + "110" + "-123-" + "456789", True),
        ("계좌번호(4-2-7)", "입금 " + "3333" + "-01-" + "1234567", True),
        ("날짜는 계좌 아님", "2026" + "-09-" + "11", False),
        ("날짜·시각은 계좌 아님", "2026" + "-09-11-" + "0930", False),
        ("지역번호 전화는 계좌 아님", "02" + "-1234-" + "5678", False),
        ("카드번호(체크섬 통과)", "카드 " + "4111" + " 1111" * 3, True),
        ("카드번호(체크섬 불일치)는 통과", "카드 " + "4111" + " 1111" * 2 + " 1112", False),
        ("사용자 경로", "C:" + "\\Users\\" + "someone" + "\\AppData", True),
        ("사용자 경로(JSON 이스케이프)", "C:" + "\\\\Users\\\\" + "someone", True),
        ("사용자 경로(git bash)", "/c/" + "Users/" + "someone/x", True),
        ("자리표시자 경로는 통과", "C:" + "\\Users\\" + "<사용자>" + "\\AppData", False),
        ("환경변수 경로는 통과", "%USERPROFILE%" + "\\.claude", False),
        ("한국어 평문", "한빛텔레콤 LTE-S-33 요금제는 월 33,000원이다", False),
    ]
    ok = 0
    fails: list[str] = []
    for name, text, expect in cases:
        got = bool(scan_text("t", text, list(STATIC_RULES), set()))
        if got == expect:
            ok += 1
        else:
            fails.append(f"  ⛔ {name} — 기대 {'차단' if expect else '통과'} / 실제 {'차단' if got else '통과'}")

    total = len(cases) + 5

    # 계정명 규칙 — 환경변수로 가짜 계정을 세워 본다
    saved = os.environ.get("USERNAME")
    try:
        os.environ["USERNAME"] = "zq" + "xv" + "acct9"
        acct = [r for r in dynamic_rules() if r.rid == "local-account"]
        line = "D:" + "\\work\\" + "zqxvacct9" + "\\notes.md"
        if acct and scan_text("t", line, acct, set()):
            ok += 1
        else:
            fails.append("  ⛔ 계정명 규칙 — 가짜 계정명을 못 잡음")
        if acct and not scan_text("t", "zqxvacct9x", acct, set()):
            ok += 1
        else:
            fails.append("  ⛔ 계정명 규칙 — 더 긴 단어 안의 부분 일치를 잘못 잡음")
    finally:
        if saved is None:
            os.environ.pop("USERNAME", None)
        else:
            os.environ["USERNAME"] = saved

    # ⭐ 내 커밋 이메일은 허용 목록에 있으면 본문에서도 통과 — 사용자 결정(2026-09-11)
    me = "Me.Myself" + at + "gmail" + ".com"
    if not scan_text("t", "연락처 " + me, list(STATIC_RULES), {me.lower()}) \
            and scan_text("t", "연락처 " + me, list(STATIC_RULES), set()):
        ok += 1
    else:
        fails.append("  ⛔ 내 이메일 허용 — 허용 목록에 넣어도 걸리거나, 안 넣어도 풀림")

    # 허용 목록이 정확히 그 문자열만 푸는가
    tok = "010" + "-0000-" + "0000"
    if not scan_text("t", tok, list(STATIC_RULES), {tok}) and scan_text("t", tok, list(STATIC_RULES), set()):
        ok += 1
    else:
        fails.append("  ⛔ 허용 목록 — 적은 문자열을 못 풀었거나, 안 적어도 풀림")

    # 보고가 값을 통째로 찍지 않는가
    secret = "ghp_" + "Z9y8" * 9
    if secret not in mask(secret):
        ok += 1
    else:
        fails.append("  ⛔ 가림 — 보고에 원문이 그대로 찍힘")

    print(f"[privacy-selftest] {ok}/{total} 통과")
    for f in fails:
        print(f)
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "staged":
        return mode_staged()
    if cmd == "message" and rest:
        return mode_message(rest[0])
    if cmd == "push":
        return mode_push()
    if cmd == "tree":
        return mode_tree("--all" in rest)
    if cmd == "selftest":
        return mode_selftest()
    print(f"[privacy] 알 수 없는 명령: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # ⚠⚠ fail-closed — 검사기가 죽으면 막는다
        print(f"[privacy] ⛔ 검사기 오류로 막았습니다: {exc!r}", file=sys.stderr)
        sys.exit(1)
