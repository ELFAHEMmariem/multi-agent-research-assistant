
from app.tools.search import web_search


def main():
    results = web_search(
        "AI cybersecurity risks in healthcare"
    )

    for result in results:
        print("TITLE:", result.get("title"))
        print("URL:", result.get("url"))
        print("CONTENT:", result.get("content"))
        print("-" * 50)


if __name__ == "__main__":
    main()
