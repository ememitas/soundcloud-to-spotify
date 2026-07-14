#!/usr/bin/env python3
"""Download a SoundCloud track (or search result) into Spotify's Local Files folder.

Spotify has no cloud upload, so this saves the track into a folder you add as a
Local Files source in Spotify's settings. Downloads with yt-dlp, converts to MP3
with tags + cover art, and checks the file before saving it.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOCAL_FILES_DIR = Path.home() / "Music" / "SoundCloud"
STAGING = Path(os.environ.get("TEMP", str(Path.home()))) / "sc2spotify_staging"
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".opus", ".flac", ".wav", ".ogg"}


def log(msg):  print(f"[sc2spotify] {msg}", flush=True)
def ok(msg):   print(f"[ OK ] {msg}", flush=True)
def err(msg):  print(f"[FAIL] {msg}", flush=True)


def which(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def ytdlp_cmd():
    exe = which("yt-dlp", "yt-dlp.exe")
    if exe:
        return [exe]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, check=True)
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return None


def preflight():
    problems = []
    yt = ytdlp_cmd()
    if not yt:
        problems.append("yt-dlp not found. Install with: python -m pip install -U yt-dlp")
    if not which("ffmpeg", "ffmpeg.exe"):
        problems.append("ffmpeg not found. Install with: winget install Gyan.FFmpeg")
    if problems:
        err("Pre-flight checks failed:")
        for p in problems:
            print("   - " + p)
        return None, None
    LOCAL_FILES_DIR.mkdir(parents=True, exist_ok=True)
    return yt, which("ffprobe", "ffprobe.exe")


def is_url(text):
    return text.strip().lower().startswith(("http://", "https://"))


def search_soundcloud(yt, query, n=5):
    cmd = yt + ["--flat-playlist", "--no-warnings",
                "--print", "%(title)s\t%(uploader)s\t%(webpage_url)s",
                f"scsearch{n}:{query}"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    results = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2].startswith("http"):
            results.append((parts[0], parts[1], parts[2]))
    return results


def choose_track(yt, query):
    log(f'Searching SoundCloud for: "{query}"')
    results = search_soundcloud(yt, query, 5)
    if not results:
        err("No results found for that search.")
        return None
    if not sys.stdin or not sys.stdin.isatty():
        return results[0][2]
    print()
    for i, (title, uploader, _url) in enumerate(results, 1):
        print(f"  {i}. {title}  —  {uploader}")
    print("  0. cancel")
    while True:
        choice = input("Pick a track number: ").strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1][2]
        print("  Please enter a number from the list.")


def clear_staging():
    if STAGING.exists():
        shutil.rmtree(STAGING, ignore_errors=True)
    STAGING.mkdir(parents=True, exist_ok=True)


def download(yt, url, fmt, quality):
    clear_staging()
    out_tmpl = str(STAGING / "%(uploader)s - %(title)s.%(ext)s")
    cmd = yt + ["-x", "--audio-format", fmt, "--audio-quality", str(quality),
                "--embed-metadata", "--embed-thumbnail", "--add-metadata",
                "--no-overwrites", "--ignore-errors", "--no-warnings",
                "-o", out_tmpl, url]
    log(f"Downloading: {url}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 and not any(STAGING.iterdir()):
        err("yt-dlp failed:")
        print(proc.stderr.strip()[-1500:])
        return []
    files = [p for p in STAGING.iterdir()
             if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    if not files:
        err("yt-dlp produced no audio files.")
        print((proc.stderr or proc.stdout).strip()[-1500:])
    return files


def validate(ffprobe, path):
    if not path.exists() or path.stat().st_size < 4096:
        return False, "file missing or suspiciously small"
    if not ffprobe:
        return True, "ffprobe unavailable, skipped deep check"
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type,duration",
             "-of", "default=noprint_wrappers=1", str(path)],
            capture_output=True, text=True, timeout=30)
    except Exception as e:
        return False, f"ffprobe error: {e}"
    if "codec_type=audio" not in r.stdout:
        return False, "no audio stream detected"
    return True, "valid audio stream"


def save_to_local_files(path):
    dest = LOCAL_FILES_DIR / path.name
    try:
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
    except Exception as e:
        return "error", f"could not save into Local Files folder: {e}"
    return "saved", f"saved to {dest}"


def main():
    ap = argparse.ArgumentParser(description="Download SoundCloud tracks into Spotify Local Files.")
    ap.add_argument("urls", nargs="+", help="song name(s) or SoundCloud URL(s)")
    ap.add_argument("--format", default="mp3", choices=["mp3", "m4a"])
    ap.add_argument("--quality", default="0", help="yt-dlp audio quality (0=best)")
    ap.add_argument("--dry-run", action="store_true", help="download + validate only")
    args = ap.parse_args()

    yt, ffprobe = preflight()
    if not yt:
        sys.exit(1)

    results = []
    for raw in args.urls:
        if is_url(raw):
            target = raw
        else:
            target = choose_track(yt, raw)
            if not target:
                results.append((raw, "download-failed", "no track selected"))
                continue

        files = download(yt, target, args.format, args.quality)
        if not files:
            results.append((raw, "download-failed", "no audio produced"))
            continue

        for f in files:
            title = f.stem
            good, detail = validate(ffprobe, f)
            if not good:
                err(f"{title}: {detail}")
                results.append((title, "invalid", detail))
                continue
            ok(f"Validated: {title} ({detail})")

            if args.dry_run:
                results.append((title, "dry-run", "downloaded + validated"))
                continue

            status, d = save_to_local_files(f)
            (ok if status == "saved" else err)(f"{title}: {d}")
            results.append((title, status, d))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    icons = {"saved": "OK ", "dry-run": "OK ", "invalid": "FAIL",
             "download-failed": "FAIL", "error": "FAIL"}
    n_ok = 0
    for title, status, detail in results:
        if status in ("saved", "dry-run"):
            n_ok += 1
        print(f"[{icons.get(status, '??? ')}] {title}")
        if status not in ("saved", "dry-run"):
            print(f"       -> {detail}")
    print("-" * 60)
    print(f"{n_ok}/{len(results)} saved to the Spotify Local Files folder")

    shutil.rmtree(STAGING, ignore_errors=True)
    if any(s not in ("saved", "dry-run") for _, s, _ in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
