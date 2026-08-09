from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "powerbi" / "project"
MODEL = PROJECT / "GA4ProductFunnel.SemanticModel"
REPORT = PROJECT / "GA4ProductFunnel.Report"
DATA = ROOT / "data" / "powerbi"


def main() -> None:
    checks: dict[str, bool] = {}

    json_files = list(PROJECT.rglob("*.json")) + list(PROJECT.rglob("*.pbip")) + list(PROJECT.rglob("*.pbir")) + list(PROJECT.rglob("*.pbism"))
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    checks["all_project_json_valid"] = bool(json_files)

    tmdl_files = list(MODEL.rglob("*.tmdl"))
    checks["tmdl_has_no_utf8_bom"] = all(not path.read_bytes().startswith(b"\xef\xbb\xbf") for path in tmdl_files)
    model_text = (MODEL / "definition" / "model.tmdl").read_text(encoding="utf-8")
    match = re.search(r'expression DataFolder = "([^"]+)"', model_text)
    data_folder = match.group(1) if match else ""
    portable_placeholder = data_folder.lower().startswith("c:\\path\\to\\") and data_folder.lower().endswith("\\data\\powerbi")
    checks["data_folder_parameter_is_valid"] = bool(match and (Path(data_folder).is_dir() or portable_placeholder))

    table_files = list((MODEL / "definition" / "tables").glob("*.tmdl"))
    referenced_csv = []
    for path in table_files:
        referenced_csv += re.findall(r'& "\\([^\"]+\.csv)"', path.read_text(encoding="utf-8"))
    checks["all_model_csv_files_exist"] = bool(referenced_csv) and all((DATA / name).is_file() for name in referenced_csv)

    funnel = pd.read_csv(DATA / "funnel.csv")
    summary = pd.read_csv(DATA / "decision_summary.csv").iloc[0]
    weekly = pd.read_csv(DATA / "weekly_funnel_complete.csv")
    checks["funnel_is_monotonic"] = funnel.sessions.is_monotonic_decreasing
    checks["funnel_reconciles_to_summary"] = int(funnel.iloc[-1].sessions) == int(summary.purchase_sessions)
    checks["complete_weeks_only"] = not weekly.partial_week.astype(bool).any()

    pages = json.loads((REPORT / "definition" / "pages" / "pages.json").read_text(encoding="utf-8"))
    checks["two_pages"] = len(pages["pageOrder"]) == 2
    visual_types = []
    for path in REPORT.rglob("visual.json"):
        visual_types.append(json.loads(path.read_text(encoding="utf-8"))["visual"]["visualType"])
    checks["cards_present"] = visual_types.count("card") >= 8
    checks["funnel_and_trend_charts_present"] = "clusteredBarChart" in visual_types and "lineChart" in visual_types

    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps(checks, indent=2))
    if failed:
        raise AssertionError(f"Validation failed: {failed}")
    print("Power BI project validation: PASS")


if __name__ == "__main__":
    main()
