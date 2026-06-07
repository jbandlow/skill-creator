import json
import subprocess
import sys

import pytest
import requests
from unittest.mock import patch, MagicMock
from kiwix_tool.client import KiwixClient, LIBZIM_AVAILABLE

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_HTML = """
<!DOCTYPE html>
<html>
<head><style>body { color: red; }</style></head>
<body>
  <div id="content">
    <h1>Title</h1>
    <script>alert("hello");</script>
    <p>This is the first paragraph.</p>
    <noscript>No script support</noscript>
    <p>This is the second paragraph.</p>
  </div>
</body>
</html>
"""


def _make_api_client(**kwargs) -> KiwixClient:
    """Create an API-mode client with a pre-set content name to skip catalog."""
    client = KiwixClient(mode="api", **kwargs)
    client._content_name = "wikipedia_test"
    return client


# ---------------------------------------------------------------------------
# clean_html
# ---------------------------------------------------------------------------


def test_clean_html():
    cleaned = KiwixClient.clean_html(TEST_HTML)
    assert "body { color: red; }" not in cleaned
    assert "alert" not in cleaned
    assert "No script support" not in cleaned
    assert "Title" in cleaned
    assert "This is the first paragraph." in cleaned
    assert "This is the second paragraph." in cleaned


def test_clean_html_no_content_div():
    """Falls back to full page text when there is no #content or .mw-parser-output."""
    html = "<html><body><p>Just a paragraph</p></body></html>"
    cleaned = KiwixClient.clean_html(html)
    assert "Just a paragraph" in cleaned


# ---------------------------------------------------------------------------
# _get_content_name
# ---------------------------------------------------------------------------


@patch("requests.get")
def test_get_content_name_success(mock_get):
    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <link type="text/html" href="/content/wikipedia_en_all_maxi_latest" />
      </entry>
    </feed>
    """
    mock_get.return_value.content = xml_response.encode("utf-8")
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = KiwixClient(mode="api")
    name = client._get_content_name()
    assert name == "wikipedia_en_all_maxi_latest"

    # Second call uses cache — no extra HTTP request.
    assert client._get_content_name() == "wikipedia_en_all_maxi_latest"
    mock_get.assert_called_once()


@patch("requests.get")
def test_get_content_name_connection_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("refused")

    client = KiwixClient(mode="api")
    with pytest.raises(requests.ConnectionError):
        client._get_content_name()


@patch("requests.get")
def test_get_content_name_no_content_in_catalog(mock_get):
    """Catalog returns valid XML but no matching content link."""
    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <link type="application/pdf" href="/other/thing" />
      </entry>
    </feed>
    """
    mock_get.return_value.content = xml_response.encode("utf-8")
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = KiwixClient(mode="api")
    with pytest.raises(ConnectionError, match="No content found"):
        client._get_content_name()


# ---------------------------------------------------------------------------
# suggest (API mode)
# ---------------------------------------------------------------------------


@patch("requests.get")
def test_suggest_api_mode(mock_get):
    mock_get.return_value.json.return_value = [
        {"value": "Python"},
        {"value": "Python (programming language)"},
    ]
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = _make_api_client()
    results = client.suggest("Py", count=5)
    assert results == ["Python", "Python (programming language)"]

    mock_get.assert_called_with(
        "http://localhost:8081/suggest",
        params={"content": "wikipedia_test", "term": "Py", "count": 5},
        timeout=5,
    )


# ---------------------------------------------------------------------------
# search (API mode)
# ---------------------------------------------------------------------------


@patch("requests.get")
def test_search_api_mode(mock_get):
    search_html = """
    <div class="results">
      <ul>
        <li>
          <a href="/content/wikipedia_test/Zen_of_Python">Zen of Python</a>
          <cite>...The Zen of Python is...</cite>
          <div class="informations">1,101 words</div>
        </li>
      </ul>
    </div>
    """
    mock_get.return_value.text = search_html
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = _make_api_client()
    results = client.search("Zen", count=1)
    assert len(results) == 1
    assert results[0]["title"] == "Zen of Python"
    assert results[0]["path"] == "Zen_of_Python"
    assert results[0]["snippet"] == "...The Zen of Python is..."
    assert results[0]["info"] == "1,101 words"


@patch("requests.get")
def test_search_api_mode_empty_results(mock_get):
    mock_get.return_value.text = "<html><body>No results</body></html>"
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = _make_api_client()
    results = client.search("xyznonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# get_page_html / get_page_text (API mode)
# ---------------------------------------------------------------------------


@patch("requests.get")
def test_get_page_html_api_mode(mock_get):
    mock_get.return_value.text = "<html>Content</html>"
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = _make_api_client()
    html = client.get_page_html("Zen of Python")
    assert html == "<html>Content</html>"
    mock_get.assert_called_with(
        "http://localhost:8081/content/wikipedia_test/Zen_of_Python",
        timeout=10,
    )


@patch("requests.get")
def test_get_page_text_api_mode(mock_get):
    """get_page_text is the composition of get_page_html + clean_html."""
    mock_get.return_value.text = TEST_HTML
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = MagicMock()

    client = _make_api_client()
    text = client.get_page_text("Test Page")
    assert "Title" in text
    assert "This is the first paragraph." in text
    assert "<script>" not in text


@patch("requests.get")
def test_get_page_html_api_mode_404(mock_get):
    mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("404")

    client = _make_api_client()
    with pytest.raises(requests.HTTPError):
        client.get_page_html("Nonexistent Page")


# ---------------------------------------------------------------------------
# Direct ZIM parsing tests (using mocks)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not LIBZIM_AVAILABLE, reason="libzim is not installed")
@patch("libzim.reader.Archive")
def test_suggest_direct_mode(mock_archive):
    mock_searcher = MagicMock()
    mock_search_res = MagicMock()

    mock_search_res.getEstimatedMatches.return_value = 2
    mock_search_res.getResults.return_value = [
        "A/Python",
        "A/Python_(programming_language)",
    ]
    mock_searcher.suggest.return_value = mock_search_res

    with patch("libzim.suggestion.SuggestionSearcher", return_value=mock_searcher):
        client = KiwixClient(mode="direct", zim_path="dummy.zim")
        client._archive = mock_archive

        results = client.suggest("Py", count=5)
        assert results == ["Python", "Python (programming language)"]
        mock_searcher.suggest.assert_called_with("Py")
        mock_search_res.getResults.assert_called_with(0, 2)


@pytest.mark.skipif(not LIBZIM_AVAILABLE, reason="libzim is not installed")
@patch("libzim.reader.Archive")
def test_search_direct_mode(mock_archive):
    mock_searcher = MagicMock()
    mock_search_res = MagicMock()
    mock_entry = MagicMock()

    mock_search_res.getEstimatedMatches.return_value = 1
    mock_search_res.getResults.return_value = ["A/Zen_of_Python"]
    mock_searcher.search.return_value = mock_search_res

    mock_entry.title = "Zen of Python"
    mock_entry.get_item.return_value.content = (
        b"<html><body>Zen description</body></html>"
    )
    mock_archive.get_entry_by_path.return_value = mock_entry

    with patch("libzim.search.Searcher", return_value=mock_searcher):
        client = KiwixClient(mode="direct", zim_path="dummy.zim")
        client._archive = mock_archive

        results = client.search("Zen", count=1)
        assert len(results) == 1
        assert results[0]["title"] == "Zen of Python"
        assert results[0]["path"] == "Zen_of_Python"
        assert "Zen description" in results[0]["snippet"]
        mock_archive.get_entry_by_path.assert_called_with("A/Zen_of_Python")


@pytest.mark.skipif(not LIBZIM_AVAILABLE, reason="libzim is not installed")
@patch("libzim.reader.Archive")
def test_get_page_html_direct_mode(mock_archive):
    mock_entry = MagicMock()
    mock_entry.get_item.return_value.content = b"<html>Content</html>"
    mock_archive.get_entry_by_path.return_value = mock_entry

    client = KiwixClient(mode="direct", zim_path="dummy.zim")
    client._archive = mock_archive

    html = client.get_page_html("Zen of Python")
    assert html == "<html>Content</html>"
    mock_archive.get_entry_by_path.assert_called_with("A/Zen_of_Python")


@pytest.mark.skipif(not LIBZIM_AVAILABLE, reason="libzim is not installed")
@patch("libzim.reader.Archive")
def test_get_page_html_direct_mode_not_found(mock_archive):
    mock_archive.get_entry_by_path.side_effect = KeyError("not found")

    client = KiwixClient(mode="direct", zim_path="dummy.zim")
    client._archive = mock_archive

    with pytest.raises(KeyError, match="not found in archive"):
        client.get_page_html("Nonexistent Page")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


def test_context_manager():
    client = KiwixClient(mode="api")
    with client as c:
        assert c is client
    # After exiting, _archive should be None (close was called).
    assert client._archive is None


# ---------------------------------------------------------------------------
# CLI (main.py)
# ---------------------------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the kiwix-tool CLI as a subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "kiwix_tool.main", *args],
        capture_output=True,
        text=True,
        cwd="/home/jbandlow/.gemini/antigravity/skills/kiwix",
    )


def test_cli_help():
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "kiwix" in result.stdout.lower() or "CLI tool" in result.stdout


def test_cli_suggest_subcommand_help():
    result = _run_cli("suggest", "--help")
    assert result.returncode == 0
    assert "term" in result.stdout.lower()


def test_cli_requires_subcommand():
    result = _run_cli()
    assert result.returncode != 0
