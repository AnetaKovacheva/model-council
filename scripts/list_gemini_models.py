import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv()
key = os.environ["GOOGLE_API_KEY"]

url = f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=100&key={key}"
models = []
while url:
    with urllib.request.urlopen(url) as r:
        data = json.load(r)
    models += data.get("models", [])
    token = data.get("nextPageToken")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=100&pageToken={token}&key={key}"
        if token else None
    )

for m in sorted(models, key=lambda m: m["name"]):
    if "generateContent" in m.get("supportedGenerationMethods", []):
        print(m["name"].removeprefix("models/"))