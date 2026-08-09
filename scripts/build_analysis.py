from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
PROCESSED = ROOT / "data" / "processed"
POWERBI = ROOT / "data" / "powerbi"
OUTPUTS = ROOT / "outputs"


def save_csv(frame: pd.DataFrame, name: str) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    POWERBI.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED / name, index=False)
    frame.to_csv(POWERBI / name, index=False)


def main() -> None:
    segments = pd.read_csv(SOURCE / "funnel_segments.csv")
    categories = pd.read_csv(SOURCE / "category_opportunity.csv")
    weekly = pd.read_csv(SOURCE / "weekly_funnel.csv", parse_dates=["week_start"])
    quality = pd.read_csv(SOURCE / "data_quality.csv")

    overall = segments.loc[segments["segment_type"] == "Overall"].iloc[0]
    stages = [
        (1, "Viewed product", int(overall["view_sessions"])),
        (2, "Added to cart", int(overall["cart_sessions"])),
        (3, "Started checkout", int(overall["checkout_sessions"])),
        (4, "Purchased", int(overall["purchase_sessions"])),
    ]
    funnel_rows = []
    for index, (order, stage, sessions) in enumerate(stages):
        previous = stages[index - 1][2] if index else sessions
        funnel_rows.append(
            {
                "stage_order": order,
                "stage": stage,
                "sessions": sessions,
                "step_conversion_rate": sessions / previous,
                "dropoff_sessions": previous - sessions if index else 0,
                "dropoff_rate": 1 - sessions / previous if index else 0,
            }
        )
    funnel = pd.DataFrame(funnel_rows)

    overall_rate = float(overall["view_to_purchase_rate"])
    segment_detail = segments.loc[segments["segment_type"] != "Overall"].copy()
    segment_detail["scenario_extra_purchases"] = (
        segment_detail["view_sessions"] * overall_rate - segment_detail["purchase_sessions"]
    ).clip(lower=0).round().astype(int)
    value = segment_detail["segment_value"].astype(str)
    segment_detail["actionable"] = ~value.str.contains("<Other>|data deleted|shop.google", regex=True)

    channel = segment_detail.loc[
        (segment_detail["segment_type"] == "First-user acquisition channel")
        & segment_detail["actionable"]
    ].sort_values("scenario_extra_purchases", ascending=False)
    top_channel = channel.iloc[0]
    top_category = categories.sort_values("scenario_extra_purchases", ascending=False).iloc[0]
    largest_loss = funnel.iloc[1]

    summary = pd.DataFrame(
        [
            {
                "analysis_start": "2020-11-25",
                "analysis_end": "2021-01-31",
                "view_sessions": int(overall["view_sessions"]),
                "purchase_sessions": int(overall["purchase_sessions"]),
                "view_to_purchase_rate": overall_rate,
                "largest_loss_stage": "Product view to add to cart",
                "largest_loss_sessions": int(largest_loss["dropoff_sessions"]),
                "largest_loss_rate": float(largest_loss["dropoff_rate"]),
                "priority_channel": str(top_channel["segment_value"]),
                "priority_channel_rate": float(top_channel["view_to_purchase_rate"]),
                "priority_channel_scenario_purchases": int(top_channel["scenario_extra_purchases"]),
                "priority_category": str(top_category["product_category"]),
                "priority_category_scenario_purchases": int(top_category["scenario_extra_purchases"]),
                "recommendation": "Investigate product-detail and add-to-cart friction first, beginning with google / organic sessions and the YouTube and Bags category paths.",
            }
        ]
    )

    qa = {
        "status": "PASS",
        "analysis_window": {"start": "2020-11-25", "end": "2021-01-31", "days": 68},
        "checks": {
            "source_has_92_days": int(quality.loc[quality.metric == "source_days", "value"].iloc[0]) == 92,
            "identifiers_complete": int(quality.loc[quality.metric == "events_without_user", "value"].iloc[0]) == 0
            and int(quality.loc[quality.metric == "events_without_session_id", "value"].iloc[0]) == 0,
            "funnel_is_monotonic": funnel["sessions"].is_monotonic_decreasing,
            "headline_reconciles": int(funnel.iloc[-1]["sessions"]) == int(overall["purchase_sessions"]),
            "stable_window_starts_after_last_cart_gap": quality.loc[
                quality.metric == "last_missing_add_to_cart_date", "value"
            ].iloc[0]
            == "2020-11-24",
            "weekly_purchase_total_reconciles": int(weekly["purchase_sessions"].sum())
            == int(overall["purchase_sessions"]),
        },
        "ordered_path_exclusions": {
            "purchase_sessions_in_order": int(overall["purchase_sessions"]),
            "purchase_sessions_outside_ordered_path": int(overall["purchases_outside_ordered_path"]),
            "excluded_share": round(
                int(overall["purchases_outside_ordered_path"])
                / (int(overall["purchase_sessions"]) + int(overall["purchases_outside_ordered_path"])),
                4,
            ),
        },
        "caveats": [
            "The public dataset is obfuscated and contains <Other> and deleted acquisition values.",
            "traffic_source is first-user acquisition, not session attribution.",
            "Category opportunity is a transparent scenario, not a causal forecast.",
            "Category analysis stops at add_to_cart because later item-category fields are not comparable.",
        ],
    }
    if not all(qa["checks"].values()):
        qa["status"] = "FAIL"
        raise AssertionError(f"Data validation failed: {qa['checks']}")

    save_csv(funnel, "funnel.csv")
    save_csv(segment_detail, "segment_detail.csv")
    save_csv(categories, "category_opportunity.csv")
    save_csv(weekly, "weekly_funnel.csv")
    save_csv(weekly.loc[~weekly["partial_week"].astype(bool)].copy(), "weekly_funnel_complete.csv")
    save_csv(
        channel[
            [
                "segment_value",
                "view_sessions",
                "purchase_sessions",
                "view_to_purchase_rate",
                "scenario_extra_purchases",
            ]
        ].copy(),
        "channel_opportunity.csv",
    )
    save_csv(summary, "decision_summary.csv")
    shutil.copy2(SOURCE / "core_event_coverage.csv", POWERBI / "core_event_coverage.csv")

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "data_quality.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary.iloc[0].to_dict(), indent=2, ensure_ascii=False))
    print(f"QA: {qa['status']}")


if __name__ == "__main__":
    main()
