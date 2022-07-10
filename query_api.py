import hashlib
import json
import requests

with open(".env") as f:
    API_KEY = f.read().strip()

SAT_CUTOFF = 1300
SALARY_CUTOFF = 60000
ENDPOINT = f"https://api.data.gov/ed/collegescorecard/v1/schools?api_key={API_KEY}&per_page=50"
KEY_MAPPING = {
    "school.name": "Name",
    "school.school_url": "Website",
    "latest.admissions.admission_rate.consumer_rate": "Admission Rate",
    # "latest.completion.consumer_rate": "Graduation Rate",
    "latest.earnings.6_yrs_after_entry.median": "6-year Median Salary",
    "latest.academics.program_percentage.computer": "CS Degree %",

    "latest.student.size": "Undergrad Size",
    "latest.cost.tuition.in_state": "In-state Tuition",
    "latest.cost.tuition.out_of_state": "Out-of-state Tuition",

    "school.city": "City",
    "school.state": "State",
    "school.locale": "Setting",

    "latest.admissions.sat_scores.25th_percentile.critical_reading": "SAT 25th % Critical Reading",
    "latest.admissions.sat_scores.75th_percentile.critical_reading": "SAT 75th % Critical Reading",
    "latest.admissions.sat_scores.25th_percentile.math": "SAT 25th % Math",
    "latest.admissions.sat_scores.75th_percentile.math": "SAT 75th % Math",
    "latest.admissions.sat_scores.25th_percentile.writing": "SAT 25th % Writing",
    "latest.admissions.sat_scores.75th_percentile.writing": "SAT 75th % Writing",
    "latest.admissions.sat_scores.average.overall": "SAT Average",
}


def make_request(query: str) -> dict:
    url = f"{ENDPOINT}&{query}"
    resp = requests.get(url)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "error" not in data, data["error"]
    return data


def make_query(filters: dict[str,], fields: list = None) -> list[dict]:
    filters_str = '&'.join([f"{k}={v}" for k, v in filters.items()])
    fields_str = f"fields={','.join(fields)}" if fields else ""
    query = f"{filters_str}&{fields_str}"
    query_hash = hashlib.sha1(query.encode()).hexdigest()  # use hash since query string is too long

    try:
        with open(f"cache/{query_hash}.json") as f:
            return json.loads(f.read().strip())
    except FileNotFoundError:
        pass

    data = make_request(query)
    metadata = data["metadata"]
    total, per_page = metadata["total"], metadata["per_page"]

    all_results = []  # makes a repeat request, but should be okay
    for page in range((total + per_page - 1) // per_page):
        print(f"Fetching page {page}")
        data = make_request(f"{query}&page={page}")
        results = data["results"]
        all_results.extend(results)

    with open(f"cache/{query_hash}.json", "w+") as f:
        f.write(json.dumps(all_results))
    return all_results


def translate_locale_value(locale: int) -> str:
    locale = (locale // 10) - 1
    return ["city", "suburb", "town", "rural"][locale]


def get_school_list(filters: dict[str,]) -> list[dict[str,]]:
    return make_query(
        filters,
        [
            "school.name",
            "school.city", "school.state",
            "school.school_url",
            "school.type",
            "school.locale",
            "school.online_only", "school.main_campus",

            "latest.cost.tuition.in_state", "latest.cost.tuition.out_of_state",

            "latest.student.size",

            "latest.earnings.6_yrs_after_entry.median",
            # "latest.earnings.7_yrs_after_entry.mean_earnings",
            # "latest.earnings.8_yrs_after_entry.mean_earnings", "latest.earnings.8_yrs_after_entry.median_earnings",
            # "latest.earnings.9_yrs_after_entry.mean_earnings", "latest.earnings.10_yrs_after_entry.median",

            # "latest.completion.consumer_rate",
            # "latest.completion.title_iv.completed_by.4yrs", "latest.completion.title_iv.completed_by.6yrs",

            "latest.admissions.test_requirements",
            "latest.admissions.admission_rate.consumer_rate",
            "latest.admissions.sat_scores",  # only took the SAT, so that's all I care about

            "latest.academics.program.degree.computer",
            "latest.academics.program_percentage.computer",

            # "latest.programs.cip_4_digit"  # Stanford's CS is 1107
        ]
    )


def filter_schools(schools: list[dict[str,]]) -> list[dict[str,]]:
    # API can't filter based on these values
    filtered_schools = []
    for school in schools:  # could be done with a list comprehension, but using loops allows for printing stuff out
        if school["latest.academics.program_percentage.computer"] == 0:
            # print(f"Filtered {school['school.name']}.".ljust(70, '.') + " no Bachelors program for CS")
            continue

        if school["school.online_only"] == 1:
            # print(f"Filtered {school['school.name']}.".ljust(70, '.') + " online only")
            continue
        if school["school.main_campus"] == 0:
            # print(f"Filtered {school['school.name']}.".ljust(70, '.') + " not main campus")
            continue

        median_earnings_6_yrs = school["latest.earnings.6_yrs_after_entry.median"]
        if median_earnings_6_yrs is None:
            # print(f"Filtered {school['school.name']}.".ljust(70, '.') + " no median earnings data")
            continue
        if median_earnings_6_yrs < SALARY_CUTOFF:
            # print(
            #     f"Filtered {school['school.name']}.".ljust(70, '.') +
            #     f" median earnings 6 years after entry (${median_earnings_6_yrs}) is < ${SALARY_CUTOFF}")
            continue

        sat_score = school["latest.admissions.sat_scores.average.overall"]
        if sat_score is not None and sat_score < SAT_CUTOFF:
            # print(f"Filtered {school['school.name']}.".ljust(70, '.') + f" SAT average ({sat_score}) is < {SAT_CUTOFF}")
            continue

        filtered_schools.append(school)
    return filtered_schools


def transform_school(school: dict[str,]) -> dict[str,]:
    school = {KEY_MAPPING[k]: v for k, v in school.items() if k in KEY_MAPPING}

    school["Setting"] = translate_locale_value(school["Setting"])
    if not school["Website"].startswith("http"):
        school["Website"] = "https://" + school["Website"]
    school["In-state Tuition"] = f"${school['In-state Tuition']}" if school["In-state Tuition"] else None
    school["Out-of-state Tuition"] = f"${school['Out-of-state Tuition']}" if school["Out-of-state Tuition"] else None
    school["6-year Median Salary"] = f"${school['6-year Median Salary']}" if school["6-year Median Salary"] else None
    school["Admission Rate"] = f"{round(school['Admission Rate'] * 100, 2)}%" if school["Admission Rate"] else None
    school["CS Degree %"] = f"{round(school['CS Degree %'] * 100, 2)}%" if school["CS Degree %"] else None
    return school
