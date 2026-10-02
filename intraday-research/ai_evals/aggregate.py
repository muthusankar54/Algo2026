"""Aggregate the LLM-as-judge panel: python ai_evals/aggregate.py

Reads ai_evals/judgments/judge_*.json (one per independent judge, same rubric) and writes
ai_evals/panel_summary.md and ai_evals/panel_scores.csv. Reports per-dimension mean and
spread, the verdict distribution and Kendall's W (agreement of the judges' rankings of the
eight dimensions; 1 = identical rankings, 0 = no agreement).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = Path(__file__).resolve().parent
DIMENSIONS = ["thesis_fit", "edge_evidence", "cost_feasibility", "method_rigor", "risk_control",
              "regulatory_operational", "behavioral_sustainability", "nifty_sensex_combination"]
VERDICT_ORDER = ["NO_GO", "PILOT_ONLY", "CONDITIONAL_GO", "GO"]


def kendalls_w(scores: np.ndarray) -> float:
    """scores: (judges, items). Tie-corrected Kendall's coefficient of concordance."""
    m, n = scores.shape
    ranks = np.vstack([sps.rankdata(row) for row in scores])
    r = ranks.sum(axis=0)
    s = ((r - r.mean()) ** 2).sum()
    ties = 0.0
    for row in scores:
        _, counts = np.unique(row, return_counts=True)
        ties += (counts ** 3 - counts).sum()
    return float(12 * s / (m ** 2 * (n ** 3 - n) - m * ties))


def main() -> None:
    judges = [json.loads(p.read_text()) for p in sorted((HERE / "judgments").glob("judge_*.json"))]
    if not judges:
        raise SystemExit("no judgments found")
    rows = []
    for j in judges:
        row = {"judge": j["judge"], "persona": j["persona"], "verdict": j["verdict"],
               "confidence": j["confidence"], "p_net_profitable_12m": j["p_net_profitable_12m"]}
        row.update({d: j["scores"][d]["score"] for d in DIMENSIONS})
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "panel_scores.csv", index=False)

    dim = df[DIMENSIONS].agg(["mean", "std", "min", "max"]).T.round(2)
    w = kendalls_w(df[DIMENSIONS].to_numpy(float))
    verdicts = df["verdict"].value_counts().reindex(VERDICT_ORDER, fill_value=0)

    lines = ["# AI-judge panel results", "",
             f"{len(df)} independent judges, same dossier and rubric (scores 1-10, 10 = most favourable "
             "to the proposal).", "",
             "## Verdicts", "", "| Judge | Persona | Verdict | Confidence | P(net profitable, 12m) |",
             "|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.judge} | {r.persona} | {r.verdict} | {r.confidence:.2f} | {r.p_net_profitable_12m:.2f} |")
    lines += ["", "Verdict distribution: " + ", ".join(f"{k} {v}" for k, v in verdicts.items()),
              f"Mean P(net profitable over 12 months): {df.p_net_profitable_12m.mean():.2f} "
              f"(range {df.p_net_profitable_12m.min():.2f}-{df.p_net_profitable_12m.max():.2f})", "",
              "## Scores by dimension", "", "| Dimension | Mean | SD | Min | Max |", "|---|---|---|---|---|"]
    for d, r in dim.iterrows():
        lines.append(f"| {d} | {r['mean']:.1f} | {r['std']:.1f} | {r['min']:.0f} | {r['max']:.0f} |")
    lines += ["", f"Overall mean score: {df[DIMENSIONS].to_numpy().mean():.2f} / 10", "",
              f"Inter-judge agreement on which dimensions are strong vs weak (Kendall's W): {w:.2f}", ""]

    lines += ["## Per-judge scores", "", "| Judge | " + " | ".join(DIMENSIONS) + " |",
              "|---|" + "---|" * len(DIMENSIONS)]
    for r in df.itertuples():
        lines.append(f"| {r.judge} | " + " | ".join(str(getattr(r, d)) for d in DIMENSIONS) + " |")

    lines += ["", "## Must-have conditions and best variants (verbatim, by judge)", ""]
    for j in judges:
        lines.append(f"### {j['judge']} ({j['persona']}): {j['verdict']}")
        lines.append("")
        lines.append("Top failure modes: " + "; ".join(j["top_failure_modes"]))
        lines.append("")
        lines.append("Must-have conditions:")
        lines += [f"- {c}" for c in j["must_have_conditions"]]
        lines.append("")
        lines.append(f"Best variant: {j['best_variant']}")
        lines.append("")
        lines.append(f"Would change verdict: {j['evidence_that_would_change_verdict']}")
        if j.get("disagreements_with_dossier"):
            lines.append("")
            lines.append("Disagreements with the dossier:")
            lines += [f"- {c}" for c in j["disagreements_with_dossier"]]
        lines.append("")
    (HERE / "panel_summary.md").write_text("\n".join(lines))
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
