import io
import json
import re
import time
from http.cookies import SimpleCookie
from typing import Tuple
import random
import time

from curl_cffi import requests
from curl_cffi.requests import Cookies
from fake_useragent import UserAgent
from rich import print
from typing import Union

from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())

ua = UserAgent(browsers=["edge"])

get_session_url = (
    "https://clerk.suno.com/v1/client/?_clerk_js_version=4.72.0-snapshot.vc141245"
)
exchange_token_url = "https://clerk.suno.com/v1/client/sessions/{sid}/tokens/api?_clerk_js_version=4.72.0-snapshot.vc141245"

base_url = "https://studio-api.suno.ai"
browser_version = "edge101"

HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) \
        Gecko/20100101 Firefox/117.0",
}

MUSIC_GENRE_LIST = [
    "African",
    "Asian",
    "South and southeast Asian",
    "Avant-garde",
    "Blues",
    "Caribbean and Caribbean-influenced",
    "Comedy",
    "Country",
    "Easy listening",
    "Electronic",
    "Folk",
    "Hip hop",
    "Jazz",
    "Latin",
    "Pop",
    "R&B and soul",
    "Rock",
]


class SongsGen:
    def __init__(self, cookie: str) -> None:
        self.session: requests.Session = requests.Session()
        HEADERS["user-agent"] = ua.random
        self.cookie = cookie
        self.session.cookies = self.parse_cookie_string(self.cookie)
        auth_token = self._get_auth_token()
        HEADERS["Authorization"] = f"Bearer {auth_token}"
        self.session.headers = HEADERS
        self.sid = None
        self.retry_time = 0
        # make the song_info_dict global since we can get the lyrics and song name first
        self.song_info_dict = {}
        self.song_info_dict["song_url_list"] = []
        # now data
        self.now_data = {}

    def _get_auth_token(self):
        response = self.session.get(get_session_url, impersonate=browser_version)
        data = response.json()
        r = data.get("response")
        sid = None
        if r:
            sid = r.get("last_active_session_id")
        if not sid:
            raise Exception("Failed to get session id")
        self.sid = sid
        response = self.session.post(
            exchange_token_url.format(sid=sid), impersonate=browser_version
        )
        data = response.json()
        return data.get("jwt")

    def _renew_auth_token(self):
        auth_token = self._get_auth_token()
        HEADERS["Authorization"] = f"Bearer {auth_token}"
        self.session.headers = HEADERS

    @staticmethod
    def parse_cookie_string(cookie_string):
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {}
        for key, morsel in cookie.items():
            cookies_dict[key] = morsel.value
        return Cookies(cookies_dict)

    def get_song_library(self):
        self._renew_auth_token()
        page_number = 1
        result = []
        while 1:
            print(f"Getting page {page_number} data.")
            url = f"https://studio-api.suno.ai/api/feed/?page={page_number}"
            response = self.session.get(url, impersonate=browser_version)
            data = response.json()
            if page_number == 3:
                break
            if len(data) < 20:
                result.extend(data)
                break
            # spider rulef
            time.sleep(2)
            if page_number % 3 == 0:
                self._renew_auth_token()
            page_number += 1
            result.extend(data)
        return result

    def get_limit_left(self) -> int:
        self.session.headers["user-agent"] = ua.random
        r = self.session.get(
            "https://studio-api.suno.ai/api/billing/info/", impersonate=browser_version
        )
        return int(r.json()["total_credits_left"] / 10)

    def _parse_lyrics(self, data: dict) -> Tuple[str, str]:
        song_name = data.get("title", "")
        mt = data.get("metadata")
        if (
            not mt
        ):  # Remove checking for title because custom songs have no title if not specified
            return "", ""
        lyrics = re.sub(r"\[.*?\]", "", mt.get("prompt"))
        return song_name, lyrics

    def _fetch_songs_metadata(self, ids):
        id1, id2 = ids[:2]
        url = f"https://studio-api.suno.ai/api/feed/?ids={id1}%2C{id2}"
        response = self.session.get(url, impersonate=browser_version)
        data = response.json()
        if type(data) == dict:
            if data.get("detail", "") == "Unauthorized":
                song_name, lyric = self._parse_lyrics(self.now_data[0])
                self.song_info_dict["song_name"] = song_name
                self.song_info_dict["lyric"] = lyric
                self.song_info_dict["song_url"] = (
                    f"https://audiopipe.suno.ai/?item_id={id1}"
                )
                self.song_info_dict["id"] = id1
                
                print("Token expired, will sleep 30 seconds and try to download")
                time.sleep(30)
                # Done here
                return True
            else:
                data = [data]
        # renew now data
        self.now_data = data
        try:
            if all(d.get("audio_url") for d in data):
                for d in data:
                    song_name, lyric = self._parse_lyrics(d)
                    self.song_info_dict["song_name"] = song_name
                    self.song_info_dict["lyric"] = lyric
                    self.song_info_dict["song_url_list"].append(d.get("audio_url"))
                    # for support old api
                    self.song_info_dict["song_url"] = d.get("audio_url")
                    self.song_info_dict["id"] = id1
                return True
            return False
        except Exception as e:
            print(e)
            print("Will sleep 30s and get the music url")
            time.sleep(30)
            song_name, lyric = self._parse_lyrics(self.now_data[0])
            self.song_info_dict["song_name"] = song_name
            self.song_info_dict["lyric"] = lyric
            self.song_info_dict["song_url_list"] = [
                f"https://audiopipe.suno.ai/?item_id={id1}",
                f"https://audiopipe.suno.ai/?item_id={id2}",
            ]
            self.song_info_dict["song_url"] = (
                f"https://audiopipe.suno.ai/?item_id={id1}"
            )
            self.song_info_dict["id"] = id1
            # Done here
            return True

    def get_songs(
        self,
        prompt: str,
        tags: Union[str, None] = None,
        title: str = "",
        make_instrumental: bool = False,
        is_custom: bool = False,
    ) -> dict:
        url = f"{base_url}/api/generate/v2/"
        self.session.headers["user-agent"] = ua.random
        payload = {
            "gpt_description_prompt": prompt,
            "mv": "chirp-v3-0",
            "prompt": "",
            "make_instrumental": make_instrumental,
        }
        if is_custom:
            payload["prompt"] = prompt
            payload["gpt_description_prompt"] = ""
            payload["title"] = title
            if not tags:
                payload["tags"] = random.choice(MUSIC_GENRE_LIST)
            else:
                payload["tags"] = tags
            print(payload)
        response = self.session.post(
            url,
            data=json.dumps(payload),
            impersonate=browser_version,
        )
        if not response.ok:
            print(response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        songs_meta_info = response_body["clips"]
        request_ids = [i["id"] for i in songs_meta_info]
        start_wait = time.time()
        print("Waiting for results...")
        print(".", end="", flush=True)
        sleep_time = 10
        while True:
            if int(time.time() - start_wait) > 600:
                raise Exception("Request timeout")

            song_info = self._fetch_songs_metadata(request_ids)

            if sleep_time > 2:
                time.sleep(sleep_time)
                sleep_time -= 1
            else:
                time.sleep(2)

            if not song_info:
                print(".", end="", flush=True)
            else:
                break
        
        return self.song_info_dict

    def save_songs(
        self,
        prompt: str,
        tags: Union[str, None] = None,
        title: Union[str, None] = None,
        make_instrumental: bool = False,
        is_custom: bool = False,
    ) -> None:
        try:
            self.get_songs(
                prompt,
                tags=tags,
                title=title,
                is_custom=is_custom,
                make_instrumental=make_instrumental,
            )  # make the info dict
            song_name = self.song_info_dict["song_name"]
            lyric = self.song_info_dict["lyric"]
            id = str(self.song_info_dict["id"])
            link = f"https://cdn1.suno.ai/{id}.mp3"
            image = f"https://cdn1.suno.ai/image_{id}.png"

        except Exception as e:
            print(e)
            raise
        print(link)

        while True:
            start_time = time.time()
            response = requests.get(link)
            access_denied = re.search("<Code>(.*?)</Code>", response.text)
            if access_denied and access_denied.group(1) == 'AccessDenied':
                time.sleep(3)
            else:
                audio_data = io.BytesIO(response.content)
                return True,song_name,link,lyric,image,audio_data
            if time.time() - start_time > 160:
                return False
            