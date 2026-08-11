import sys
import os
import json
import re
import requests

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import config
import blogger_client

service = blogger_client._get_service()

# 1. Search all posts to see if there are duplicates
print("=== Searching all posts ===")
request = service.posts().list(blogId=config.BLOGGER_BLOG_ID, fetchBodies=True, maxResults=100)
response = request.execute()
posts = response.get('items', [])

ev_posts = []
for p in posts:
    if "배터리" in p.get("title", "") or "전기차" in p.get("title", ""):
        ev_posts.append(p)

for p in ev_posts:
    print(f"ID: {p['id']}, URL: {p['url']}, Title: {p['title']}, Updated: {p['updated']}")

print("\n=== Fetching Target Post ID 9099587799185812804 ===")
try:
    target_post = service.posts().get(blogId=config.BLOGGER_BLOG_ID, postId="9099587799185812804").execute()
    print(f"ID: {target_post['id']}")
    print(f"URL: {target_post.get('url')}")
    print(f"Title: {target_post.get('title')}")
    print(f"Updated: {target_post.get('updated')}")
    
    content = target_post.get("content", "")
    print(f"Content Length: {len(content)}")
    if "Apple, Samsung, Nike" in content:
        print("BRAND DUMP FOUND IN API CONTENT")
    else:
        print("BRAND DUMP NOT FOUND IN API CONTENT")
        
    if "2026년 2026년" in content:
        print("2026 DUPLICATE FOUND IN API CONTENT")
    else:
        print("2026 DUPLICATE NOT FOUND IN API CONTENT")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Fetching Live URL HTML ===")
live_url = target_post.get("url") if target_post else "https://tech-workstation.blogspot.com/2026/08/2026-3-lfp-k_01416599853.html"
try:
    resp = requests.get(live_url)
    print(f"Status: {resp.status_code}")
    html = resp.text
    if "Apple, Samsung, Nike" in html:
        print("BRAND DUMP FOUND IN LIVE HTML")
    else:
        print("BRAND DUMP NOT FOUND IN LIVE HTML")
except Exception as e:
    print(f"Error fetching live URL: {e}")
