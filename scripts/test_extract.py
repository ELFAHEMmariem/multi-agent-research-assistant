
from app.tools.search import web_search
from app.tools.dedup import deduplicate_results
from app.tools.extract import extract_pages


def main():
    results = web_search(
        "OWASP LLM prompt injection security"
    )

    unique = deduplicate_results(
        results,
        max_per_domain=2,
        max_total=2,
    )

    urls = [item["url"] for item in unique]

    extracted = extract_pages(urls)

    for page in extracted["results"]:
        print("\nURL:", page["url"])
        print(
            page.get("raw_content", "")[:500]
        )

    print(
        "\nFAILED:",
        extracted["failed_results"],
    )


if __name__ == "__main__":
    main()
