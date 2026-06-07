---
name: kiwix
description: Query, search, and retrieve articles from a local Wikipedia database. Supports both HTTP API and direct ZIM file parsing. Use this when the user asks to query Wikipedia, search for concepts, or extract page contents locally.
---

# Instruction: kiwix

You can use the local Wikipedia database (via Kiwix) to query, search, and extract clean text articles. This skill supports two access modes:
1. **`api` mode (Default)**: Connects to the running `kiwix-serve` server on `localhost:8081`. Best for lightweight, step-by-step query-and-reason loops.
2. **`direct` mode**: Parses the ZIM archive on disk directly using `libzim`. Best for high-performance bulk operations or data mining (e.g., extracting multiple pages quickly).

The latest ZIM archive symlink is located at:
`/media/jbandlow/extra/kiwix/zims/wikipedia_en_all_maxi_latest.zim`

---

## 1. Installation & Setup

All dependencies are defined in `pyproject.toml` in this skill directory. To set up the virtual environment:
```bash
cd ~/.gemini/antigravity/skills/kiwix
uv sync
```

---

## 2. Command Line Interface (CLI)

The package exposes a `kiwix-tool` command. You can run it via `uv run` in the skill directory:

### Suggest / Autocomplete Page Titles
Get autocomplete suggestions for a term:
```bash
uv run kiwix-tool --method api suggest Python
uv run kiwix-tool --method direct suggest Python
```

### Full-Text Search
Search for articles matching a query:
```bash
uv run kiwix-tool --method api search "Zen of Python"
uv run kiwix-tool --method direct search "Zen of Python"
```

### Get Clean Article Plaintext
Fetch the clean plain text of a page:
```bash
uv run kiwix-tool --method api get "Python (programming language)"
uv run kiwix-tool --method direct get "Python (programming language)"
```
Use `--format html` to get raw HTML instead of plaintext.

---

## 3. Python Programmatic Usage

You can import and use `KiwixClient` directly in your Python tools/scripts:

```python
from kiwix_tool import KiwixClient

# 1. Initialize the client (Defaults to 'api' mode)
with KiwixClient(mode="api", host="http://localhost:8081") as client:
    # 2. Get autocomplete suggestions
    suggestions = client.suggest("Python")
    print("Suggestions:", suggestions)

    # 3. Search for articles
    results = client.search("Zen of Python")
    for r in results:
        print(f"Title: {r['title']}, Path: {r['path']}")

    # 4. Fetch page plaintext
    content = client.get_page_text("Zen of Python")
    print(content[:500])
```

To run in direct ZIM parsing mode:
```python
with KiwixClient(mode="direct", zim_path="/media/jbandlow/extra/kiwix/zims/wikipedia_en_all_maxi_latest.zim") as client:
    content = client.get_page_text("Python (programming language)")
    print(content[:500])
```

---

## 4. Performance Guidelines

* **Low-latency lookups**: For general QA or retrieval tasks where the agent searches for a page and reads it, use `mode="api"`. It has lower setup time and avoids reading the entire index file into Python memory.
* **Bulk queries**: For scripts or operations that require scanning or scraping thousands of articles (e.g. building a local database), use `mode="direct"`. It avoids HTTP network roundtrips, loopback latency, and HTTP parsing overhead, processing files at filesystem speeds.
