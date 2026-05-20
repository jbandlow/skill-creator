# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "musicbrainzngs",
# ]
# ///

import argparse
import json
import sys
import musicbrainzngs

def setup_api(username=None, password=None):
    # MusicBrainz requires a meaningful user agent
    musicbrainzngs.set_useragent(
        "AntigravityMusicBrainzSkill",
        "1.0",
        "https://github.com/jbandlow/skill-creator"
    )
    if username and password:
        musicbrainzngs.auth(username, password)

def search(entity_type, query, limit=5):
    try:
        if entity_type == 'artist':
            result = musicbrainzngs.search_artists(query, limit=limit)
            items = result.get('artist-list', [])
        elif entity_type == 'release':
            result = musicbrainzngs.search_releases(query, limit=limit)
            items = result.get('release-list', [])
        elif entity_type == 'recording':
            result = musicbrainzngs.search_recordings(query, limit=limit)
            items = result.get('recording-list', [])
        else:
            print(f"Error: Unsupported search entity type '{entity_type}'. Supported: artist, release, recording.")
            sys.exit(1)
            
        print(json.dumps(items, indent=2))
    except Exception as e:
        print(f"Search failed: {e}")
        sys.exit(1)

def lookup(entity_type, mbid, includes=None):
    inc_list = includes.split(',') if includes else []
    try:
        if entity_type == 'artist':
            result = musicbrainzngs.get_artist_by_id(mbid, includes=inc_list)
            item = result.get('artist', {})
        elif entity_type == 'release':
            result = musicbrainzngs.get_release_by_id(mbid, includes=inc_list)
            item = result.get('release', {})
        elif entity_type == 'recording':
            result = musicbrainzngs.get_recording_by_id(mbid, includes=inc_list)
            item = result.get('recording', {})
        else:
            print(f"Error: Unsupported lookup entity type '{entity_type}'. Supported: artist, release, recording.")
            sys.exit(1)
            
        print(json.dumps(item, indent=2))
    except Exception as e:
        print(f"Lookup failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Helper script for querying the MusicBrainz API.")
    parser.add_argument('action', choices=['search', 'lookup'], help="Action to perform.")
    parser.add_argument('entity_type', choices=['artist', 'release', 'recording'], help="The type of entity.")
    parser.add_argument('query_or_mbid', help="The search query string OR the precise MBID.")
    
    parser.add_argument('--inc', help="Comma-separated list of includes for lookups (e.g., 'releases,recordings').")
    parser.add_argument('--limit', type=int, default=5, help="Number of search results to return.")
    
    # Auth arguments
    parser.add_argument('--username', help="MusicBrainz website username (for digest auth).")
    parser.add_argument('--password', help="MusicBrainz website password.")

    args = parser.parse_args()

    setup_api(username=args.username, password=args.password)

    if args.action == 'search':
        search(args.entity_type, args.query_or_mbid, args.limit)
    elif args.action == 'lookup':
        lookup(args.entity_type, args.query_or_mbid, args.inc)

if __name__ == "__main__":
    main()
