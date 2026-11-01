"""CLI:  python -m generator --seed 20261022 --employees 5000 --out data/full"""
import argparse, json, os, sys
from .config import Config, SEED
from .build import generate_all
from .validate import validate
from .evaluate import detection_metrics, distribution_metrics
from .export import export_all
from .docs import write_docs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m generator", description="Synthetic compensation-equity data generator")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--employees", type=int, default=5000, help="scale: 200 = starter, 5000 = full")
    ap.add_argument("--out", default="data/full")
    ap.add_argument("--docs", default=None, help="optional: also (re)write docs/ from the schema")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    cfg = Config(seed=a.seed, employees=a.employees)
    R = generate_all(cfg)
    T, gt, an = R["tables"], R["ground_truth"], R["analysis"]
    val = validate(T, gt, an, R["master"])
    metrics = dict(detection=detection_metrics(T, an, gt), distributions=distribution_metrics(T, an))
    cmd = f"python -m generator --seed {a.seed} --employees {a.employees} --out {a.out}"
    rows = export_all(R, a.out, val, metrics, cmd)
    if a.docs:
        write_docs(a.docs)
    if not a.quiet:
        print(f"[{a.out}] seed={a.seed} employees={a.employees} validation={val['status']} "
              f"unexpected_errors={val['unexpected_errors']} labelled_findings={val['labelled_findings_observed']}")
        for k, v in metrics["detection"].items():
            print(f"   {k:34s} truth={v['ground_truth']:3d} detected={v['detected']:3d} precision={v['precision']} recall={v['recall']}")
    return 0 if val["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
