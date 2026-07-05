from dataclasses import dataclass

@dataclass
class Tutor:
    tutor_id: str
    profile_url: str
    name: str
    price: str
    rating: str
    reviews: str
    subjects: list[str]
    speaks: str
    description: str
    avatar_url: str
    parsed_on_page: int | None = None
    gender: str | None = None
    gender_confidence: float | None = None
    face_detection_error: str | None = None
