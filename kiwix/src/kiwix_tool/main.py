import argparse
import sys
import json
from .client import KiwixClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI tool to query local Kiwix/Wikipedia (via HTTP API or libzim)."
    )
    
    # Global arguments
    parser.add_argument(
        "--method",
        choices=["api", "direct"],
        default="api",
        help="Access method: 'api' uses the kiwix-serve HTTP API, 'direct' parses the ZIM file on disk directly (default: %(default)s)."
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8081",
        help="Kiwix HTTP server host/URL (default: %(default)s)."
    )
    parser.add_argument(
        "--zim",
        default="/media/jbandlow/extra/kiwix/zims/wikipedia_en_all_maxi_latest.zim",
        help="Path to the ZIM file archive on disk (default: %(default)s)."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # suggest subcommand
    suggest_parser = subparsers.add_parser(
        "suggest", help="Get autocomplete suggestions for a prefix term."
    )
    suggest_parser.add_argument("term", help="Prefix search term.")
    suggest_parser.add_argument(
        "--count", type=int, default=10, help="Maximum suggestions (default: %(default)s)."
    )

    # search subcommand
    search_parser = subparsers.add_parser(
        "search", help="Perform a full-text query across articles."
    )
    search_parser.add_argument("query", help="Full-text query string.")
    search_parser.add_argument(
        "--count", type=int, default=10, help="Maximum results (default: %(default)s)."
    )

    # get subcommand
    get_parser = subparsers.add_parser(
        "get", help="Retrieve content of a specific page."
    )
    get_parser.add_argument("title", help="Case-sensitive Wikipedia page title.")
    get_parser.add_argument(
        "--format",
        choices=["text", "html"],
        default="text",
        help="Output format: 'text' or 'html' (default: %(default)s)."
    )

    args = parser.parse_args()

    try:
        # Initialize client
        client = KiwixClient(mode=args.method, host=args.host, zim_path=args.zim)
    except Exception as e:
        print(f"Error initializing KiwixClient: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with client:
            if args.command == "suggest":
                results = client.suggest(args.term, count=args.count)
                print(json.dumps(results, indent=2))

            elif args.command == "search":
                results = client.search(args.query, count=args.count)
                print(json.dumps(results, indent=2))

            elif args.command == "get":
                if args.format == "html":
                    content = client.get_page_html(args.title)
                else:
                    content = client.get_page_text(args.title)
                print(content)

    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
