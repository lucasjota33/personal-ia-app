import json
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


def extract_json_from_ai(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def extract_tables_from_markdown(text: str) -> List[Tuple[str, pd.DataFrame]]:
    tables: List[Tuple[str, pd.DataFrame]] = []
    lines = text.split("\n")
    current_table: List[str] = []
    current_title = ""
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            current_table.append(stripped)
            in_table = True
        else:
            if in_table and current_table:
                table_frame = _parse_markdown_table(current_title, current_table)
                if table_frame is not None:
                    tables.append((current_title, table_frame))
                current_table = []
                in_table = False
            cleaned_title = re.sub(r'^#+\s*', '', stripped).strip()
            if cleaned_title and not cleaned_title.startswith(("|", "-", "* ", "•")):
                current_title = cleaned_title

    if in_table and current_table:
        table_frame = _parse_markdown_table(current_title, current_table)
        if table_frame is not None:
            tables.append((current_title, table_frame))

    return tables


def _parse_markdown_table(title: str, rows: List[str]) -> Optional[pd.DataFrame]:
    if len(rows) < 2:
        return None
    header = [cell.strip() for cell in rows[0].strip("|").split("|")]
    data_rows = []
    for row in rows[1:]:
        if re.match(r'^[\s\|\-\:]+$', row):
            continue
        values = [cell.strip() for cell in row.strip("|").split("|")]
        if len(values) < len(header):
            values.extend([""] * (len(header) - len(values)))
        elif len(values) > len(header):
            values = values[: len(header)]
        data_rows.append(values)
    if not data_rows:
        return None
    df = pd.DataFrame(data_rows, columns=header)
    return df
