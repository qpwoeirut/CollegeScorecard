import csv

from query_api import filter_schools, get_school_list, transform_school, KEY_MAPPING


def general_search() -> dict[str, dict[str,]]:
    schools = get_school_list({"school.operating": 1, "latest.student.size__range": "500.."})
    schools.sort(key=lambda s: s["school.name"])
    schools = [transform_school(school) for school in filter_schools(schools)]
    return {school["Name"]: school for school in schools}


def search_from_list(names: list[str]) -> dict[str, dict[str,]]:
    schools = {}
    for name in names:
        results = get_school_list({"school.name": name})
        # the search is autocompleted, so make sure we get the value we want
        try:
            school = results[0] if len(results) == 1 else [r for r in results if r["school.name"] == name][0]
        except IndexError:
            raise ValueError(f"{name} not found. found {[s['school.name'] for s in results]} instead")
        schools[name] = transform_school(school)  # couldn't get multivalue filter working for school.name
    return schools


def print_schools(schools: list[dict[str,]]):
    print(f"Total schools: {len(schools)}\n\n")
    for school in schools:
        print(school["Name"] if "Name" in school else school["school.name"])
        for k, v in school.items():
            print(f"{k}: {v}")
        print('=' * 80, '\n')


def add_us_news_link(us_news_dict: dict[str, str], schools: dict[str, dict[str, ]]) -> dict[str, dict[str, ]]:
    for k in schools.keys():
        schools[k]["US News Link"] = f"https://www.usnews.com/best-colleges/{us_news_dict[k]}"
    return schools


def save_schools(filename: str, schools: dict[str, dict[str,]], additional_fields: list):
    with open(filename, "w+") as csv_file:
        field_names = list(KEY_MAPPING.values()) + additional_fields
        field_names.remove("Website")

        writer = csv.DictWriter(csv_file, field_names, extrasaction="ignore")
        writer.writeheader()
        for school in schools.values():
            school["Name"] = f"""=HYPERLINK("{school["Website"]}", "{school["Name"]}")"""
            writer.writerow(school)


def main():
    with open("school_list.csv") as f:
        reader = csv.DictReader(f)
        school_dict = {row["Name"]: row["US N&W ID"] for row in reader}
    schools = search_from_list(list(school_dict.keys()))
    schools = add_us_news_link(school_dict, schools)
    save_schools("ranking.csv", schools, ["US News Link"])

    schools = general_search()
    save_schools("general.csv", schools, [])


if __name__ == '__main__':
    main()
