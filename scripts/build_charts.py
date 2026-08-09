from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "charts"
INK = "#172B4D"
TEXT = "#52606D"
BLUE = "#2F6B9A"
ORANGE = "#D9892B"
GREEN = "#287D5A"
GRID = "#D9E2EC"
BG = "#F7F9FC"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 48), title, fill=INK, font=font(36, True))
    draw.text((70, 100), subtitle, fill=TEXT, font=font(20))
    return image, draw


def funnel_chart() -> None:
    data = pd.read_csv(DATA / "funnel.csv")
    image, draw = canvas(
        "The largest loss occurs before add to cart",
        "Ordered sessions, 25 Nov 2020–31 Jan 2021",
    )
    max_value = data["sessions"].max()
    x0, max_width = 330, 1080
    for index, row in data.iterrows():
        y = 210 + index * 145
        width = int(max_width * row["sessions"] / max_value)
        color = ORANGE if index == 1 else BLUE
        draw.text((70, y + 18), row["stage"], fill=INK, font=font(23, True))
        draw.rounded_rectangle((x0, y, x0 + width, y + 72), radius=10, fill=color)
        if width >= 150:
            draw.text((x0 + 18, y + 17), f"{int(row['sessions']):,}", fill="white", font=font(25, True))
            conversion_x = x0 + width + 22
        else:
            draw.text((x0 + width + 18, y + 17), f"{int(row['sessions']):,}", fill=INK, font=font(25, True))
            conversion_x = x0 + width + 125
        if index:
            draw.text(
                (conversion_x, y + 17),
                f"{row['step_conversion_rate']:.1%} from prior step",
                fill=TEXT,
                font=font(18),
            )
    draw.rounded_rectangle((70, 790, 1530, 850), radius=10, fill="#FFF3E5")
    draw.text(
        (95, 805),
        "42,078 sessions (74.2%) are lost between product view and add to cart.",
        fill=INK,
        font=font(22, True),
    )
    image.save(OUT / "ordered_funnel.png")


def opportunity_chart() -> None:
    data = pd.read_csv(DATA / "segment_detail.csv")
    data = data.loc[
        (data["segment_type"] == "First-user acquisition channel") & data["actionable"]
    ].sort_values("scenario_extra_purchases", ascending=True)
    image, draw = canvas(
        "Google organic is the largest actionable channel gap",
        "Scenario: additional purchases if each channel reached the 4.71% overall rate",
    )
    max_value = max(data["scenario_extra_purchases"].max(), 1)
    bar_x, max_width = 620, 650
    for index, (_, row) in enumerate(data.iterrows()):
        y = 230 + index * 150
        width = int(max_width * row["scenario_extra_purchases"] / max_value)
        draw.text((70, y + 6), row["segment_value"], fill=INK, font=font(22, True))
        draw.text(
            (70, y + 46),
            f"Observed conversion: {row['view_to_purchase_rate']:.2%} | Viewed sessions: {int(row['view_sessions']):,}",
            fill=TEXT,
            font=font(17),
        )
        draw.rounded_rectangle((bar_x, y + 8, bar_x + width, y + 64), radius=8, fill=ORANGE)
        draw.text(
            (bar_x + width + 18, y + 20),
            f"{int(row['scenario_extra_purchases'])} scenario purchases",
            fill=TEXT,
            font=font(19),
        )
    draw.text(
        (70, 800),
        "This prioritizes investigation; it does not claim the channel caused the lower conversion.",
        fill=TEXT,
        font=font(19),
    )
    image.save(OUT / "channel_opportunity.png")


def weekly_chart() -> None:
    data = pd.read_csv(DATA / "weekly_funnel.csv", parse_dates=["week_start"])
    complete = data.loc[~data["partial_week"].astype(bool)].reset_index(drop=True)
    image, draw = canvas(
        "Purchase conversion peaked in early December, then weakened",
        "Complete weeks only; the pattern is descriptive, not causal",
    )
    left, top, right, bottom = 120, 210, 1500, 740
    for tick in range(0, 8):
        rate = tick / 100
        y = bottom - int((rate / 0.08) * (bottom - top))
        draw.line((left, y, right, y), fill=GRID, width=1)
        draw.text((55, y - 12), f"{rate:.0%}", fill=TEXT, font=font(16))
    points = []
    for index, row in complete.iterrows():
        x = left + int(index * (right - left) / max(len(complete) - 1, 1))
        y = bottom - int(row["view_to_purchase_rate"] / 0.08 * (bottom - top))
        points.append((x, y))
        draw.text((x - 42, bottom + 24), row["week_start"].strftime("%d %b"), fill=TEXT, font=font(15))
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=BLUE)
    draw.line(points, fill=BLUE, width=5)
    peak = complete.loc[complete["view_to_purchase_rate"].idxmax()]
    draw.rounded_rectangle((990, 115, 1515, 175), radius=10, fill="#EAF2F8")
    draw.text(
        (1015, 130),
        f"Peak complete week: {peak['view_to_purchase_rate']:.2%}",
        fill=INK,
        font=font(20, True),
    )
    image.save(OUT / "weekly_conversion.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    funnel_chart()
    opportunity_chart()
    weekly_chart()
    print(f"Charts: {OUT}")


if __name__ == "__main__":
    main()
