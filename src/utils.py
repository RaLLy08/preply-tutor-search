from src.models import Tutor

import pandas as pd

def from_pd_row(row: pd.Series) -> Tutor:
    return Tutor(
        tutor_id=row["tutor_id"],
        profile_url=row["profile_url"],
        name=row["name"],
        price=row["price"],
        rating=row["rating"],
        reviews=row["reviews"],
        subjects=row["subjects"].split(",") if pd.notna(row["subjects"]) else [],
        speaks=row["speaks"],
        description=row["description"],
        avatar_url=row["avatar_url"],
        parsed_on_page=row["parsed_on_page"]
    )
