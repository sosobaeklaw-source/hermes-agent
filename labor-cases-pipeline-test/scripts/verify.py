#!/usr/bin/env python3
"""
labor-cases-pipeline-test 자체 검증 스크립트

실행: python3 labor-cases-pipeline-test/scripts/verify.py
의존성: 표준 라이브러리만

검증 항목:
  1. Atom inventory (개수, 카테고리)
  2. YAML front-matter 필드 무결성
  3. Wikilink integrity (177개 링크 0개 unresolved 여부)
  4. Atom graph degree distribution
  5. JSONL 유효성 + atom_refs 해결성
  6. 컴플라이언스 스캔 (변호사법 §23, 표시광고법 §3, 자료 결론 단정)
     - 컨텍스트 인식: negative example 줄은 제외
  7. Citation density (source: 필드 보유율)
  8. Confidence distribution
  9. Issue × Instance matrix coverage
 10. Korean readability index (KRI proxy)

모든 검증은 결정적(deterministic)이며 외부 API/모델 불사용. 같은 입력에 대해
항상 같은 출력을 내므로 CI에서 회귀 테스트로 사용 가능.
"""
import os, re, json, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# ---------- 1. atom inventory ----------
atom_dirs = ["01_atomized/parties","01_atomized/facts","01_atomized/procedure",
             "01_atomized/issues","01_atomized/doctrines","01_atomized/reasoning","01_atomized/outcomes"]
atoms = {os.path.splitext(os.path.basename(f))[0]: f
         for d in atom_dirs for f in sorted(glob.glob(d+"/*.md"))}

# ---------- 2. YAML front-matter ----------
required_fields = ["id","type","instance","source","tags","related","confidence"]
field_presence = {k:0 for k in required_fields}
yaml_missing = []
for aid, path in atoms.items():
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m: yaml_missing.append(aid); continue
    for k in required_fields:
        if re.search(rf"^{k}\s*:", m.group(1), re.M):
            field_presence[k] += 1

# ---------- 3. Wikilink integrity ----------
link_re = re.compile(r"\[\[([A-Z]+-\d+-[a-zA-Z0-9-]+)\]\]")
in_deg = {a:0 for a in atoms}
out_deg = {a:0 for a in atoms}
unresolved = []
total_links = 0
scan_paths = list(atoms.values()) + glob.glob("02_legal_pipeline/*.md") + \
             glob.glob("03_marketing_pipeline/*.md") + \
             ["01_atomized/_graph.md","01_atomized/README.md","REPORT.md","00_source/INDEX.md"]
for p in scan_paths:
    if not os.path.exists(p): continue
    text = open(p, encoding="utf-8").read()
    src = os.path.splitext(os.path.basename(p))[0]
    for tgt in link_re.findall(text):
        total_links += 1
        if src in atoms: out_deg[src] += 1
        if tgt in atoms: in_deg[tgt] += 1
        else: unresolved.append((p, tgt))

# ---------- 5. JSONL ----------
jsonl_path = "02_legal_pipeline/04_training_pairs.jsonl"
jsonl_errs = []
pairs = []
if os.path.exists(jsonl_path):
    for i, line in enumerate(open(jsonl_path, encoding="utf-8"), 1):
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            pairs.append(obj)
            for k in ["id","type","prompt","completion"]:
                if k not in obj: jsonl_errs.append((i, f"missing {k}"))
            for ref in obj.get("atom_refs", []):
                if ref not in atoms:
                    jsonl_errs.append((i, f"unresolved atom_refs: {ref}"))
        except json.JSONDecodeError as e:
            jsonl_errs.append((i, f"JSON parse error: {e}"))

# ---------- 6. Compliance scan (context-aware) ----------
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

# ---------- 7. Source citation density ----------
src_cited = 0
for p in atoms.values():
    text = open(p, encoding="utf-8").read()
    m = re.search(r"^source:\s*(\S.*)$", text, re.M)
    if m and m.group(1).strip().lower() not in ("","n/a","none"): src_cited += 1

# ---------- 8. Confidence distribution ----------
conf = {"high":0,"medium":0,"low":0,"other":0}
for p in atoms.values():
    text = open(p, encoding="utf-8").read()
    m = re.search(r"^confidence:\s*(\S+)", text, re.M)
    v = m.group(1).strip().lower() if m else "other"
    conf[v if v in conf else "other"] += 1

# ---------- 9. Issue × Instance matrix ----------
import collections
matrix = collections.defaultdict(set)
for p in atoms.values():
    if "/reasoning/" not in p: continue
    text = open(p, encoding="utf-8").read()
    mi = re.search(r"^instance:\s*(.+)$", text, re.M)
    if not mi: continue
    insts = re.findall(r"(admin|high|supreme)", mi.group(1))
    issues = re.findall(r"\[\[(I-\d+-[a-z-]+)\]\]", text)
    for i in issues:
        for ii in insts: matrix[i].add(ii)

# ---------- 10. KRI ----------
def kri(text):
    sents = [s.strip() for s in re.split(r"[.!?。\n]+", text) if len(s.strip())>5]
    if not sents: return None
    word_counts=[]; word_lens=[]
    for s in sents:
        ws = s.split(); word_counts.append(len(ws)); word_lens.extend(len(w) for w in ws)
    ASL = sum(word_counts)/len(word_counts)
    AWL = sum(word_lens)/max(len(word_lens),1)
    return 100 - 0.6*AWL - 0.3*ASL, ASL, AWL

# ---------- REPORT ----------
print("="*70)
print("VERIFICATION REPORT — labor-cases-pipeline-test")
print("="*70)

print(f"\n[1] ATOM INVENTORY")
print(f"    total = {len(atoms)}")
for d in atom_dirs:
    print(f"    {d.split('/')[-1]:<12} {len(glob.glob(d+'/*.md'))}")

print(f"\n[2] YAML FRONT-MATTER")
print(f"    missing front-matter: {len(yaml_missing)}")
for k,v in field_presence.items():
    pct = v/len(atoms)*100
    print(f"    {k:<12} {v}/{len(atoms)} ({pct:.1f}%)")

print(f"\n[3] WIKILINK INTEGRITY")
integrity = (total_links - len(unresolved))/total_links*100 if total_links else 0
print(f"    total links:    {total_links}")
print(f"    unresolved:     {len(unresolved)}")
print(f"    integrity:      {integrity:.2f}%")

print(f"\n[4] GRAPH DEGREE")
print(f"    avg in-degree:  {sum(in_deg.values())/len(atoms):.2f}")
print(f"    avg out-degree: {sum(out_deg.values())/len(atoms):.2f}")
print(f"    zero in-deg:    {[a for a,v in in_deg.items() if v==0]}")

print(f"\n[5] JSONL TRAINING PAIRS")
print(f"    pairs:  {len(pairs)}")
print(f"    errors: {len(jsonl_errs)}")

print(f"\n[6] COMPLIANCE VIOLATIONS (context-aware)")
print(f"    true violations: {len(violations)}")
for v in violations: print(f"    - {v}")

print(f"\n[7] CITATION DENSITY")
print(f"    source field present: {src_cited}/{len(atoms)} ({src_cited/len(atoms)*100:.1f}%)")

print(f"\n[8] CONFIDENCE DISTRIBUTION")
for k,v in conf.items(): print(f"    {k:<8} {v}")

print(f"\n[9] ISSUE × INSTANCE MATRIX")
issues = ["I-001-lawyer-accompaniment","I-002-fact-misperception",
          "I-003-disciplinary-discretion","I-004-rule-reasonableness"]
covered=0
for i in issues:
    row = [matrix.get(i,set())]
    print(f"    {i:<35} {'admin' if 'admin' in row[0] else '....':<8} "
          f"{'high' if 'high' in row[0] else '....':<8} "
          f"{'supreme' if 'supreme' in row[0] else '....':<8}")
    covered += len(row[0] & {'admin','high','supreme'})
print(f"    cells covered: {covered}/{len(issues)*3} ({covered/(len(issues)*3)*100:.1f}%)")

print(f"\n[10] KOREAN READABILITY (KRI proxy)")
for p in ["03_marketing_pipeline/03_card_news.md",
          "03_marketing_pipeline/04_blog_post.md",
          "03_marketing_pipeline/05_ad_copy.md"]:
    if not os.path.exists(p): continue
    r = kri(open(p, encoding="utf-8").read())
    if r: print(f"    {p:<45} KRI={r[0]:.1f} ASL={r[1]:.1f} AWL={r[2]:.2f}")

# ---------- PASS/FAIL ----------
print("\n" + "="*70)
fails = []
if yaml_missing: fails.append(f"YAML missing in {len(yaml_missing)} atoms")
if unresolved: fails.append(f"{len(unresolved)} unresolved wikilinks")
if jsonl_errs: fails.append(f"{len(jsonl_errs)} JSONL errors")
if violations: fails.append(f"{len(violations)} compliance violations")
if fails:
    print("RESULT: FAIL")
    for f in fails: print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: PASS — all structural checks green")
    sys.exit(0)
