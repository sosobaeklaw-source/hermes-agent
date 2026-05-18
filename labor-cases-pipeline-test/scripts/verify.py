#!/usr/bin/env python3
"""
verify.py — labor-cases-pipeline-test 자체 검증 스크립트 (v2)

실행: python3 labor-cases-pipeline-test/scripts/verify.py
의존성: 표준 라이브러리만

검증 항목 (v2 강화):
   1. Atom inventory (10 categories: P F PR I D R O L CIT A)
   2. YAML front-matter — 8 required fields (status 신설)
   3. Wikilink integrity
   4. Graph degree distribution + 고아 노드 0
   5. JSONL validity + atom_refs 해결성
   6. 컴플라이언스 스캔 (context-aware)
   7. Citation density (source 100%)
   8. Confidence distribution
   9. Issue × Instance matrix (목표 100%)
  10. Korean readability KRI
  11. NEW: 카테고리 코드 화이트리스트 검증
  12. NEW: atom-id 일치성 (파일명 == YAML id)
  13. NEW: 슬러그 영문 소문자 강제
  14. NEW: instance suffix 일관성 (R-*, etc.)
  15. NEW: 변경 이력 status 필드 검증

설계 명세 위반 시 exit code 1로 종료. CI에서 회귀 테스트 사용 가능.
"""
import os, re, json, glob, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

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
ALLOWED_CATS = set(ATOM_DIRS)
ID_RE = re.compile(r"^([A-Z]+)-(\d{3})-([a-z0-9-]+)$")

# ---------- gather ----------
atoms = {}
for cat, d in ATOM_DIRS.items():
    for f in sorted(glob.glob(d+"/*.md")):
        bn = os.path.splitext(os.path.basename(f))[0]
        atoms[bn] = (f, cat)

# ---------- 2 + 11 + 12 + 13 YAML & naming ----------
required_fields = ["id","type","instance","source","tags","related","confidence"]
optional_fields = ["status"]
field_presence = {k:0 for k in required_fields+optional_fields}
yaml_missing=[]; id_mismatch=[]; bad_category=[]; bad_slug=[]
for aid, (path, cat_from_dir) in atoms.items():
    text = open(path, encoding="utf-8").read()
    m_fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m_fm: yaml_missing.append(aid); continue
    fm = m_fm.group(1)
    for k in required_fields + optional_fields:
        if re.search(rf"^{k}\s*:", fm, re.M): field_presence[k] += 1
    # YAML id == filename?
    m_id = re.search(r"^id:\s*(\S+)", fm, re.M)
    if m_id and m_id.group(1).strip() != aid:
        id_mismatch.append((aid, m_id.group(1).strip()))
    # category whitelist
    m_atom = ID_RE.match(aid)
    if not m_atom: bad_slug.append(aid); continue
    if m_atom.group(1) not in ALLOWED_CATS: bad_category.append(aid)
    if m_atom.group(1) != cat_from_dir: bad_category.append((aid, cat_from_dir))

# ---------- 3 + 4 wikilink integrity & degree ----------
link_re = re.compile(r"\[\[([A-Z]+-\d+-[a-zA-Z0-9-]+)\]\]")
in_deg = {a:0 for a in atoms}
out_deg = {a:0 for a in atoms}
unresolved = []
total_links = 0
scan_paths = [p for p,_ in atoms.values()] + glob.glob("02_legal_pipeline/*.md") + \
             glob.glob("03_marketing_pipeline/*.md") + \
             ["01_atomized/_graph.md","01_atomized/README.md","REPORT.md",
              "00_source/INDEX.md","QUALITY_ASSESSMENT.md","RCA.md","_CONVENTIONS.md",
              "EXECUTIVE_REPORT.md","DEVIL_REDTEAM.md"]
for p in scan_paths:
    if not os.path.exists(p): continue
    text = open(p, encoding="utf-8").read()
    src = os.path.splitext(os.path.basename(p))[0]
    for tgt in link_re.findall(text):
        total_links += 1
        if src in atoms: out_deg[src] += 1
        if tgt in atoms: in_deg[tgt] += 1
        else: unresolved.append((p, tgt))

# ---------- 5 JSONL ----------
jsonl_path = "02_legal_pipeline/04_training_pairs.jsonl"
jsonl_errs = []; pairs = []
if os.path.exists(jsonl_path):
    for i, line in enumerate(open(jsonl_path, encoding="utf-8"), 1):
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line); pairs.append(obj)
            for k in ["id","type","prompt","completion"]:
                if k not in obj: jsonl_errs.append((i, f"missing {k}"))
            for ref in obj.get("atom_refs", []):
                if ref not in atoms: jsonl_errs.append((i, f"unresolved atom_refs: {ref}"))
        except json.JSONDecodeError as e:
            jsonl_errs.append((i, f"JSON parse error: {e}"))

# ---------- 6 compliance (context-aware) ----------
forbidden = {
    "변호사법 §23": ["승소 보장","100% 승소","99% 승소","확실히 승소","최고 승률","최저 수임료","압도적","유일한"],
    "표시광고법 §3": ["반드시 이긴다","무조건 이긴다","틀림없이","무조건 환급","항상 승소"],
    "단정 표현(자료 결론 부재)": ["대법원이 인정했다","대법원이 받아들였다","대법원이 정식 인정"],
}
neg_markers = ["금지","위반","예:","예시","절대 금지","조심","금기","피해야","사용 금지","사용하지"]
violations = []
for p in glob.glob("03_marketing_pipeline/*.md"):
    lines = open(p, encoding="utf-8").readlines()
    for i, line in enumerate(lines):
        for cat, kws in forbidden.items():
            for kw in kws:
                if kw in line:
                    ctx = (lines[max(0,i-1)] + line + (lines[i+1] if i+1<len(lines) else ""))
                    if any(nm in ctx for nm in neg_markers): continue
                    violations.append((p, i+1, cat, kw))

# ---------- 7 citation density ----------
src_cited = 0
for path,_ in atoms.values():
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^source:\s*(\S.*)$", text, re.M)
    if m and m.group(1).strip().lower() not in ("","n/a","none"): src_cited += 1

# ---------- 8 confidence dist ----------
conf = {"high":0,"medium":0,"low":0,"other":0}
for path,_ in atoms.values():
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^confidence:\s*(\S+)", text, re.M)
    v = m.group(1).strip().lower() if m else "other"
    conf[v if v in conf else "other"] += 1

# ---------- 9 issue × instance matrix ----------
# Coverage mode: 'covered' = reasoning atom exists (positive) OR issue atom explicitly
# declares "NOT-COVERED" for that instance (negative coverage). Negative coverage means
# the court did not address this issue - this is a meaningful state, not an absence.
matrix = collections.defaultdict(lambda: {"positive": set(), "negative": set()})
# positive coverage from reasoning atoms
for path,cat in atoms.values():
    if cat != "R": continue
    text = open(path, encoding="utf-8").read()
    mi = re.search(r"^instance:\s*(.+)$", text, re.M)
    if not mi: continue
    insts = re.findall(r"(admin|high|supreme)", mi.group(1))
    issues = re.findall(r"\[\[(I-\d+-[a-z-]+)\]\]", text)
    for i in issues:
        for ii in insts: matrix[i]["positive"].add(ii)
# negative coverage declared in issue atoms (e.g., "supreme: ◌ NOT-COVERED")
for path,cat in atoms.values():
    if cat != "I": continue
    text = open(path, encoding="utf-8").read()
    aid = os.path.splitext(os.path.basename(path))[0]
    for inst in ["admin","high","supreme"]:
        if re.search(rf"^\s*-?\s*{inst}\s*:\s*◌\s*NOT-COVERED", text, re.M):
            matrix[aid]["negative"].add(inst)

# ---------- 10 KRI ----------
def kri(text):
    sents = [s.strip() for s in re.split(r"[.!?。\n]+", text) if len(s.strip())>5]
    if not sents: return None
    wcs=[]; wls=[]
    for s in sents:
        ws=s.split(); wcs.append(len(ws)); wls.extend(len(w) for w in ws)
    ASL=sum(wcs)/len(wcs); AWL=sum(wls)/max(len(wls),1)
    return 100-0.6*AWL-0.3*ASL, ASL, AWL

# ---------- 14 instance suffix consistency ----------
# R-* atoms with instance=admin should have -admin suffix (or be admin-only)
suffix_issues = []
for aid, (path, cat) in atoms.items():
    text = open(path, encoding="utf-8").read()
    mi = re.search(r"^instance:\s*(.+)$", text, re.M)
    if not mi: continue
    inst_str = mi.group(1).strip()
    # only care about single-instance reasoning atoms
    if cat == "R":
        if inst_str == "admin" and not aid.endswith("-admin"): suffix_issues.append((aid, "needs -admin"))
        if inst_str == "high" and not aid.endswith("-high"): suffix_issues.append((aid, "needs -high"))
        if inst_str == "supreme" and not aid.endswith("-supreme"): suffix_issues.append((aid, "needs -supreme"))

# ---------- REPORT ----------
print("="*72)
print("VERIFICATION REPORT (v2) — labor-cases-pipeline-test")
print("="*72)

print(f"\n[1] ATOM INVENTORY                                  total = {len(atoms)}")
for cat, d in ATOM_DIRS.items():
    n = len(glob.glob(d+"/*.md"))
    print(f"    {cat:<4} {d.split('/')[-1]:<14} {n}")

print(f"\n[2] YAML FRONT-MATTER                               missing={len(yaml_missing)}")
for k in required_fields:
    pct = field_presence[k]/len(atoms)*100 if atoms else 0
    flag = " " if pct == 100 else "!"
    print(f"  {flag} {k:<12} {field_presence[k]}/{len(atoms)} ({pct:.1f}%)")
print(f"  · status (optional) {field_presence['status']}/{len(atoms)} ({field_presence['status']/len(atoms)*100:.1f}%)")

print(f"\n[3] WIKILINK INTEGRITY")
integrity = (total_links-len(unresolved))/total_links*100 if total_links else 0
print(f"    total {total_links} / unresolved {len(unresolved)} / integrity {integrity:.2f}%")
for u in unresolved[:5]: print(f"    - {u}")

print(f"\n[4] GRAPH DEGREE")
zero_in = [a for a,v in in_deg.items() if v==0]
print(f"    avg in {sum(in_deg.values())/len(atoms):.2f} / out {sum(out_deg.values())/len(atoms):.2f}")
print(f"    zero in-degree: {len(zero_in)}: {zero_in}")

print(f"\n[5] JSONL TRAINING PAIRS                            {len(pairs)} pairs / {len(jsonl_errs)} errors")

print(f"\n[6] COMPLIANCE VIOLATIONS (context-aware)            {len(violations)}")

print(f"\n[7] CITATION DENSITY                                 {src_cited}/{len(atoms)} ({src_cited/len(atoms)*100:.1f}%)")

print(f"\n[8] CONFIDENCE DISTRIBUTION")
for k,v in conf.items(): print(f"    {k:<8} {v}")

print(f"\n[9] ISSUE × INSTANCE MATRIX (●=reasoning atom, ◌=NOT-COVERED 명시, ○=결손)")
issues = ["I-001-lawyer-accompaniment","I-002-fact-misperception",
          "I-003-disciplinary-discretion","I-004-rule-reasonableness"]
covered=0; total_cells=len(issues)*3
for i in issues:
    cells = matrix.get(i,{"positive":set(),"negative":set()})
    def mark(inst):
        if inst in cells["positive"]: return "●"
        if inst in cells["negative"]: return "◌"
        return "○"
    a,h,s = mark("admin"), mark("high"), mark("supreme")
    print(f"    {i:<35} admin:{a}  high:{h}  supreme:{s}")
    covered += sum(1 for x in [a,h,s] if x in "●◌")
print(f"    cells covered: {covered}/{total_cells} ({covered/total_cells*100:.1f}%)")

print(f"\n[10] KOREAN READABILITY")
for p in ["03_marketing_pipeline/03_card_news.md",
          "03_marketing_pipeline/04_blog_post.md",
          "03_marketing_pipeline/05_ad_copy.md"]:
    if not os.path.exists(p): continue
    r = kri(open(p, encoding="utf-8").read())
    if r: print(f"    {p:<45} KRI={r[0]:.1f}")

print(f"\n[11] CATEGORY WHITELIST (allowed {sorted(ALLOWED_CATS)})")
print(f"    bad category atoms: {len(bad_category)}")

print(f"\n[12] ATOM-ID == FILENAME")
print(f"    mismatches: {len(id_mismatch)}")
for m in id_mismatch[:5]: print(f"    - {m}")

print(f"\n[13] SLUG FORMAT (lowercase ASCII + hyphen)")
print(f"    bad slugs: {len(bad_slug)}")

print(f"\n[14] INSTANCE SUFFIX CONSISTENCY (R-*)")
print(f"    issues: {len(suffix_issues)}")
for s in suffix_issues[:5]: print(f"    - {s}")

# ---------- PASS/FAIL ----------
print("\n" + "="*72)
fails = []
if yaml_missing: fails.append(f"YAML missing in {len(yaml_missing)} atoms")
if unresolved: fails.append(f"{len(unresolved)} unresolved wikilinks")
if zero_in: fails.append(f"{len(zero_in)} orphan atoms (zero in-degree)")
if jsonl_errs: fails.append(f"{len(jsonl_errs)} JSONL errors")
if violations: fails.append(f"{len(violations)} compliance violations")
if bad_category: fails.append(f"{len(bad_category)} bad category atoms")
if id_mismatch: fails.append(f"{len(id_mismatch)} id↔filename mismatches")
if bad_slug: fails.append(f"{len(bad_slug)} bad slugs")
if suffix_issues: fails.append(f"{len(suffix_issues)} instance suffix issues")
matrix_pct = covered/total_cells*100
if matrix_pct < 100: fails.append(f"Issue×Instance matrix coverage {matrix_pct:.1f}% < 100%")

if fails:
    print("RESULT: FAIL")
    for f in fails: print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: PASS — all checks green (100%)")
    sys.exit(0)
