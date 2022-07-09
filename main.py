import csv
import hashlib
import json
import requests

with open(".env") as f:
    API_KEY = f.read().strip()

ENDPOINT = f"https://api.data.gov/ed/collegescorecard/v1/schools?api_key={API_KEY}&per_page=50"
KEY_MAPPING = {
    "school.name": "Name",
    "school.city": "City",
    "school.state": "State",
    "school.school_url": "Website",
    "school.locale": "Setting",
    "latest.cost.tuition.in_state": "In-state Tuition",
    "latest.cost.tuition.out_of_state": "Out-of-state Tuition",
    "latest.student.size": "Undergrad Size",
    "latest.earnings.6_yrs_after_entry.median": "6-year Median Salary",
    "latest.completion.consumer_rate": "Graduation Rate",
    "latest.admissions.admission_rate.consumer_rate": "Admission Rate",
    "latest.academics.program_percentage.computer": "% of CS Degrees",

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
    return make_query(filters,
                      [
                          "school.name",
                          "school.city", "school.state",
                          "school.school_url",
                          "school.type",
                          "school.locale",

                          "latest.cost.tuition.in_state", "latest.cost.tuition.out_of_state",

                          "latest.student.size",

                          "latest.earnings.6_yrs_after_entry.median",
                          # "latest.earnings.7_yrs_after_entry.mean_earnings",
                          # "latest.earnings.8_yrs_after_entry.mean_earnings", "latest.earnings.8_yrs_after_entry.median_earnings",
                          # "latest.earnings.9_yrs_after_entry.mean_earnings", "latest.earnings.10_yrs_after_entry.median",

                          "latest.completion.consumer_rate",
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
            print(f"Filtered {school['school.name']}.".ljust(70, '.') + " no Bachelors program for CS")
            continue

        median_earnings_6_yrs = school["latest.earnings.6_yrs_after_entry.median"]
        if median_earnings_6_yrs is None:
            print(f"Filtered {school['school.name']}.".ljust(70, '.') + " no median earnings data")
            continue
        if median_earnings_6_yrs < 50000:
            print(
                f"Filtered {school['school.name']}.".ljust(70, '.') +
                f" median earnings 6 years after entry (${median_earnings_6_yrs}) is < $50000")
            continue

        sat_score = school["latest.admissions.sat_scores.average.overall"]
        if sat_score is not None and sat_score < 1200:
            print(
                f"Filtered {school['school.name']}.".ljust(70, '.') +
                f" SAT average ({sat_score}) is < 1200")
            continue

        filtered_schools.append(school)
    return filtered_schools


def transform_school(school: dict[str,]) -> dict[str,]:
    school = {KEY_MAPPING[k]: v for k, v in school.items() if k in KEY_MAPPING}
    # school["Location"] = f"{school['City']}, {school['State']}"
    # del school["City"]
    # del school["State"]

    school["Setting"] = translate_locale_value(school["Setting"])
    if not school["Website"].startswith("http"):
        school["Website"] = "https://" + school["Website"]
    return school


def general_search() -> list[dict[str,]]:
    schools = get_school_list({"school.operating": 1, "latest.student.size__range": "500.."})
    schools.sort(key=lambda s: s["school.name"])
    print(f"Total schools: {len(schools)}\n\n")
    filtered = [transform_school(school) for school in filter_schools(schools)]
    return filtered


def search_from_list(names: list[str]) -> list[dict[str,]]:
    schools = []
    for name in names:
        school = get_school_list({"school.name": name})[0]
        schools.append(school)  # couldn't get multivalue filter working for school.name
    return [transform_school(school) for school in schools]


def print_schools(schools: list[dict[str,]]):
    for school in schools:
        print(school["Name"])
        for k, v in school.items():
            print(f"{k}: {v}")
        print('=' * 80, '\n')


def save_schools(filename: str, schools: list[dict[str,]]):
    with open(filename, "w+") as csv_file:
        field_names = KEY_MAPPING.values()
        writer = csv.DictWriter(csv_file, field_names)
        writer.writeheader()
        for school in schools:
            writer.writerow(school)


def main():
    schools = search_from_list([
        "Massachusetts Institute of Technology",
        "Stanford University",
        "University of California-Los Angeles",
        "Harvard University",
        "Princeton University",
        "University of Chicago",
        "University of Pennsylvania",
        "Yale University",
        "Rice University",
        "University of California-Berkeley",
        "University of Maryland-College Park",
        "University of California-Irvine",
        "University of California-San Diego",
        "Cornell University",
        "University of California-Davis",
        "Carnegie Mellon University",
        "University of California-Santa Barbara",
        "California Institute of Technology",
        "Johns Hopkins University",
        "University of Michigan-Ann Arbor",
        "The University of Texas at Austin",
        "Georgia Tech",
        "Purdue University-Main Campus",
        "UIUC",
        "University of Washington-Seattle Campus",
        "Ohio State University-Main Campus",
        "University of Wisconsin-Madison",
    ])

    save_schools("ranking.csv", schools)


if __name__ == '__main__':
    main()
