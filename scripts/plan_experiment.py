"""Size the next GA4 funnel experiment from committed aggregate results."""

import csv
import math
from datetime import date
from pathlib import Path
from statistics import NormalDist


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "decision_summary.csv"
OUTPUT = ROOT / "outputs" / "experiment_plan.md"
ALPHA = 0.05
POWER = 0.80
TARGET_RELATIVE_LIFT = 0.10


def sample_size_per_arm(baseline: float, variant: float) -> int:
    z_alpha = NormalDist().inv_cdf(1 - ALPHA / 2)
    z_power = NormalDist().inv_cdf(POWER)
    pooled = (baseline + variant) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power * math.sqrt(
            baseline * (1 - baseline) + variant * (1 - variant)
        )
    ) ** 2
    return math.ceil(numerator / (variant - baseline) ** 2)


with SOURCE.open(encoding="utf-8", newline="") as source_file:
    summary = next(csv.DictReader(source_file))

baseline = float(summary["view_to_purchase_rate"])
variant = baseline * (1 + TARGET_RELATIVE_LIFT)
per_arm = sample_size_per_arm(baseline, variant)
total_sample = per_arm * 2
period_days = (
    date.fromisoformat(summary["analysis_end"])
    - date.fromisoformat(summary["analysis_start"])
).days + 1
historical_views_per_day = int(summary["view_sessions"]) / period_days
estimated_days = math.ceil(total_sample / historical_views_per_day)

OUTPUT.write_text(
    f"""# Experiment plan: product-view to purchase funnel

## Decision

Test the highest-evidence product-page friction hypothesis after instrumentation QA. Randomize eligible viewed sessions 50/50 at the user level and keep assignment sticky across sessions.

## Sizing

- Baseline purchase conversion per viewed session: **{baseline:.2%}**.
- Target detectable effect: **{TARGET_RELATIVE_LIFT:.0%} relative lift** to **{variant:.2%}**.
- Two-sided alpha: **{ALPHA:.0%}**; power: **{POWER:.0%}**.
- Required sample: **{per_arm:,} viewed sessions per arm** (**{total_sample:,} total**).
- At the historical rate of **{historical_views_per_day:,.0f} viewed sessions/day**, the lower-bound runtime is about **{estimated_days} days** before adding a full-business-cycle constraint.

## Measurement contract

- Primary outcome: purchase conversion per assigned user among eligible product viewers.
- Diagnostic: add-to-cart conversion, add-to-cart error rate, and CTA exposure.
- Guardrails: revenue per viewed session, checkout error rate, and refund rate if available.
- Segments are diagnostic only; the overall treatment effect is the decision metric.

## Decision rule

Ship only if the predeclared primary metric improves, guardrails stay within agreed bounds, instrumentation is stable, and the result survives a full business cycle. Otherwise iterate or stop; do not select a winning segment after the fact.

## Caveats

This is an analytical design, not an executed experiment. The sample calculation uses the committed aggregate baseline and a normal approximation for two independent proportions. Recalculate with user-level exposure data before launch and adjust for repeat sessions or other clustering.
""",
    encoding="utf-8",
)

print(f"Wrote {OUTPUT.relative_to(ROOT)}")

