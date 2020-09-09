# -*- coding: utf-8 -*-
import json
import os
import re
from collections import defaultdict
from typing import List, Set
from requests_html import HTMLSession


HH_START_LINK = \
    "https://hh.ru/search/vacancy?search_field=name&text=data+engineer"

BASE_DIR = os.path.dirname(__file__)

HH_VACANCIES_JSON_PATH = os.path.join(BASE_DIR, "hh.json")

LANGUAGES_TXT_PATH = os.path.join(BASE_DIR, "languages.txt")


def collect_vacancy_urls(session: HTMLSession) -> List[str]:
    urls = []
    r = session.get(HH_START_LINK)
    while r:
        vacancy_blocks = r.html.find("div.vacancy-serp-item")
        for block in vacancy_blocks:
            el = block.find("a.bloko-link", first=True)
            urls.append(el.attrs["href"])
        pager_next_el = r.html.find("a[data-qa=pager-next]", first=True)
        if pager_next_el:
            next_url = "https://hh.ru{}".format(pager_next_el.attrs["href"])
            r = session.get(next_url)
        else:
            r = None
    return urls


def fetch_vacancy(session: HTMLSession, url: str) -> dict:
    vacancy = dict(
        url=url, company_title=None, company_name=None, company_location=None,
        salary=None, experience=None, employment_mode=None, text=None,
        skills=[])
    r = session.get(url)
    title_el = r.html.find("h1[data-qa=vacancy-title]", first=True)
    if title_el:
        vacancy["company_title"] = title_el.text
    company_name_el = r.html.find("a[data-qa=vacancy-company-name]", first=True)
    if company_name_el:
        vacancy["company_name"] = company_name_el.text
    company_location_el = r.html.find(
        "p[data-qa=vacancy-view-location]", first=True)
    if company_location_el:
        vacancy["company_location"] = company_location_el.text
    salary_el = r.html.find("p.vacancy-salary", first=True)
    if salary_el:
        vacancy["salary"] = salary_el.text
    experience_el = r.html.find("span[data-qa=vacancy-experience]", first=True)
    if experience_el:
        vacancy["experience"] = experience_el.text
    employment_mode_el = r.html.find(
        "p[data-qa=vacancy-view-employment-mode]", first=True)
    if employment_mode_el:
        vacancy["employment_mode"] = employment_mode_el.text
    vacancy_text_el = r.html.find(
        "div.vacancy-branded-user-content", first=True, clean=True)
    if not vacancy_text_el:
        vacancy_text_el = r.html.find(
            "div.vacancy-section", first=True, clean=True)
    if vacancy_text_el:
        vacancy["text"] = vacancy_text_el.text
    skill_els = r.html.find("span.bloko-tag__section")
    for skill_el in skill_els:
        vacancy["skills"].append(skill_el.text)
    return vacancy


def fetch_vacancies() -> List[dict]:
    session = HTMLSession()
    vacancies = list()
    urls = collect_vacancy_urls(session=session)
    print("Vacancies to fetch: {}".format(len(urls)))
    for url in urls:
        vacancies.append(fetch_vacancy(session=session, url=url))
    session.close()
    return vacancies


def save_vacancies(vacancies: List[dict]):
    with open(HH_VACANCIES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(vacancies, f)


def load_vacancies() -> List[dict]:
    with open(HH_VACANCIES_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_languages():
    with open(LANGUAGES_TXT_PATH, "r", encoding="utf-8") as f:
        return [x.strip() for x in f.readlines()]


def clean_word(word: str) -> str:
    cleaning = True
    punctuations = ("(", ")", ",", ";", ".", "?", "!", "-")
    while cleaning:
        cleaning = False
        for punctuation in punctuations:
            if word.startswith(punctuation):
                word = word[1:]
                cleaning = True
            if word.endswith(punctuation):
                word = word[:-1]
                cleaning = True
    return word.lower()


def extract_words(text: str) -> Set[str]:
    words = text.split()
    clean_words = set()
    for w in words:
        w = clean_word(w)
        if w:
            clean_words.update(w.split("/"))
    return clean_words


def analyze_languages(vacancies: List[dict]):
    vacancies_len = float(len(vacancies))
    languages = load_languages()
    languages_dict = {l: 0 for l in languages}
    for vacancy in vacancies:
        words = extract_words(text=vacancy["text"])
        for l in languages:
            if l in words:
                languages_dict[l] += 1
    print("## TOP 10 Languages")
    languages_tuple_list = [(l, count) for l, count in languages_dict.items()]
    languages_tuple_list.sort(key=lambda tup: tup[1], reverse=True)
    for i in range(1, 11):
        item = languages_tuple_list[i - 1]
        percentage = (float(item[1]) / vacancies_len) * 100
        print(f"{item[0]}: {item[1]} вакансий ({percentage:.2f}%)")


def analyze_technologies(vacancies: List[dict]) -> None:
    r = re.compile("[a-zA-Z]+")
    vacancies_len = float(len(vacancies))
    languages = load_languages()
    all_words_dict = defaultdict(int)
    for vacancy in vacancies:
        words = extract_words(text=vacancy["text"])
        # print(words)
        words = set([w for w in words if w not in languages])
        words = list(filter(r.match, words))
        for w in words:
            all_words_dict[w] += 1
    print("## TOP 20 Technologies")
    all_words_tuple_list = [(w, count) for w, count in all_words_dict.items()]
    # ¯\_( ͡❛ ͜ʖ ͡❛)_/¯ (because some vacancies have a lot of english words)
    # I am excluding some words manually
    word_to_exclude = (
        "data", "engineer", "big", "and", "apache", "a", "with", "of", "to",
        "the", "experience", "in", "team", "for", "science", "is", "work",
        "we", "on", "engineering", "working", "knowledge", "development",
        "our", "or", "be", "are", "skills", "an", "from", "software", "new",
        "have", "design", "code", "years", "pipelines", "that", "will", "api",
        "english", "services", "cloud", "processing", "solutions", )
    all_words_tuple_list = [
        x for x in all_words_tuple_list if x[0] not in word_to_exclude]
    all_words_tuple_list.sort(key=lambda tup: tup[1], reverse=True)
    for i in range(1, 21):
        item = all_words_tuple_list[i - 1]
        percentage = (float(item[1]) / vacancies_len) * 100
        print(f"{item[0]}: {item[1]} вакансий ({percentage:.2f}%)")


def analyze_vacancies(vacancies: List[dict]):
    print("Vacancies: {}".format(len(vacancies)))
    # analyze_languages(vacancies=vacancies)
    analyze_technologies(vacancies=vacancies)


def main():
    if os.path.isfile(HH_VACANCIES_JSON_PATH):
        # load from json
        vacancies = load_vacancies()
    else:
        # fetch vacancies
        vacancies = fetch_vacancies()
        # save to json
        save_vacancies(vacancies=vacancies)    
    # analyze vacancies
    analyze_vacancies(vacancies=vacancies)
    

if __name__ == "__main__":
    main()
