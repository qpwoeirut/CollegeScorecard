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


def make_query(filters: dict[str, ], fields: list = None) -> list[dict]:
    filters_str = '&'.join([f"{k}={v}" for k, v in filters.items()])
    fields_str = f"fields={','.join(fields)}" if fields else ""
    query = f"{filters_str}&{fields_str}"
    data = make_request(query)
    metadata = data["metadata"]
    total, per_page = metadata["total"], metadata["per_page"]
    print(total)

    all_results = []  # makes a repeat request, but should be okay
    for page in range((total + per_page - 1) // per_page):
        print(f"Fetching page {page}")
        data = make_request(f"{query}&page={page}")
        results = data["results"]
        all_results.extend(results)
    return all_results


schools = make_query(
    {"school.name": "Stanford University", "school.operating": 1},
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
        "latest.completion.title_iv.completed_by.4yrs", "latest.completion.title_iv.completed_by.6yrs",

        "latest.admissions",

        "latest.academics.program.degree.computer",

        # "latest.programs.cip_4_digit"  # Stanford's CS is 1107
    ]
)
for school in schools:
    print(school["school.name"])
    for k, v in school.items():
        print(f"{k}: {v}")
