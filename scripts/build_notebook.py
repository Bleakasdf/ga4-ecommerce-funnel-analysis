from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "notebooks" / "ga4_product_funnel.ipynb"


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(source: str, output: str, count: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "source": source.splitlines(keepends=True),
        "outputs": [
            {
                "name": "stdout",
                "output_type": "stream",
                "text": [line + "\n" for line in output.rstrip().splitlines()],
            }
        ],
    }


def main() -> None:
    segments = pd.read_csv(SOURCE / "funnel_segments.csv")
    funnel = pd.read_csv(PROCESSED / "funnel.csv")
    categories = pd.read_csv(PROCESSED / "category_opportunity.csv")
    weekly = pd.read_csv(PROCESSED / "weekly_funnel.csv")
    overall = segments.loc[segments.segment_type == "Overall"].iloc[0]

    channel = segments.loc[
        (segments.segment_type == "First-user acquisition channel")
        & segments.segment_value.isin(["google / organic", "google / cpc", "(direct) / (none)"])
    ].copy()
    channel["scenario_extra_purchases"] = (
        channel.view_sessions * float(overall.view_to_purchase_rate) - channel.purchase_sessions
    ).clip(lower=0).round().astype(int)

    checks = pd.DataFrame(
        {
            "check": ["Funnel counts decrease", "Weekly purchases reconcile", "Ordered purchases reconcile"],
            "passed": [
                funnel.sessions.is_monotonic_decreasing,
                weekly.purchase_sessions.sum() == overall.purchase_sessions,
                funnel.iloc[-1].sessions == overall.purchase_sessions,
            ],
        }
    )

    cells = [
        markdown(
            "# GA4 ecommerce funnel analysis\n\n"
            "**Business question:** At which stage are the largest user losses occurring, "
            "which segments contribute most to the missed purchase opportunity, and what "
            "should the product team investigate first?"
        ),
        markdown(
            "## 1. Data scope\n\n"
            "The public GA4 sample covers 1 Nov 2020–31 Jan 2021. `add_to_cart` is missing "
            "on 18 dates, including 21–24 Nov, so headline metrics use the stable 25 Nov "
            "2020–31 Jan 2021 window."
        ),
        code(
            "import pandas as pd\n\n"
            "segments = pd.read_csv('../data/source/funnel_segments.csv')\n"
            "funnel = pd.read_csv('../data/processed/funnel.csv')\n"
            "categories = pd.read_csv('../data/processed/category_opportunity.csv')\n"
            "weekly = pd.read_csv('../data/processed/weekly_funnel.csv')\n"
            "print(segments.loc[segments.segment_type == 'Overall'].to_string(index=False))",
            segments.loc[segments.segment_type == "Overall"].to_string(index=False),
            1,
        ),
        markdown(
            "## 2. Ordered session funnel\n\n"
            "SQL assigns a session to a stage only if events occur in order: "
            "`view_item → add_to_cart → begin_checkout → purchase`."
        ),
        code(
            "funnel[['stage', 'sessions', 'step_conversion_rate', 'dropoff_sessions', 'dropoff_rate']]",
            funnel[["stage", "sessions", "step_conversion_rate", "dropoff_sessions", "dropoff_rate"]].to_string(index=False),
            2,
        ),
        markdown(
            "**Finding:** 42,078 sessions, or 74.2%, are lost between product view and add to cart. "
            "This is the first area to diagnose."
        ),
        markdown("## 3. Segment priority"),
        code(
            "overall_rate = segments.loc[segments.segment_type == 'Overall', 'view_to_purchase_rate'].iloc[0]\n"
            "channels = segments[segments.segment_type == 'First-user acquisition channel'].copy()\n"
            "channels = channels[channels.segment_value.isin(['google / organic', 'google / cpc', '(direct) / (none)'])]\n"
            "channels['scenario_extra_purchases'] = ((channels.view_sessions * overall_rate) - channels.purchase_sessions).clip(lower=0).round()\n"
            "print(channels[['segment_value', 'view_sessions', 'view_to_purchase_rate', 'scenario_extra_purchases']].sort_values('scenario_extra_purchases', ascending=False).to_string(index=False))",
            channel[["segment_value", "view_sessions", "view_to_purchase_rate", "scenario_extra_purchases"]]
            .sort_values("scenario_extra_purchases", ascending=False)
            .to_string(index=False),
            3,
        ),
        markdown(
            "**Finding:** Google organic has the largest actionable volume-adjusted gap: 17,442 "
            "viewed sessions and 3.99% purchase conversion versus 4.71% overall. Reaching the "
            "overall rate is a transparent scenario of about 126 additional purchases, not a forecast."
        ),
        markdown("## 4. Product category opportunity"),
        code(
            "print(categories.head(6).to_string(index=False))",
            categories.head(6).to_string(index=False),
            4,
        ),
        markdown(
            "Category analysis stops at add to cart because later item-category values are not "
            "comparable. The scenario uses the overall view-to-cart rate and downstream "
            "cart-to-purchase rate."
        ),
        markdown("## 5. Validation"),
        code("print(checks.to_string(index=False))", checks.to_string(index=False), 5),
        markdown(
            "## 6. Recommendation\n\n"
            "Investigate product-detail and add-to-cart friction first. Begin with Google organic "
            "sessions and the YouTube and Bags category paths. Add page-level diagnostics such as "
            "stock status, price visibility, CTA exposure, errors, and load time; then test the most "
            "supported product hypothesis with an A/B experiment. Device rates are similar, so device "
            "is not the first priority.\n\n"
            "This observational sample identifies where to investigate; it does not prove causality."
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
