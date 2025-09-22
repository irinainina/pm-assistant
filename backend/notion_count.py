import requests
from utils.config import Config

# Your Notion Internal Integration Token
NOTION_API_KEY = Config.NOTION_API_KEY

# Notion API endpoint for search
url = "https://api.notion.com/v1/search"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Empty query = search all pages
payload = {
    "query": "",
    "filter": {
        "property": "object",
        "value": "page"
    },
    "page_size": 100
}

all_pages = []
has_more = True
start_cursor = None

while has_more:
    if start_cursor:
        payload["start_cursor"] = start_cursor

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    # Collect results
    all_pages.extend(data.get("results", []))

    # Pagination control
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

# Print total number of pages
print(f"Total pages accessible to integration: {len(all_pages)}")

# Print ALL page titles and IDs
for i, page in enumerate(all_pages, start=1):
    page_id = page["id"]
    title = "Untitled"
    if "properties" in page and "title" in page["properties"]:
        title_prop = page["properties"]["title"].get("title", [])
        if title_prop:
            title = title_prop[0].get("plain_text", "Untitled")
    print(f"{i}. {title} ({page_id})")


# import requests
# from utils.config import Config

# NOTION_API_KEY = Config.NOTION_API_KEY
# NOTION_ROOT_PAGE_ID = Config.NOTION_ROOT_PAGE_ID

# headers = {
#     "Authorization": f"Bearer {NOTION_API_KEY}",
#     "Notion-Version": "2022-06-28",
#     "Content-Type": "application/json"
# }

# def count_child_pages(root_page_id):
#     url = f"https://api.notion.com/v1/blocks/{root_page_id}/children"
#     params = {"page_size": 100}

#     total_pages = 0
#     has_more = True
#     next_cursor = None

#     while has_more:
#         if next_cursor:
#             params["start_cursor"] = next_cursor

#         response = requests.get(url, headers=headers, params=params)
#         response.raise_for_status()
#         data = response.json()

#         # считаем только блоки типа "child_page"
#         for block in data.get("results", []):
#             if block["type"] == "child_page":
#                 total_pages += 1

#         has_more = data.get("has_more", False)
#         next_cursor = data.get("next_cursor")

#     return total_pages


# if __name__ == "__main__":    
#       count = count_child_pages(NOTION_ROOT_PAGE_ID)
#       print(f"Number of pages: {count}")
