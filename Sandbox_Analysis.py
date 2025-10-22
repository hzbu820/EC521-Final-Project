#!/usr/bin/env python3
"""
Analyze sandbox JSON reports and produce statistical summaries.

Inputs:
  - One or more JSON files (glob default: reports/*.json)
  - Optional ground-truth mapping:
      * ENV: BENIGN_PACKAGES="requests,pyyaml" (comma-separated, case-insensitive)
      * ENV: MALICIOUS_PACKAGES="badlib,evilpkg"
    If not provided, truth is inferred from filename prefixes:
      * reports/benign_*.json -> benign
      * reports/malicious_*.json -> malicious

JSON Schema (flexible):
  We try these keys if present:
    - package name:  ["package_name","name","package","pkg"]
    - registry:      ["registry","ecosystem"]
    - predicted lbl: ["label"]  (values like: safe|warn|block|malicious|benign)
    - risk score:    ["risk","score","slop_score","prob"]

Prediction rule (default):
  - If 'label' exists:
        positive = label in {"warn","block","malicious","suspicious"}
    else if 'risk' exists:
        positive = risk >= --threshold (default 0.50)
  You can override positive rule by --positive-if "label" or "risk>=0.8"

Outputs:
  - analysis/metrics.json   (all computed metrics)
  - analysis/metrics.csv    (per-file and per-threshold rows)
  - analysis/metrics.md     (pretty summary for CI)
  - prints metrics.md to stdout; appends to $GITHUB_STEP_SUMMARY if set.

Usage:
  python scripts/analyze_reports.py \
      --glob "reports/*.json" \
      --thresholds 0.3 0.5 0.8

Requires: Python 3.9+, pandas (optional; will fallback to CSV via stdlib if missing)
"""

from __future__ import annotations
import argparse, glob, json, os, re, sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except Exception:
    pd = None  # will fallback

POS_LABELS = {"warn", "block", "malicious", "suspicious"}
NEG_LABELS = {"safe", "benign", "clean"}

def _get(obj: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return default

def normalize_name(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    # common formats like "pkg==1.2.3" or "@scope/pkg"
    s = re.split(r"[=<>~!^ ]", s)[0]
    return s.lower()

def infer_truth_from_env(name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    b = os.getenv("BENIGN_PACKAGES", "")
    m = os.getenv("MALICIOUS_PACKAGES", "")
    benign = {x.strip().lower() for x in b.split(",") if x.strip()}
    malicious = {x.strip().lower() for x in m.split(",") if x.strip()}
    if name in benign:
        return 0
    if name in malicious:
        return 1
    return None

def infer_truth_from_path(path: str) -> Optional[int]:
    base = os.path.basename(path).lower()
    if base.startswith("benign_") or "benign" in base:
        return 0
    if base.startswith("malicious_") or "malicious" in base or "evil" in base:
        return 1
    return None

def load_reports(paths: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    out = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)
        except Exception as e:
            print(f"[WARN] cannot parse {p}: {e}", file=sys.stderr)
            continue
        # Some reports might be a list; flatten into one record per item with file hint
        if isinstance(j, list):
            for idx, item in enumerate(j):
                if isinstance(item, dict):
                    item["_source_file"] = p
                    item["_source_index"] = idx
                    out.append((p, item))
        elif isinstance(j, dict):
            j["_source_file"] = p
            out.append((p, j))
        else:
            print(f"[WARN] {p} JSON not dict/list, skipping.", file=sys.stderr)
    return out

def derive_row(rec: Dict[str, Any], default_threshold: float) -> Dict[str, Any]:
    name = normalize_name(_get(rec, ["package_name", "name", "package", "pkg"]))
    registry = _get(rec, ["registry", "ecosystem"], "unknown")
    label = _get(rec, ["label"], None)
    risk = _get(rec, ["risk", "score", "slop_score", "prob"], None)

    # Normalize label if string
    norm_label = str(label).lower() if isinstance(label, str) else None
    # Prediction: positive?
    if norm_label:
        pred_pos = norm_label in POS_LABELS
    elif isinstance(risk, (int, float)):
        pred_pos = float(risk) >= default_threshold
    else:
        # If no usable prediction, treat as negative but mark unknown
        pred_pos = False

    # Ground truth:
    truth = infer_truth_from_env(name)
    if truth is None:
        truth = infer_truth_from_path(rec.get("_source_file", ""))

    return {
        "file": rec.get("_source_file", ""),
        "index": rec.get("_source_index", None),
        "name": name,
        "registry": registry,
        "label": norm_label,
        "risk": None if risk is None else float(risk),
        "pred_positive": int(bool(pred_pos)),
        "truth": truth,  # 0 benign, 1 malicious, None unknown
    }

def compute_metrics(rows: List[Dict[str, Any]], thresholds: List[float]) -> Dict[str, Any]:
    # Filter rows with known truth
    known = [r for r in rows if r["truth"] in (0, 1)]
    # Aggregate per default decision already in rows (pred_positive)
    tp = sum(1 for r in known if r["truth"] == 1 and r["pred_positive"] == 1)
    fp = sum(1 for r in known if r["truth"] == 0 and r["pred_positive"] == 1)
    tn = sum(1 for r in known if r["truth"] == 0 and r["pred_positive"] == 0)
    fn = sum(1 for r in known if r["truth"] == 1 and r["pred_positive"] == 0)

    def safe_div(a,b): return (a / b) if b else 0.0
    precision = safe_div(tp, tp + fp)
    recall    = safe_div(tp, tp + fn)
    f1        = safe_div(2*precision*recall, precision+recall) if (precision+recall)>0 else 0.0
    acc       = safe_div(tp+tn, tp+tn+fp+fn)
    fpr       = safe_div(fp, fp+tn)
    fnr       = safe_div(fn, fn+tp)

    # Threshold sweep if risk available
    thresh_rows = []
    for t in thresholds:
        T_tp=T_fp=T_tn=T_fn=0
        n_with_risk=0
        for r in known:
            if r["risk"] is None:
                continue
            n_with_risk += 1
            pos = 1 if r["risk"] >= t else 0
            if r["truth"]==1 and pos==1: T_tp+=1
            if r["truth"]==0 and pos==1: T_fp+=1
            if r["truth"]==0 and pos==0: T_tn+=1
            if r["truth"]==1 and pos==0: T_fn+=1
        p = safe_div(T_tp, T_tp+T_fp)
        r_ = safe_div(T_tp, T_tp+T_fn)
        f1_ = safe_div(2*p*r_, p+r_) if (p+r_)>0 else 0.0
        thresh_rows.append({
            "threshold": t,
            "n_with_risk": n_with_risk,
            "tp": T_tp, "fp": T_fp, "tn": T_tn, "fn": T_fn,
            "precision": round(p,4), "recall": round(r_,4), "f1": round(f1_,4)
        })

    # Per-bucket summaries
    by_truth = defaultdict(list)
    for r in known:
        by_truth[r["truth"]].append(r["risk"])
    avg_risk_benign = sum(x for x in by_truth[0] if x is not None)/max(1, sum(1 for x in by_truth[0] if x is not None))
    avg_risk_mal    = sum(x for x in by_truth[1] if x is not None)/max(1, sum(1 for x in by_truth[1] if x is not None))

    return {
        "counts": {"total": len(rows), "known": len(known), "unknown": len(rows)-len(known)},
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "metrics": {
            "accuracy": round(acc,4),
            "precision": round(precision,4),
            "recall": round(recall,4),
            "f1": round(f1,4),
            "fpr": round(fpr,4),
            "fnr": round(fnr,4),
        },
        "threshold_sweep": thresh_rows,
        "risk_means": {"benign": round(avg_risk_benign,4), "malicious": round(avg_risk_mal,4)},
    }

def to_markdown(rows: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    cm = summary["confusion_matrix"]; mt = summary["metrics"]
    lines = []
    lines.append("# Sandbox Statistical Analysis\n")
    lines.append(f"- Total reports: **{summary['counts']['total']}** (known truth: **{summary['counts']['known']}**, unknown: **{summary['counts']['unknown']}**)")
    lines.append("")
    lines.append("## Confusion Matrix (default decision rule)")
    lines.append("")
    lines.append("|      | Pred + | Pred - |")
    lines.append("|------|--------|--------|")
    lines.append(f"| True + | {cm['tp']} | {cm['fn']} |")
    lines.append(f"| True - | {cm['fp']} | {cm['tn']} |")
    lines.append("")
    lines.append("**Metrics:** "
                 f"Accuracy={mt['accuracy']:.3f} • Precision={mt['precision']:.3f} • "
                 f"Recall={mt['recall']:.3f} • F1={mt['f1']:.3f} • FPR={mt['fpr']:.3f} • FNR={mt['fnr']:.3f}")
    lines.append("")
    lines.append("## Risk Means (if available)")
    lines.append(f"- Benign avg risk: **{summary['risk_means']['benign']}**")
    lines.append(f"- Malicious avg risk: **{summary['risk_means']['malicious']}**")
    lines.append("")
    if summary["threshold_sweep"]:
        lines.append("## Threshold Sweep (risk-based)")
        lines.append("| thr | n | tp | fp | tn | fn | precision | recall | f1 |")
        lines.append("|-----|---|----|----|----|----|-----------|--------|----|")
        for row in summary["threshold_sweep"]:
            lines.append("| {threshold:.2f} | {n_with_risk} | {tp} | {fp} | {tn} | {fn} | {precision:.3f} | {recall:.3f} | {f1:.3f} |".format(**row))
    lines.append("")
    # Per-file table (top 30)
    lines.append("## Sample of Files")
    lines.append("| file | name | registry | label | risk | pred+ | truth |")
    lines.append("|------|------|----------|-------|------|-------|-------|")
    for r in rows[:30]:
        lines.append(f"| {os.path.basename(r['file'])} | {r['name'] or ''} | {r['registry']} | {r['label'] or ''} | "
                     f"{'' if r['risk'] is None else f'{r['risk']:.3f}'} | {r['pred_positive']} | {r['truth']} |")
    return "\n".join(lines)

def write_csv(rows: List[Dict[str, Any]], sweep: List[Dict[str, Any]], outdir: str):
    os.makedirs(outdir, exist_ok=True)
    perfile = os.path.join(outdir, "per_file.csv")
    thresh  = os.path.join(outdir, "threshold_sweep.csv")
    # Use pandas if available
    if pd:
        pd.DataFrame(rows).to_csv(perfile, index=False)
        pd.DataFrame(sweep).to_csv(thresh, index=False)
    else:
        import csv
        with open(perfile, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            if rows: w.writeheader(); w.writerows(rows)
        with open(thresh, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sweep[0].keys()) if sweep else [])
            if sweep: w.writeheader(); w.writerows(sweep)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="reports/*.json", help="Glob for report JSON files")
    ap.add_argument("--thresholds", type=float, nargs="*", default=[0.5], help="Risk thresholds to sweep")
    ap.add_argument("--default-threshold", type=float, default=0.5, help="Default risk threshold if using risk-based decision")
    ap.add_argument("--outdir", default="analysis", help="Output directory for metrics")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.glob))
    if not paths:
        print(f"[ERROR] No JSON files matched {args.glob}", file=sys.stderr)
        sys.exit(2)

    records = load_reports(paths)
    rows = [derive_row(rec, args.default_threshold) for _, rec in records]

    summary = compute_metrics(rows, args.thresholds)

    os.makedirs(args.outdir, exist_ok=True)
    # Write artifacts
    md = to_markdown(rows, summary)
    with open(os.path.join(args.outdir, "metrics.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(args.outdir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    # CSVs
    write_csv(rows, summary["threshold_sweep"], args.outdir)

    # CI niceties
    print(md)
    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(md)

if __name__ == "__main__":
    main()