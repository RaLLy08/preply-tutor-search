from src.models import Tutor
from src.utils import from_pd_row

import os
from time import sleep
from urllib.parse import urlencode
from urllib.request import urlopen
from dataclasses import dataclass, asdict

import pandas as pd

from playwright.sync_api import sync_playwright

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


def build_url(base_url, params):
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"


def append_tutors_to_csv_if_exist(tutors, path):
    existing_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    new_df = pd.DataFrame([asdict(tutor) for tutor in tutors])

    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(path, index=False)



def read_last_tutor(path) -> Tutor | None:
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)
    if df.empty:
        return None

    last_row = df.iloc[-1]
    return from_pd_row(last_row)




def parse_tutors_from_page(page):
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


    tutor_cards = page.locator("section[data-qa-group='tutor-profile']")
    tutors = [parse_tutor_card(tutor_cards.nth(i)) for i in range(tutor_cards.count())]
    return tutors


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

    last_tutor = read_last_tutor("data/tutors.csv")
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

        tutors = parse_tutors_from_page(page)
        
        for tutor in tutors:
            tutor.parsed_on_page = page_number

        logger.info(f"Parsed {len(tutors)} tutors on page {page_number}.")

        logger.info(f"Analyzed faces for {len(tutors)} tutors on page {page_number}.")

        append_tutors_to_csv_if_exist(tutors, "data/tutors.csv")


    browser.close()

