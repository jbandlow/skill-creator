---
name: beets
description: Manage, import, and organize music libraries using the beets CLI tool. Use this when the user asks to import music, query their local music collection, or manipulate music metadata.
---

# Instruction: beets

You can use the `beet` command-line application to manage a user's local music library.

## 0. Installation (CRITICAL)
If the user asks you to manage their music but `beets` is not installed on the system, **you must install it using `uv`**.
Do not use `pip` or `pipx`. 

```bash
uv tool install beets
```

## 1. Configuration
`beets` uses a YAML configuration file to know where music lives and how to import it.
- **Location**: Typically at `~/.config/beets/config.yaml`.
- **Viewing Paths**: Run `beet config -p` to see where the config file is located.
- **Editing**: Run `beet config -e` to open the configuration in the default editor. **Note:** As an agent, it is usually easier for you to directly edit the config file path if modifications are requested.

**Core Settings**:
- `directory`: The folder where the organized music is stored.
- `library`: The path to the SQLite database (e.g., `~/data/musiclibrary.db`).
- `import`: The import strategy.
  - `copy: yes`: Copies original files into the `directory`. (Default behavior).
  - `move: yes`: Moves original files into the `directory` (saves space).
  - `copy: no`: Tags files in place, without moving them. Add `write: no` to avoid touching files entirely.

## 2. Importing Music
To add music to the library and automatically tag it using MusicBrainz:
```bash
beet import <path_to_directory>
```

**Helpful Flags**:
- `-A`: Do not attempt to auto-tag the music.
- `-q`: Quiet mode. Do not ask for interactive input; skip ambiguous tracks.
- `-s`: Import tracks as singletons (individual tracks) instead of grouping them into albums.

## 3. Querying the Library
To query the database and list tracks or albums:
```bash
beet ls <query>
```

**Query Formatting**:
By default, an unadorned word like `beet ls love` matches substring values across artist, album, title, genre, etc.

*   **Specific Fields**: `beet ls artist:Radiohead` or `beet ls year:1990..1999`
*   **Albums (not tracks)**: `beet ls -a year:2012`
*   **Exact Matches**: `beet ls artist:=Radiohead` (prevents matching "Radiohead Cover Band").
*   **Case Insensitive Exact**: `beet ls artist:=~radiohead`.
*   **Regular Expressions**: `beet ls artist::^Radiohead`. (Prefix the expression with `:`).

## 4. Modifying and Removing
Change metadata in the database and write tags to files:
```bash
beet modify <query> <field>=<value>
# Example:
beet modify artist:Prince artist="The Artist"
```
*Note: Use the `-a` flag with modify to change album-level fields (like `albumartist` or `year`) to avoid cascading conflicts across tracks.*

To remove items from the database:
```bash
beet remove <query>
```
*Note: Add the `-d` flag if you want to also permanently delete the corresponding music files from the disk.*

To reorganize files according to path formats setup in the config:
```bash
beet move <query>
```

## 5. Getting Help & Documentation
If you are unsure of the correct syntax or need more specific details about advanced `beets` features or plugins:
- Run the localized help command: `beet help` or `beet help <command>`.
- Or, directly reference the official Beets documentation online at: `https://beets.readthedocs.io/en/stable/`.
