from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "powerbi" / "project"
REPORT = PROJECT / "GA4ProductFunnel.Report"
MODEL = PROJECT / "GA4ProductFunnel.SemanticModel"
PAGES = REPORT / "definition" / "pages"

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
INK, TEXT, BLUE, ORANGE, GREEN = "#172B4D", "#52606D", "#2F6B9A", "#D9892B", "#287D5A"
BORDER, BACKGROUND = "#D9E2EC", "#F5F7FA"

TABLES = {
    "decision_summary": {
        "file": "decision_summary.csv",
        "columns": {
            "analysis_start": "dateTime", "analysis_end": "dateTime", "view_sessions": "int64",
            "purchase_sessions": "int64", "view_to_purchase_rate": "double", "largest_loss_stage": "string",
            "largest_loss_sessions": "int64", "largest_loss_rate": "double", "priority_channel": "string",
            "priority_channel_rate": "double", "priority_channel_scenario_purchases": "int64",
            "priority_category": "string", "priority_category_scenario_purchases": "int64", "recommendation": "string",
        },
        "formats": {"view_to_purchase_rate": "0.0%", "largest_loss_rate": "0.0%", "priority_channel_rate": "0.0%"},
        "measures": {
            "Viewed sessions": ("MAX(decision_summary[view_sessions])", "#,##0"),
            "Purchased sessions": ("MAX(decision_summary[purchase_sessions])", "#,##0"),
            "Purchase conversion": ("MAX(decision_summary[view_to_purchase_rate])", "0.0%"),
            "Lost before cart": ("MAX(decision_summary[largest_loss_sessions])", "#,##0"),
            "Loss before cart rate": ("MAX(decision_summary[largest_loss_rate])", "0.0%"),
            "Channel scenario purchases": ("MAX(decision_summary[priority_channel_scenario_purchases])", "#,##0"),
            "Category scenario purchases": ("MAX(decision_summary[priority_category_scenario_purchases])", "#,##0"),
        },
    },
    "funnel": {
        "file": "funnel.csv",
        "columns": {"stage_order": "int64", "stage": "string", "sessions": "int64", "step_conversion_rate": "double", "dropoff_sessions": "int64", "dropoff_rate": "double"},
        "formats": {"step_conversion_rate": "0.0%", "dropoff_rate": "0.0%"},
        "measures": {"Stage sessions": ("SUM(funnel[sessions])", "#,##0")},
    },
    "weekly_funnel_complete": {
        "file": "weekly_funnel_complete.csv",
        "columns": {"week_start": "dateTime", "view_sessions": "int64", "cart_sessions": "int64", "checkout_sessions": "int64", "purchase_sessions": "int64", "view_to_purchase_rate": "double", "partial_week": "boolean"},
        "formats": {"view_to_purchase_rate": "0.0%"},
        "measures": {"Weekly purchase conversion": ("AVERAGE(weekly_funnel_complete[view_to_purchase_rate])", "0.0%")},
    },
    "channel_opportunity": {
        "file": "channel_opportunity.csv",
        "columns": {"segment_value": "string", "view_sessions": "int64", "purchase_sessions": "int64", "view_to_purchase_rate": "double", "scenario_extra_purchases": "int64"},
        "formats": {"view_to_purchase_rate": "0.0%"},
        "measures": {"Channel scenario opportunity": ("SUM(channel_opportunity[scenario_extra_purchases])", "#,##0")},
    },
    "category_opportunity": {
        "file": "category_opportunity.csv",
        "columns": {"product_category": "string", "view_sessions": "int64", "cart_sessions": "int64", "view_to_cart_rate": "double", "overall_benchmark_rate": "double", "scenario_extra_carts": "int64", "scenario_extra_purchases": "int64"},
        "formats": {"view_to_cart_rate": "0.0%", "overall_benchmark_rate": "0.0%"},
        "measures": {"Category scenario opportunity": ("SUM(category_opportunity[scenario_extra_purchases])", "#,##0")},
    },
}


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False))


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def position(x: int, y: int, width: int, height: int, z: int) -> dict:
    return {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z}


def field(table: str, name: str, kind: str = "column") -> dict:
    key = "Measure" if kind == "measure" else "Column"
    return {key: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def projection(table: str, name: str, kind: str = "column", label: str | None = None) -> dict:
    return {"field": field(table, name, kind), "queryRef": f"{table}.{name}", "nativeQueryRef": label or name.replace("_", " ").title()}


def style(title: str) -> dict:
    return {
        "title": [{"properties": {"show": literal("true"), "text": literal(f"'{title}'"), "fontSize": literal("14D"), "fontColor": {"solid": {"color": literal(f"'{TEXT}'")}}}}],
        "background": [{"properties": {"show": literal("true"), "color": {"solid": {"color": literal("'#FFFFFF'")}}, "transparency": literal("0D")}}],
        "border": [{"properties": {"show": literal("true"), "color": {"solid": {"color": literal(f"'{BORDER}'")}}, "radius": literal("8D")}}],
        "visualHeader": [{"properties": {"show": literal("false")}}],
    }


def textbox(name: str, x: int, y: int, width: int, height: int, text: str, size: int = 26, bold: bool = True, color: str = INK) -> dict:
    return {"$schema": SCHEMA_VISUAL, "name": name, "position": position(x, y, width, height, 100), "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": {"fontFamily": "Segoe UI", "fontSize": f"{size}px", "fontWeight": "bold" if bold else "normal", "color": color}}]}]}}]}, "visualContainerObjects": {"background": [{"properties": {"show": literal("false")}}], "border": [{"properties": {"show": literal("false")}}]}}}


def card(name: str, x: int, y: int, width: int, table: str, measure: str, title: str, z: int) -> dict:
    return {"$schema": SCHEMA_VISUAL, "name": name, "position": position(x, y, width, 140, z), "visual": {"visualType": "card", "query": {"queryState": {"Values": {"projections": [projection(table, measure, "measure")]}}}, "visualContainerObjects": style(title)}}


def chart(name: str, chart_type: str, x: int, y: int, width: int, height: int, category: tuple[str, str], measure: tuple[str, str], title: str, color: str, z: int) -> dict:
    return {"$schema": SCHEMA_VISUAL, "name": name, "position": position(x, y, width, height, z), "visual": {"visualType": chart_type, "query": {"queryState": {"Category": {"projections": [projection(category[0], category[1])]}, "Y": {"projections": [projection(measure[0], measure[1], "measure")]}}}, "objects": {"categoryAxis": [{"properties": {"show": literal("true"), "fontSize": literal("10D")}}], "valueAxis": [{"properties": {"show": literal("true"), "start": literal("0D"), "gridlineStyle": literal("'dotted'"), "gridlineColor": {"solid": {"color": literal("'#E5E7EB'")}}}}], "labels": [{"properties": {"show": literal("true"), "labelDisplayUnits": literal("1D")}}], "dataPoint": [{"properties": {"fill": {"solid": {"color": literal(f"'{color}'")}}}}], "lineStyles": [{"properties": {"strokeWidth": literal("3D")}}]}, "visualContainerObjects": style(title)}}


def table_visual(name: str, x: int, y: int, width: int, height: int, fields: list[tuple[str, str]], title: str, z: int) -> dict:
    return {"$schema": SCHEMA_VISUAL, "name": name, "position": position(x, y, width, height, z), "visual": {"visualType": "tableEx", "query": {"queryState": {"Values": {"projections": [projection(table, column) for table, column in fields]}}}, "objects": {"columnHeaders": [{"properties": {"autoSizeColumnWidth": literal("true"), "backColor": {"solid": {"color": literal("'#EAF2F8'")}}}}], "total": [{"properties": {"totals": literal("false")}}]}, "visualContainerObjects": style(title)}}


def tmdl_table(name: str, spec: dict) -> str:
    lines = [f"table {name}", ""]
    for measure, (expression, fmt) in spec["measures"].items():
        lines += [f"\tmeasure '{measure}' = {expression}", f"\t\tformatString: {fmt}", ""]
    for column, dtype in spec["columns"].items():
        col = f"'{column}'" if " " in column else column
        lines += [f"\tcolumn {col}", f"\t\tdataType: {dtype}"]
        if column in spec["formats"]:
            lines.append(f"\t\tformatString: {spec['formats'][column]}")
        lines += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {column}", ""]
    types = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date", "boolean": "type logical"}
    typed = ", ".join(f'{{"{column}", {types[dtype]}}}' for column, dtype in spec["columns"].items())
    lines += [f"\tpartition {name} = m", "\t\tmode: import", "\t\tsource =", "\t\t\tlet", f'\t\t\t\tSource = Csv.Document(File.Contents(#"DataFolder" & "\\{spec["file"]}"), [Delimiter=",", Columns={len(spec["columns"])}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),', "\t\t\t\tHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),", f'\t\t\t\tTyped = Table.TransformColumnTypes(Headers, {{{typed}}}, "en-US")', "\t\t\tin", "\t\t\t\tTyped", ""]
    return "\n".join(lines)


def page(name: str, display_name: str, visuals: list[dict]) -> None:
    page_dir = PAGES / name
    write_json(page_dir / "page.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json", "name": name, "displayName": display_name, "displayOption": "FitToPage", "height": 1080, "width": 1920, "objects": {"background": [{"properties": {"color": {"solid": {"color": literal(f"'{BACKGROUND}'")}}, "transparency": literal("0D")}}]}})
    for visual in visuals:
        write_json(page_dir / "visuals" / visual["name"] / "visual.json", visual)


def build(data_folder: Path) -> None:
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    definition = MODEL / "definition"
    refs = "\n".join(f"ref table {name}" for name in TABLES)
    write_text(definition / "model.tmdl", f'model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n\tdiscourageImplicitMeasures\n\nexpression DataFolder = "{data_folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\n{refs}\n')
    write_text(definition / "database.tmdl", "database GA4ProductFunnel\n\tcompatibilityLevel: 1702\n\tcompatibilityMode: powerBI\n\tlanguage: 1033\n")
    for name, spec in TABLES.items():
        write_text(definition / "tables" / f"{name}.tmdl", tmdl_table(name, spec))
    write_json(MODEL / "definition.pbism", {"version": "4.2", "settings": {"qnaEnabled": True}})
    write_json(MODEL / "diagramLayout.json", {"version": "1.1.0", "diagrams": []})
    write_json(PROJECT / "GA4ProductFunnel.pbip", {"version": "1.0", "artifacts": [{"report": {"path": "GA4ProductFunnel.Report"}}], "settings": {"enableAutoRecovery": True}})
    write_json(REPORT / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../GA4ProductFunnel.SemanticModel"}}})
    write_json(REPORT / "definition" / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write_json(REPORT / "definition" / "report.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json", "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "2.1.0", "report": "3.0.0", "page": "2.0.0"}, "type": "SharedResources"}}, "settings": {"useEnhancedTooltips": True}})
    page1, page2 = "01funneldecision00000", "02segmentpriority0000"
    write_json(PAGES / "pages.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": [page1, page2], "activePageName": page1})

    page(page1, "Funnel decision", [
        textbox("p1title", 40, 24, 1780, 60, "Where does the ecommerce funnel lose users?"),
        card("p1views", 40, 112, 440, "decision_summary", "Viewed sessions", "Viewed product sessions", 200),
        card("p1purchases", 500, 112, 440, "decision_summary", "Purchased sessions", "Ordered purchases", 210),
        card("p1rate", 960, 112, 440, "decision_summary", "Purchase conversion", "View-to-purchase conversion", 220),
        card("p1loss", 1420, 112, 460, "decision_summary", "Lost before cart", "Lost before add to cart", 230),
        chart("p1funnel", "clusteredBarChart", 40, 290, 900, 440, ("funnel", "stage"), ("funnel", "Stage sessions"), "Ordered session funnel", BLUE, 300),
        chart("p1weekly", "lineChart", 980, 290, 900, 440, ("weekly_funnel_complete", "week_start"), ("weekly_funnel_complete", "Weekly purchase conversion"), "Weekly purchase conversion (complete weeks)", ORANGE, 310),
        textbox("p1finding", 60, 770, 1760, 95, "Primary finding: 42,078 sessions (74.2%) are lost between product view and add to cart.", 24, True, ORANGE),
        textbox("p1action", 60, 890, 1760, 120, "Investigate product-page and add-to-cart friction first. Add stock, price, CTA exposure, error, and load-time diagnostics before choosing an A/B test.", 21, False, GREEN),
    ])
    page(page2, "Segment priorities", [
        textbox("p2title", 40, 24, 1780, 60, "Which segments should the product team investigate first?"),
        card("p2channel", 40, 112, 440, "decision_summary", "Channel scenario purchases", "Google organic scenario gap", 200),
        card("p2category", 500, 112, 440, "decision_summary", "Category scenario purchases", "YouTube category scenario gap", 210),
        card("p2overall", 960, 112, 440, "decision_summary", "Purchase conversion", "Overall benchmark", 220),
        card("p2lossrate", 1420, 112, 460, "decision_summary", "Loss before cart rate", "Loss before add to cart", 230),
        chart("p2channels", "clusteredBarChart", 40, 290, 900, 360, ("channel_opportunity", "segment_value"), ("channel_opportunity", "Channel scenario opportunity"), "Actionable first-user channel opportunity", ORANGE, 300),
        chart("p2categories", "clusteredBarChart", 980, 290, 900, 360, ("category_opportunity", "product_category"), ("category_opportunity", "Category scenario opportunity"), "Product-category opportunity", BLUE, 310),
        table_visual("p2table", 40, 680, 1180, 300, [("category_opportunity", "product_category"), ("category_opportunity", "view_sessions"), ("category_opportunity", "view_to_cart_rate"), ("category_opportunity", "overall_benchmark_rate"), ("category_opportunity", "scenario_extra_purchases")], "Category evidence", 320),
        textbox("p2note", 1260, 700, 580, 250, "Start with Google organic because it combines high volume with below-benchmark conversion. Within product paths, review YouTube and Bags categories first. Device rates are similar, so device is not the primary lead.", 18, False),
        textbox("p2caveat", 60, 1005, 1760, 50, "Scenario estimates prioritize investigation; the obfuscated observational sample does not prove causality.", 15, False, TEXT),
    ])
    print(PROJECT / "GA4ProductFunnel.pbip")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-folder", type=Path, default=ROOT / "data" / "powerbi")
    args = parser.parse_args()
    build(args.data_folder.resolve())
