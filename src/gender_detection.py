from src.models import Tutor
from src.utils import from_pd_row
from typing import Optional

from urllib.request import urlopen
from dataclasses import dataclass, asdict

from loguru import logger
import cv2
import numpy as np
from deepface import DeepFace
import pandas as pd


def fetch_image(url):
    with urlopen(url) as response:
        data = np.asarray(bytearray(response.read()), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

@dataclass
class GenderDetectionResult:
    face_detection_error: Optional[str] = None
    gender: Optional[str] = None
    gender_confidence: Optional[str] = None

def predict_tutor_gender(tutor: Tutor) -> GenderDetectionResult:
    gender_detection_result = GenderDetectionResult()

    if not tutor.avatar_url:
        gender_detection_result.face_detection_error = "no avatar"
        return gender_detection_result

    try:
        logger.info(f"Fetching image for tutor {tutor.name} (ID: {tutor.tutor_id}) from URL: {tutor.avatar_url}")
        img = fetch_image(tutor.avatar_url)
        logger.info(f"Image fetched successfully for tutor {tutor.name} (ID: {tutor.tutor_id})")
        results = DeepFace.analyze(img_path=img, actions=["gender"], enforce_detection=False, detector_backend="mtcnn")
        logger.info(f"Gender detection results for tutor {tutor.name} (ID: {tutor.tutor_id}): {results}")
        result = results[0] if isinstance(results, list) else results
     
        gender_detection_result.gender = result["dominant_gender"]
        gender_detection_result.gender_confidence = str(result["gender"][gender_detection_result.gender])

    except Exception as e:
        # logger.error(f"Error analyzing face for tutor ({i+1}/{len(tutors)}) {tutor.name} (ID: {tutor.tutor_id}): {e}")
        gender_detection_result.face_detection_error = str(e)
    logger.info(f"Gender Result for tutor {gender_detection_result}")
    return gender_detection_result


df = pd.read_csv("data/tutors.csv")

for index, row in df.iterrows():
    logger.info(f"Processing tutor {index + 1}/{len(df)}")
    tutor = from_pd_row(row)
    gender_result = predict_tutor_gender(tutor)
    
    df.at[index, "gender"] = gender_result.gender
    df.at[index, "gender_confidence"] = gender_result.gender_confidence

df.to_csv("data/tutors.csv", index=False)