#!/usr/bin/env bash
# Step 10: regenerate twice with the same seed and compare row counts + SHA-256 checksums of every output file.
# Usage: ./reproducibility_check.sh [seed] [employees]
set -euo pipefail
SEED="${1:-20261022}"; N="${2:-5000}"
PY="${PYTHON:-python3}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
$PY -m generator --seed "$SEED" --employees "$N" --out "$TMP/run1" --quiet || true
$PY -m generator --seed "$SEED" --employees "$N" --out "$TMP/run2" --quiet || true
$PY - "$TMP" "$SEED" "$N" <<'PY'
import json, sys
tmp, seed, n = sys.argv[1], sys.argv[2], sys.argv[3]
a = json.load(open(f"{tmp}/run1/checksums.json")); b = json.load(open(f"{tmp}/run2/checksums.json"))
ma = json.load(open(f"{tmp}/run1/manifest/source_manifest.json"))["row_counts"]
mb = json.load(open(f"{tmp}/run2/manifest/source_manifest.json"))["row_counts"]
diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
print(f"seed={seed} employees={n}")
print(f"{'table':28s}{'run1 rows':>10s}{'run2 rows':>10s}")
for t in sorted(ma):
    print(f"{t:28s}{ma[t]:>10d}{mb[t]:>10d}{'  OK' if ma[t] == mb[t] else '  MISMATCH'}")
print(f"files compared (SHA-256): {len(a)};  differing files: {len(diff)}")
ok = not diff and ma == mb
report = dict(seed=int(seed), employees=int(n), files_compared=len(a), differing_files=diff, row_counts_equal=ma == mb,
              result="REPRODUCIBLE" if ok else "NOT REPRODUCIBLE", sample_checksums={k: a[k] for k in sorted(a)[:5]})
json.dump(report, open("reproducibility_report.json", "w"), indent=2)
print(report["result"]); sys.exit(0 if ok else 1)
PY
