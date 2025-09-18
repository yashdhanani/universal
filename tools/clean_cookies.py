#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


def is_comment_or_blank(line: str) -> bool:
    s = line.strip()
    return not s or s.startswith("#")


def parse_fields(line: str):
    # Netscape format is 7 TAB-separated fields
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 7:
        return None
    # Keep first 6 as-is; join the rest back for value (in case of stray tabs)
    domain, include_subdomains, path, secure, expiration, name = parts[:6]
    value = "\t".join(parts[6:])
    return [domain, include_subdomains, path, secure, expiration, name, value]


def valid_bool(s: str) -> bool:
    return s in ("TRUE", "FALSE")


def try_int(s: str):
    try:
        int(s)
        return True
    except Exception:
        return False


def fix_or_remove(fields, mode="remove"):
    domain, include_subdomains, path, secure, expiration, name, value = fields

    problems = []

    # 1) include_subdomains must be TRUE/FALSE
    if not valid_bool(include_subdomains):
        problems.append(("include_subdomains", include_subdomains))

    # 2) secure must be TRUE/FALSE
    if not valid_bool(secure):
        problems.append(("secure", secure))

    # 3) expiration must be an integer
    if not try_int(expiration):
        problems.append(("expiration", expiration))

    # 4) Domain starts with '.' → include_subdomains should be TRUE
    if domain.startswith(".") and include_subdomains == "FALSE":
        problems.append(("dot_domain_FALSE", include_subdomains))

    if not problems:
        return fields, True  # already valid

    if mode == "fix":
        # Attempt safe corrections
        if not valid_bool(include_subdomains):
            include_subdomains = "FALSE"
        if not valid_bool(secure):
            secure = "FALSE"
        if not try_int(expiration):
            expiration = "0"
        if domain.startswith(".") and include_subdomains == "FALSE":
            include_subdomains = "TRUE"

        return [domain, include_subdomains, path, secure, expiration, name, value], True

    # mode == "remove" → drop the line
    return None, False


def main():
    ap = argparse.ArgumentParser(description="Clean/fix Netscape cookies.txt for yt-dlp")
    ap.add_argument("input", nargs="?", default=r"e:\\project\\downloader\\cookies.txt", help="Path to cookies.txt")
    ap.add_argument("--output", "-o", help="Write cleaned file to this path (default: overwrite input)")
    ap.add_argument("--mode", choices=["remove", "fix"], default="remove", help="Remove invalid lines (default) or try to fix them")
    ap.add_argument("--dry-run", action="store_true", help="Print summary without writing changes")
    ap.add_argument("--backup", action="store_true", help="Create .bak backup of input before overwriting")
    args = ap.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"Input not found: {inp}")
        return 1

    outp = Path(args.output) if args.output else inp

    lines = inp.read_text(encoding="utf-8", errors="ignore").splitlines(True)

    kept = []
    removed = 0
    fixed = 0

    for line in lines:
        if is_comment_or_blank(line):
            kept.append(line)
            continue
        fields = parse_fields(line)
        if not fields:
            # Malformed → drop or keep based on mode
            if args.mode == "fix":
                # Can't reliably fix without 7 fields → drop
                removed += 1
            else:
                removed += 1
            continue

        new_fields, ok = fix_or_remove(fields, mode=args.mode)
        if not ok and new_fields is None:
            removed += 1
            continue

        if new_fields != fields:
            fixed += 1

        kept.append("\t".join(new_fields) + "\n")

    if args.dry_run:
        print(f"Checked: {len(lines)} lines")
        print(f"Kept:    {len(kept)}")
        print(f"Fixed:   {fixed} (mode={args.mode})")
        print(f"Removed: {removed}")
        return 0

    if outp == inp and args.backup:
        shutil.copy2(inp, inp.with_suffix(inp.suffix + ".bak"))

    outp.write_text("".join(kept), encoding="utf-8")
    print(f"Wrote {outp} (fixed={fixed}, removed={removed}, mode={args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())