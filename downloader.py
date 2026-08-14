import os
import httpx
from pathlib import Path
import yt_dlp
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, APIC

class AudioDownloader:
    def __init__(self, dest_dir, lfm_key=None):
        self.dest_dir = Path(dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.lfm_key = lfm_key
        self.http = httpx.Client(timeout=10.0)

    def search_and_download(self, artist, title):
        # FIXME: some tracks have characters like '/' or ':' that yt-dlp replaces differently. Needs proper mapping.
        query = f"ytsearch1:{artist} - {title} audio"
        
        temp_template = str(self.dest_dir / "%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if not info or 'entries' not in info or not info['entries']:
                raise RuntimeError(f"Could not find video for {artist} - {title}")
            
            video_id = info['entries'][0]['id']
            temp_mp3 = self.dest_dir / f"{video_id}.mp3"
            
            safe_title = "".join(c for c in f"{artist} - {title}" if c.isalnum() or c in " -_().")
            final_path = self.dest_dir / f"{safe_title}.mp3"
            
            if final_path.exists():
                os.remove(final_path)
            
            if temp_mp3.exists():
                os.rename(temp_mp3, final_path)
            else:
                mp3_files = list(self.dest_dir.glob("*.mp3"))
                if mp3_files:
                    newest = max(mp3_files, key=os.path.getctime)
                    os.rename(newest, final_path)
                else:
                    raise FileNotFoundError("Downloaded MP3 not found after yt-dlp post-processing")

            self.enrich_and_tag(final_path, artist, title)
            return final_path

    def enrich_and_tag(self, file_path, artist, title):
        album = None
        genre = None
        img_data = None
        
        if self.lfm_key:
            try:
                url = "http://ws.audioscrobbler.com/2.0/"
                params = {
                    "method": "track.getInfo",
                    "api_key": self.lfm_key,
                    "artist": artist,
                    "track": title,
                    "format": "json"
                }
                r = self.http.get(url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    track_info = data.get("track", {})
                    
                    album_info = track_info.get("album", {})
                    album = album_info.get("title")
                    
                    tags = track_info.get("toptags", {}).get("tag", [])
                    # # print(f"Loaded {len(tags)} tags from Last.fm")
                    if tags:
                        genre = tags[0].get("name")
                    
                    images = album_info.get("image", [])
                    if images:
                        img_url = None
                        for sz in ["extralarge", "large", "medium"]:
                            for img in images:
                                if img.get("size") == sz and img.get("#text"):
                                    img_url = img["#text"]
                                    break
                            if img_url:
                                break
                        
                        if img_url:
                            img_res = self.http.get(img_url)
                            if img_res.status_code == 200:
                                img_data = img_res.content
            except httpx.HTTPError:
                # Carry on with default tags if Last.fm lookup fails
                pass

        try:
            tags = ID3(file_path)
        except mutagen.id3.ID3NoHeaderError:
            tags = ID3()
        
        tags['TIT2'] = TIT2(encoding=3, text=title)
        tags['TPE1'] = TPE1(encoding=3, text=artist)
        
        if album:
            tags['TALB'] = TALB(encoding=3, text=album)
        if genre:
            tags['TCON'] = TCON(encoding=3, text=genre)
            
        if img_data:
            tags['APIC'] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_data
            )
            
        tags.save(file_path)
