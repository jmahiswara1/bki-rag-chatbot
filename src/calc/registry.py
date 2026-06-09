from src.core.db import get_client
from src.core.models import Formula, Variable


def get_formula(code: str) -> Formula | None:
    # Load a curated, verified formula by code.
    client = get_client()
    resp = client.table("formulas").select("*").eq("code", code).limit(1).execute()
    if not resp.data:
        return None
    row = resp.data[0]
    variables = [Variable(**v) for v in row["variables"]]
    return Formula(
        code=row["code"],
        title=row["title"],
        section_no=row["section_no"],
        expression=row["expression"],
        variables=variables,
        paragraph_id=row.get("paragraph_id"),
        page_no=row.get("page_no"),
        result_unit=row.get("result_unit"),
        notes=row.get("notes"),
    )
