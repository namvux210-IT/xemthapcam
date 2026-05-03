#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime, timezone

JSON_URL      = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/thapcam.json"
OUTPUT_FILE   = "thapcam.m3u"
PLAYLIST_NAME = "ThapCam Live Sports"
DEFAULT_GROUP = "The thao"

NAME_FIELDS  = ["name", "title", "channel_name", "channel", "ten", "label"]
URL_FIELDS   = ["url", "stream", "link", "stream_url", "m3u_url", "source", "src", "hls", "hls_url"]
LOGO_FIELDS  = ["logo", "icon", "thumb", "thumbnail", "image", "img"]
GROUP_FIELDS = ["group", "category", "sport", "type", "group-title", "genre", "display"]


def fetch_json(url):
    print(f"[*] Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print(f"[+] Fetched OK - type={type(data).__name__}")
    return data


def detect_field(sample, candidates):
    keys_lower = {k.lower(): k for k in sample.keys()}
    for c in candidates:
        if c in sample:
            return c
        if c.lower() in keys_lower:
            return keys_lower[c.lower()]
    return None


def get_val(item, field):
    if not field or field not in item:
        return ""
    val = item[field]
    if isinstance(val, list):
        val = val[0] if val else ""
    return str(val).strip() if val is not None else ""


def collect_channels(data):
    """
    Thu thập tất cả kênh từ JSON dù cấu trúc phẳng hay lồng nhau.
    Hỗ trợ:
      - Mảng phẳng: [{name, url}, ...]
      - Object có key chứa mảng: {channels: [{...}]}
      - Mảng các nhóm lồng nhau: [{name, channels: [{url,...}]}]
    """
    channels = []

    def walk(obj, group_name=None):
        if isinstance(obj, list):
            for item in obj:
                walk(item, group_name)
        elif isinstance(obj, dict):
            # Kiểm tra nếu item này có field URL -> đây là kênh
            url_f = detect_field(obj, URL_FIELDS)
            if url_f:
                url = get_val(obj, url_f)
                if url and url.startswith(("http", "rtmp", "rtsp")):
                    name_f  = detect_field(obj, NAME_FIELDS)
                    logo_f  = detect_field(obj, LOGO_FIELDS)
                    group_f = detect_field(obj, GROUP_FIELDS)
                    channels.append({
                        "name":  get_val(obj, name_f)  or "Kenh",
                        "url":   url,
                        "logo":  get_val(obj, logo_f)  or "",
                        "group": group_name or get_val(obj, group_f) or DEFAULT_GROUP,
                    })
                    return

            # Không có URL -> tìm key nào là list để đệ quy vào
            # Lấy tên nhóm từ field name nếu có
            grp = group_name
            name_f = detect_field(obj, NAME_FIELDS)
            if name_f:
                grp = get_val(obj, name_f) or group_name

            for key, val in obj.items():
                if isinstance(val, (list, dict)):
                    walk(val, grp)

    walk(data)
    return channels


def build_m3u(channels):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f'#EXTM3U x-playlist-title="{PLAYLIST_NAME}"',
        f'# Cap nhat: {now} | Nguon: {JSON_URL}',
    ]
    for ch in channels:
        lines.append(
            f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}'
        )
        lines.append(ch["url"])
    return "\n".join(lines) + "\n"


def main():
    try:
        data = fetch_json(JSON_URL)
    except Exception as e:
        print(f"[!] Loi fetch: {e}")
        sys.exit(1)

    channels = collect_channels(data)
    print(f"[+] Tong kenh tim duoc: {len(channels)}")

    if not channels:
        print("[!] Khong tim thay kenh nao co URL hop le!")
        sys.exit(1)

    # In vài kênh mẫu để kiểm tra
    for ch in channels[:3]:
        print(f"    -> {ch['name']} | {ch['group']} | {ch['url'][:60]}")

    m3u = build_m3u(channels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    print(f"[OK] Luu thanh cong: {out} ({os.path.getsize(out)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
