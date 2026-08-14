import argparse
import json
import os
import sys
from pathlib import Path

from spotify_sync import spotify
from spotify_sync import downloader

def sanitize_filename(name):
    # keep it simple, strip out things that break windows paths
    for c in '<>:"/\\|?*':
        name = name.replace(c, '')
    return name.strip()

def load_state(output_dir):
    state_file = Path(output_dir) / ".sync_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # state file corrupted, start fresh
            return {}
    return {}

def save_state(output_dir, state):
    state_file = Path(output_dir) / ".sync_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def sync_playlist(playlist_id, output_dir, client_id, client_secret, lastfm_key):
    """Downloads tracks from a Spotify playlist that aren't already synced."""
    out_path = Path(output_dir)
    if not out_path.exists():
        out_path.mkdir(parents=True, exist_ok=True)

    state = load_state(out_path)

    print(f"Fetching tracks for playlist {playlist_id}...")
    try:
        tracks = spotify.get_playlist_tracks(playlist_id, client_id, client_secret)
    except Exception as e:
        print(f"Failed to fetch Spotify playlist: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(tracks)} tracks in playlist.")
    
    # We clean up missing files from state so we re-download if deleted manually
    active_ids = {t["id"] for t in tracks if t.get("id")}
    state = {tid: path for tid, path in state.items() if tid in active_ids and (out_path / path).exists()}

    for idx, track in enumerate(tracks, 1):
        # Spotify API can return None for local files uploaded by users
        if not track or not track.get("id"):
            print(f"[{idx}/{len(tracks)}] Skipping un-identifiable local or empty track.")
            continue
            
        track_id = track["id"]
        artist = track["artist"]
        title = track["title"]
        
        # print(f"DEBUG: Processing track ID {track_id} - {artist} - {title}")
        
        if track_id in state:
            # Double check the file actually exists where we expect it
            expected_file = out_path / state[track_id]
            if expected_file.exists():
                print(f"[{idx}/{len(tracks)}] Skipping: {artist} - {title} (already downloaded)")
                continue

        print(f"[{idx}/{len(tracks)}] Syncing: {artist} - {title}")
        safe_filename = sanitize_filename(f"{artist} - {title}")
        dest_filename = f"{safe_filename}.mp3"
        dest_path = out_path / dest_filename
        
        # Avoid collisions if another track happened to generate the same safe filename
        counter = 1
        while dest_path.exists():
            dest_filename = f"{safe_filename} ({counter}).mp3"
            dest_path = out_path / dest_filename
            counter += 1

        try:
            downloader.download_track(track, dest_path, lastfm_key)
            state[track_id] = dest_filename
            save_state(out_path, state)
        except Exception as e:
            # We don't want one bad download to stop the whole sync process
            print(f"  Error syncing {artist} - {title}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Sync a Spotify playlist to a local directory of tagged MP3s."
    )
    parser.add_argument("playlist_id", help="Spotify playlist ID or share URL")
    parser.add_argument("output_dir", help="Local directory to save MP3s")
    
    args = parser.parse_args()
    
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    lastfm_key = os.environ.get("LASTFM_API_KEY")
    
    if not client_id or not client_secret:
        print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env variables must be set.", file=sys.stderr)
        sys.exit(1)
        
    try:
        sync_playlist(args.playlist_id, args.output_dir, client_id, client_secret, lastfm_key)
    except KeyboardInterrupt:
        print("\nSync interrupted by user. Exiting.")
        sys.exit(130)

if __name__ == "__main__":
    main()
