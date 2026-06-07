from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Try importing libzim, handle gracefully if not installed
try:
    import libzim.reader
    import libzim.search
    import libzim.suggestion
    LIBZIM_AVAILABLE = True
except ImportError:
    LIBZIM_AVAILABLE = False


class KiwixClient:
    """
    Client for accessing local Wikipedia content from Kiwix.
    Supports both HTTP API (via kiwix-serve) and direct file parsing (via libzim).
    """

    def __init__(
        self,
        mode: str = "api",
        host: str = "http://localhost:8081",
        zim_path: str = "/media/jbandlow/extra/kiwix/zims/wikipedia_en_all_maxi_latest.zim"
    ):
        self.mode = mode.lower()
        self.host = host.rstrip("/")
        self.zim_path = zim_path
        
        self._content_name: str | None = None
        self._archive: libzim.reader.Archive | None = None

        if self.mode == "direct":
            if not LIBZIM_AVAILABLE:
                raise ImportError(
                    "The 'libzim' Python package is not installed. "
                    "Install it or run in 'api' mode."
                )
            try:
                self._archive = libzim.reader.Archive(self.zim_path)
            except Exception as e:
                raise IOError(
                    f"Failed to open ZIM archive at {self.zim_path}: {e}"
                )

    def close(self) -> None:
        """Close any open file handles (applicable to direct mode)."""
        self._archive = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_content_name(self) -> str:
        """Retrieve the name of the ZIM content from the server catalog (API mode).

        Raises:
            ConnectionError: If kiwix-serve is unreachable or returns no content.
        """
        if self._content_name:
            return self._content_name

        r = requests.get(f"{self.host}/catalog/v2/entries?count=-1", timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for link in root.findall(".//atom:entry/atom:link[@type='text/html']", ns):
            href = link.attrib.get("href", "")
            if href.startswith("/content/"):
                self._content_name = href.split("/")[-1]
                return self._content_name

        raise ConnectionError(
            f"No content found in kiwix-serve catalog at {self.host}. "
            "Is kiwix-serve running and serving a ZIM file?"
        )

    def suggest(self, term: str, count: int = 10) -> list[str]:
        """Get title suggestions matching the query prefix."""
        if self.mode == "api":
            content_name = self._get_content_name()
            params = {
                "content": content_name,
                "term": term,
                "count": count
            }
            r = requests.get(f"{self.host}/suggest", params=params, timeout=5)
            r.raise_for_status()
            data = r.json()
            # Parse suggest JSON responses
            results = []
            for item in data:
                val = item.get("value", "")
                if val:
                    results.append(val)
            return results
        else:
            # direct mode
            if self._archive is None:
                raise RuntimeError("Archive not initialized for direct mode.")
            searcher = libzim.suggestion.SuggestionSearcher(self._archive)
            search_res = searcher.suggest(term)
            total = search_res.getEstimatedMatches()
            results = []
            for path in search_res.getResults(0, min(count, total)):
                # Convert ZIM internal path (e.g. A/Title) to clean title
                title = path
                if title.startswith("A/"):
                    title = title[2:]
                title = title.replace("_", " ")
                title = urllib.parse.unquote(title)
                results.append(title)
            return results

    def search(self, query: str, count: int = 25) -> list[dict[str, str]]:
        """Perform a full-text search across the wiki."""
        if self.mode == "api":
            content_name = self._get_content_name()
            params = {
                "books.name": content_name,
                "pattern": query,
                "pageLength": count
            }
            r = requests.get(f"{self.host}/search", params=params, timeout=10)
            r.raise_for_status()
            
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            results_container = soup.find(class_="results")
            if results_container:
                for li in results_container.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    
                    # Extract the article path relative to content root
                    path = href
                    prefix = f"/content/{content_name}/"
                    if prefix in path:
                        path = path.split(prefix)[-1]
                    elif "/content/" in path:
                        path = path.split("/content/")[-1].split("/", 1)[-1]
                    else:
                        path = path.split("/")[-1]

                    cite = li.find("cite")
                    snippet = cite.get_text(strip=True) if cite else ""
                    info_div = li.find("div", class_="informations")
                    info = info_div.get_text(strip=True) if info_div else ""
                    
                    results.append({
                        "title": title,
                        "path": path,
                        "snippet": snippet,
                        "info": info
                    })
            return results
        else:
            # direct mode
            if self._archive is None:
                raise RuntimeError("Archive not initialized for direct mode.")
            query_obj = libzim.search.Query().set_query(query)
            searcher = libzim.search.Searcher(self._archive)
            search_res = searcher.search(query_obj)
            total = search_res.getEstimatedMatches()
            results = []
            for path in search_res.getResults(0, min(count, total)):
                try:
                    entry = self._archive.get_entry_by_path(path)
                    clean_path = path[2:] if path.startswith("A/") else path
                    # Extract a snippet from first 200 chars of plaintext
                    content_bytes = entry.get_item().content
                    html_content = bytes(content_bytes).decode("utf-8", errors="ignore")
                    snippet = self.clean_html(html_content)[:200]
                    if len(snippet) >= 200:
                        snippet += "..."
                    results.append({
                        "title": entry.title,
                        "path": clean_path,
                        "snippet": snippet,
                        "info": f"{len(html_content)} bytes"
                    })
                except Exception:
                    continue
            return results

    def get_page_html(self, title: str) -> str:
        """Retrieve the raw HTML content of a page."""
        # Clean title spaces to underscores
        formatted_title = title.replace(" ", "_")
        if self.mode == "api":
            content_name = self._get_content_name()
            # Escape title characters
            escaped_title = urllib.parse.quote(formatted_title)
            url = f"{self.host}/content/{content_name}/{escaped_title}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.text
        else:
            # direct mode
            if self._archive is None:
                raise RuntimeError("Archive not initialized for direct mode.")
            paths_to_try = [f"A/{formatted_title}", formatted_title]
            for p in paths_to_try:
                try:
                    entry = self._archive.get_entry_by_path(p)
                    content_bytes = entry.get_item().content
                    return bytes(content_bytes).decode("utf-8")
                except KeyError:
                    continue
            raise KeyError(f"Page '{title}' not found in archive.")

    def get_page_text(self, title: str) -> str:
        """Retrieve a cleaned plaintext version of a page."""
        html = self.get_page_html(title)
        return self.clean_html(html)

    @staticmethod
    def clean_html(html: str) -> str:
        """Helper to extract text from HTML and remove page clutter."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove styling and script elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
            
        # Target the main article body container (vector layout / mediawiki)
        content_div = soup.find(id="content") or soup.find(class_="mw-parser-output")
        if content_div:
            text = content_div.get_text()
        else:
            text = soup.get_text()
            
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Strip duplicate newline sequences
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        return cleaned_text.strip()
