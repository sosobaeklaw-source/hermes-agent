#!/usr/bin/env python3
"""
preflight.py — atom 작성 전 사전 검증 + 다음 id 사전 등록

실행:
  python3 scripts/preflight.py reserve <category>
  python3 scripts/preflight.py list
  python3 scripts/preflight.py check <atom-id>

지원 카테고리: P F PR I D R O L CIT A

목적: atom-id 작명 drift 영구 방지. 작성 전에 다음 id를 등록하고, 슬러그를
사전에 확정한 뒤에야 본문을 작성하도록 강제.
"""
import os, re, sys, glob, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATOM_DIRS = {
    "P":   "01_atomized/parties",
    "F":   "01_atomized/facts",
    "PR":  "01_atomized/procedure",
    "I":   "01_atomized/issues",
    "D":   "01_atomized/doctrines",
    "R":   "01_atomized/reasoning",
    "O":   "01_atomized/outcomes",
    "L":   "01_atomized/laws",
    "CIT": "01_atomized/citations",
    "A":   "01_atomized/actors",
}
ID_RE = re.compile(r"^([A-Z]+)-(\d{3})-([a-z0-9-]+)$")

def list_atoms():
    by_cat = {}
    for cat, d in ATOM_DIRS.items():
        path = os.path.join(ROOT, d)
        files = sorted(glob.glob(path+"/*.md"))
        ids = []
        for f in files:
            bn = os.path.splitext(os.path.basename(f))[0]
            m = ID_RE.match(bn)
            if m: ids.append((int(m.group(2)), bn))
        by_cat[cat] = sorted(ids)
    return by_cat

def next_id(cat):
    if cat not in ATOM_DIRS:
        return None, f"unknown category: {cat} (allowed: {list(ATOM_DIRS)})"
    used = [n for n,_ in list_atoms().get(cat, [])]
    n = (max(used)+1) if used else 1
    return f"{cat}-{n:03d}-<slug>", None

def check_id(atom_id):
    m = ID_RE.match(atom_id)
    if not m: return False, "format invalid: must be <CAT>-NNN-<slug>"
    cat = m.group(1)
    if cat not in ATOM_DIRS: return False, f"unknown category: {cat}"
    # check duplicate
    path = os.path.join(ROOT, ATOM_DIRS[cat], atom_id+".md")
    if os.path.exists(path): return False, f"already exists: {path}"
    # check number gap
    used = [n for n,_ in list_atoms().get(cat, [])]
    n = int(m.group(2))
    if used and n != max(used)+1 and n not in used:
        return True, f"warning: number {n:03d} skips ahead of next sequential {max(used)+1:03d}"
    return True, "OK"

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        for cat, ids in list_atoms().items():
            print(f"[{cat}] {len(ids)} atoms")
            for n, aid in ids: print(f"  {aid}")
    elif cmd == "reserve":
        if len(sys.argv) < 3:
            print("usage: preflight.py reserve <CATEGORY>"); sys.exit(1)
        cat = sys.argv[2].upper()
        nid, err = next_id(cat)
        if err: print(f"ERROR: {err}"); sys.exit(1)
        print(f"NEXT ID: {nid}")
        print(f"DIR:     {ATOM_DIRS[cat]}/")
        print(f"\n원자 작성 전에 위 id의 slug를 확정한 뒤")
        print(f"  cp _TEMPLATES/atom.md.tpl {ATOM_DIRS[cat]}/{nid}.md")
        print(f"로 시작하라. 작성 후 반드시 verify.py로 적분 검사할 것.")
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("usage: preflight.py check <atom-id>"); sys.exit(1)
        ok, msg = check_id(sys.argv[2])
        print(("OK" if ok else "FAIL") + ": " + msg)
        sys.exit(0 if ok else 1)
    else:
        print(__doc__); sys.exit(1)

if __name__ == "__main__":
    main()
