from models import Tutor

from time import sleep
from urllib.parse import urlencode
from urllib.request import urlopen
from dataclasses import dataclass, asdict
import json

from playwright.sync_api import sync_playwright
import cv2
import numpy as np
from deepface import DeepFace
from loguru import logger

def config_logging():
    logger.add("logs/app_{time}.log", serialize=True, mode="w")

config_logging()


def login(page, email, password):
    page.goto("https://preply.com/")

    page.click("text=Log in")
    sleep(2)
    login_input = page.locator("input[type='email']")
    login_input.fill(email)
    password_input = page.locator("input[type='password']")
    password_input.fill(password)

    submit_button = page.locator("button[type='submit']", has_text="Log in")
    submit_button.click()

    sleep(5)

def build_url(base_url, params):
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"



def fetch_image(url):
    with urlopen(url) as response:
        data = np.asarray(bytearray(response.read()), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def analyze_tutor_faces(tutors):
    for i, tutor in enumerate(tutors):
        if not tutor.avatar_url:
            tutor.face_detection_error = "no avatar"
            continue

        try:
            logger.info(f"Fetching avatar for tutor ({i+1}/{len(tutors)}) {tutor.name} (ID: {tutor.tutor_id})...")
            img = fetch_image(tutor.avatar_url)
            logger.info(f"Analyzing face for tutor ({i+1}/{len(tutors)}) {tutor.name} (ID: {tutor.tutor_id})...")
            results = DeepFace.analyze(img_path=img, actions=["gender"], enforce_detection=False, detector_backend="mtcnn")
            logger.info(f"Face analysis result for tutor ({i+1}/{len(tutors)}) {tutor.name} (ID: {tutor.tutor_id}): {results}")
            result = results[0] if isinstance(results, list) else results
            tutor.gender = result["dominant_gender"]
            tutor.gender_confidence = str(result["gender"][tutor.gender])
        except Exception as e:
            logger.error(f"Error analyzing face for tutor ({i+1}/{len(tutors)}) {tutor.name} (ID: {tutor.tutor_id}): {e}")
            tutor.face_detection_error = str(e)


def save_tutors_jsonl(tutors, path):
    with open(path, "a", encoding="utf-8") as f:
        for tutor in tutors:
            f.write(json.dumps(asdict(tutor), ensure_ascii=False) + "\n")

def read_last_tutor(path) -> Tutor | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                json_data = json.loads(last_line)
                return Tutor(**json_data)
    except FileNotFoundError:
        return None


def parse_tutor_card(card):
    def text_or_none(locator):
        return locator.inner_text().strip() if locator.count() else None

    return Tutor(
        tutor_id=card.get_attribute("data-qa-tutor-id"),
        profile_url=card.locator("a[data-qa-group='tutor-profile-url']").first.get_attribute("href"),
        name=text_or_none(card.locator(".styles_FullName__scSqc h4").first),
        price=text_or_none(card.locator("[data-qa-group='tutor-price-value']").first),
        rating=text_or_none(card.locator(".styles_reviewsButton__SfuGT h5").first),
        reviews=text_or_none(card.locator(".styles_reviewsButton__SfuGT p").first),
        subjects=[s.strip() for s in card.locator(".styles_SubjectItem__xmPqR").all_inner_texts()],
        speaks=text_or_none(card.locator(".styles_SpeaksList__Rlshm").first),
        description=text_or_none(card.locator("[data-seo-snippet='true']").first),
        avatar_url=card.locator("a[data-qa-group='tutor-profile-url']").first.locator("img").first.get_attribute("src"),
    )

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    # save session and cookies to a file
    context = browser.new_context(storage_state="data/storage.json")

    page = context.new_page()

    # check are we logged in or not
    page.goto("https://preply.com/")

    if page.locator("text=Log in").is_visible():
        login(page, "wokima6417@lovadio.com", "wokima6417@lovadio.comMark")
        logger.info("Logged in successfully.")
        context.storage_state(path="data/storage.json")


    # go to seach page
    search_params = {
        "taxonomySlug": "english",
        "priceRange": "15-25",
        "cf": "1",
        "additional": "native",
        "CoB": "US",
        "page": 1
    }

    last_tutor = read_last_tutor("data/tutors.jsonl")
    max_page = 233
    start_page = 1

    if last_tutor:
        logger.info(f"Last tutor parsed: {last_tutor.name} (ID: {last_tutor.tutor_id}) on page {last_tutor.parsed_on_page}")
        search_params["page"] = last_tutor.parsed_on_page
        start_page = last_tutor.parsed_on_page + 1
 

    for page_number in range(start_page, max_page + 1):
        logger.info(f"Parsing tutors on page {page_number}...")
        search_params["page"] = page_number

        search_url = build_url("https://preply.com/en/online/english-tutors", search_params)
        page.goto(search_url)

        tutor_cards = page.locator("section[data-qa-group='tutor-profile']")
        tutors = [parse_tutor_card(tutor_cards.nth(i)) for i in range(tutor_cards.count())]
        for tutor in tutors:
            tutor.parsed_on_page = page_number

        logger.info(f"Parsed {len(tutors)} tutors on page {page_number}.")

        analyze_tutor_faces(tutors)

        logger.info(f"Analyzed faces for {len(tutors)} tutors on page {page_number}.")

        save_tutors_jsonl(tutors, "data/tutors.jsonl")


    browser.close()
