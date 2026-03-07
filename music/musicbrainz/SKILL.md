---
name: musicbrainz
description: Query the MusicBrainz database for artists, releases, recordings, and obtain MBIDs using a dedicated helper script. Use this when the user needs precise metadata or MusicBrainz Identifiers for their music files.
---

# Instruction: musicbrainz

The MusicBrainz API is a complex, relationship-driven database that requires precise "MBIDs" (MusicBrainz Identifiers) for data lookups.

To make querying easier and to automatically handle strict rate-limits, you **MUST** use the provided Python helper script located at `~/.gemini/antigravity/skills/music/musicbrainz/scripts/mb_helper.py`.

**CRITICAL**: You must execute the script using `uv run`. The script contains inline metadata (`# /// script`) that `uv run` will use to automatically fetch the `musicbrainzngs` dependency in an isolated, temporary environment. Do **not** use `pip install`.

```bash
uv run ~/.gemini/antigravity/skills/music/musicbrainz/scripts/mb_helper.py <arguments>
```

## 1. Search vs Lookup Workflow

Because lookups require an MBID, interacting with MusicBrainz is usually a two-step process:

**Step 1: Search for an Entity**
Search for an artist, release, or recording to discover its MBID. The helper script returns the top 5 matches in JSON format.
```bash
uv run ~/.gemini/antigravity/skills/music/musicbrainz/scripts/mb_helper.py search artist "radiohead"
```

**Step 2: Lookup the MBID (with includes)**
Once you have the MBID, perform a direct lookup. Often, to get the deep data you actually want (such as all the releases an artist has made), you need to pass `--inc` arguments.
```bash
uv run ~/.gemini/antigravity/skills/music/musicbrainz/scripts/mb_helper.py lookup artist "a74b1b7f-71a5-4011-9441-d0b5e4122711" --inc "releases,recordings"
```
*(Common includes: `releases`, `recordings`, `artist-credits`, `aliases`)*

## 2. Authentication (User Data & Submissions)

Standard searches and lookups do **not** require authentication.

However, if the user asks you to interact with user-specific data (like user-tags, ratings, or submitting data), you must authenticate the helper script.

1. **Account Requirement**: MusicBrainz does not use traditional "API Keys". It uses standard HTTP Digest Auth. Instruct the user to create an account at `https://musicbrainz.org/register` if they do not have one.
2. **Environment Variables**: Instruct the user to set their credentials via the `MUSICBRAINZ_USERNAME` and `MUSICBRAINZ_PASSWORD` environment variables in their shell, or locate them if they have already set them.
3. **Running the Script**: Pass these credentials into the helper script using the optional flags:
```bash
uv run ~/.gemini/antigravity/skills/music/musicbrainz/scripts/mb_helper.py lookup artist <MBID> --username $MUSICBRAINZ_USERNAME --password $MUSICBRAINZ_PASSWORD
```
