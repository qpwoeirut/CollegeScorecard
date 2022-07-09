import json
import requests

with open(".env") as f:
    API_KEY = f.read().strip()

ENDPOINT = f"https://api.data.gov/ed/collegescorecard/v1/schools?api_key={API_KEY}&per_page=50"


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
    data = make_request(query)
    metadata = data["metadata"]
    total, per_page = metadata["total"], metadata["per_page"]

    all_results = []  # makes a repeat request, but should be okay
    for page in range((total + per_page - 1) // per_page):
        print(f"Fetching page {page}")
        data = make_request(f"{query}&page={page}")
        results = data["results"]
        all_results.extend(results)
    return all_results


def get_school_list() -> list[dict[str,]]:
    try:
        with open("unfiltered.json") as f:
            return json.loads(f.read().strip())
    except FileNotFoundError:
        schools = make_query(
            {
                "school.operating": 1,
                "latest.student.size__range": "500..",
            },
            [
                "school.name",
                "school.city", "school.state",
                "school.school_url",
                "school.degree_urbanization"

                "latest.cost.tuition.in_state", "latest.cost.tuition.out_of_state",

                "latest.student.size",

                "latest.earnings.6_yrs_after_entry.median", "latest.earnings.7_yrs_after_entry.mean_earnings",
                "latest.earnings.8_yrs_after_entry.mean_earnings", "latest.earnings.8_yrs_after_entry.median_earnings",
                "latest.earnings.9_yrs_after_entry.mean_earnings", "latest.earnings.10_yrs_after_entry.median",

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
        with open("unfiltered.json", "w+") as f:
            f.write(json.dumps(schools))
        return schools


def filter_schools(schools: list[dict[str,]]) -> list[dict[str,]]:
    # API can't filter based on these values
    filtered_schools = []
    for school in schools:  # could be done with a list comprehension, but using loops allows for printing stuff out
        if school["latest.academics.program.degree.computer"] == 0:
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

        filtered_schools.append(school)
    return filtered_schools


def main():
    schools = get_school_list()
    schools.sort(key=lambda s: s["school.name"])
    print(f"Total schools: {len(schools)}\n\n")
    filtered = filter_schools(schools)
    print(f"\n\nSchools remaining: {len(filtered)}")
    for school in filtered:
        print(school["school.name"])
        for k, v in school.items():
            if k == "school.school_url":
                v = "https://" + v
            print(f"{k}: {v}")
        print('=' * 80, '\n')


if __name__ == '__main__':
    main()
