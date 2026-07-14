# soundcloud-to-spotify

A small Windows script that downloads a song from SoundCloud into Spotify's
Local Files folder. Type a song name to search, or paste a link.

Spotify has no cloud upload, so this uses the desktop app's Local Files feature:
the song is saved to a folder and shows up under Your Library → Local Files.

## Setup

You need Python, plus:

```
python -m pip install -U yt-dlp
winget install Gyan.FFmpeg
```

Then, one time in the Spotify desktop app: Settings → Local Files → turn on
Show Local Files → Add a source → pick your `Music\SoundCloud` folder.

## Usage

```
python sc2spotify.py "artist - song"
python sc2spotify.py "https://soundcloud.com/artist/track"
```

Or double-click `Add to Spotify.bat` and type a song when asked.

Searching a name shows the top 5 results so you can pick the right one. If a new
track doesn't appear, restart Spotify so it rescans the folder.

## Options

- `--format mp3|m4a` – output format (default mp3)
- `--dry-run` – download and check only

## Note

Files stay on your PC and reach your phone only inside a playlist with Premium.
Only works on tracks that are actually downloadable. For personal use.
