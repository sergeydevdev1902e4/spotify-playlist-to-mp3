# spotify-playlist-to-mp3

I built this tool to sync my Spotify playlists to a local folder on my Windows machine so I can load them onto my offline music player. It fetches the track list from a Spotify playlist, searches for the best matching audio on YouTube, downloads and converts it to MP3 using yt-dlp, and then pulls accurate genre tags from Last.fm to write into the ID3 metadata.

It skips already downloaded tracks, so you can run it repeatedly to keep your local directory in sync with your playlist.

## Prerequisites

1. **FFmpeg**: You must have `ffmpeg.exe` and `ffprobe.exe` in your system PATH (or in the same directory as the script) so yt-dlp can convert the downloaded audio to MP3.
2. **Spotify API Credentials**: You need a Client ID and Client Secret from the Spotify Developer Dashboard.
3. **Last.fm API Key** (Optional but recommended): Needed if you want the script to tag your files with proper genres.

## Installation

Clone this repository and install the dependencies:

```cmd
pip install -r requirements.txt
```

## Usage

Set your credentials as environment variables to keep your command lines clean:

```cmd
set SPOTIFY_CLIENT_ID=your_client_id
set SPOTIFY_CLIENT_SECRET=your_client_secret
set LASTFM_API_KEY=your_lastfm_api_key
```

Then run the sync script pointing to a Spotify playlist ID and your target directory:

```cmd
python sync.py --playlist 37i9dQZF1DX10zKzsJ2jva --out "D:\Music\Synthwave"
```

If you don't want to set environment variables, you can pass them directly as arguments:

```cmd
python sync.py --playlist 37i9dQZF1DX10zKzsJ2jva --out "D:\Music\Synthwave" --spotify-id "xxx" --spotify-secret "yyy"
```

To skip Last.fm tagging entirely, just don't provide the API key.

<!-- refreshed: 2026-09-14 -->
