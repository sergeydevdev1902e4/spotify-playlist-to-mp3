import os
import httpx

class SpotifyClient:
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        self.token = None

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Spotify credentials not set. Need SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.")

    def _authenticate(self):
        url = "https://accounts.spotify.com/api/token"
        data = {"grant_type": "client_credentials"}
        res = httpx.post(
            url,
            data=data,
            auth=(self.client_id, self.client_secret),
            timeout=10.0
        )
        res.raise_for_status()
        self.token = res.json()["access_token"]

    def get_playlist_tracks(self, playlistId: str):
        """Fetches all tracks from a Spotify playlist, resolving pagination."""
        if not self.token:
            self._authenticate()

        headers = {"Authorization": f"Bearer {self.token}"}
        url = f"https://api.spotify.com/v1/playlists/{playlistId}/tracks?limit=100"
        tracks = []

        # TODO: Spotify API sometimes randomly resets connections on pagination, should probably add a 3-count retry loop
        while url:
            res = httpx.get(url, headers=headers, timeout=15.0)
            if res.status_code == 401:
                # Token might have expired during a very long sync run, re-auth once
                self._authenticate()
                headers["Authorization"] = f"Bearer {self.token}"
                res = httpx.get(url, headers=headers, timeout=15.0)

            res.raise_for_status()
            data = res.json()

            # print(f"DEBUG fetched page: {len(data.get('items', []))} items")

            for item in data.get("items", []):
                if not item or not item.get("track"):
                    continue

                track_data = item["track"]
                # Skip local files or podcast episodes that sometimes creep into playlists
                if track_data.get("is_local") or track_data.get("type") != "track":
                    continue

                artists = [a["name"] for a in track_data.get("artists", [])]
                tracks.append({
                    "id": track_data.get("id"),
                    "name": track_data.get("name"),
                    "artists": artists,
                    "album": track_data.get("album", {}).get("name", ""),
                    "duration_ms": track_data.get("duration_ms", 0)
                })

            url = data.get("next")

        return tracks
