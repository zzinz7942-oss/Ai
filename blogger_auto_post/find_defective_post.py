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

request = service.posts().list(blogId=config.BLOGGER_BLOG_ID, fetchBodies=True, maxResults=100)
response = request.execute()
posts = response.get('items', [])

for p in posts:
    if "배터리" in p.get("title", ""):
        content = p.get("content", "")
        if "Apple, Samsung, Nike" in content:
            print(f"FOUND DEFECTIVE POST: ID {p['id']}, URL {p['url']}")
        else:
            print(f"CLEAN POST: ID {p['id']}, URL {p['url']}")
