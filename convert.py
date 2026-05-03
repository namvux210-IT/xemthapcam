#!/usr/bin/env python3
import json
import urllib.request
import os
import sys
from datetime import datetime, timezone

JSON_URL      = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/thapcam.json"
OUTPUT_FILE   = "thapcam.m3u"
PLAYLIST_NAME = "ThapCam Live Sports"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_best_url(stream_links):
    """Lấy URL tốt nhất từ stream_links, ưu tiên HLS default=true"""
    if not stream_links:
        return None
    # Ưu tiên link có default=true
    for lnk in stream_links:
        if lnk.get("default") is True and lnk.get("url", "").startswith("http"):
            return lnk["url"]
    # Nếu không có default, lấy link đầu tiên có URL hợp lệ
    for lnk in stream_links:
        if lnk.get("url", "").startswith("http"):
            return lnk["url"]
    return None


def extract_channels(data):
    channels = []

    # Root là dict có key "channels"
    if isinstance(data, dict):
        items = data.get("channels", [])
    elif isinstance(data, list):
        items = data
    else:
        return channels

    for item in items:
        if not isinstance(item, dict):
            continue

        name    = item.get("name", "Kenh")
        logo    = item.get("image", "") or item.get("logo", "") or item.get("thumb_key", "")
        display = item.get("display", "contain")

        # Lấy tên nhóm từ org_metadata nếu có
        org  = item.get("org_metadata") or {}
        league = org.get("league", "") if isinstance(org, dict) else ""
        group  = league or "The thao"

        # Lấy danh sách streams
        streams = item.get("streams", [])
        if not streams:
            # Thử lấy URL trực tiếp nếu có
            direct = item.get("url") or item.get("stream_url") or item.get("src")
            if direct and direct.startswith("http"):
                channels.append({"name": name, "url": direct, "logo": logo, "group": group})
            continue

        # Mỗi stream có stream_links
        added = False
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            stream_links = stream.get("stream_links", [])
            url = get_best_url(stream_links)
            if url:
                stream_name = stream.get("name", "")
                display_name = f"{name} ({stream_name})" if stream_name and stream_name != "KT" else name
                channels.append({
                    "name":  display_name,
                    "url":   url,
                    "logo":  logo,
                    "group": group,
                })
                added = True
                break  # Chỉ lấy stream đầu tiên có URL hợp lệ

        if not added:
            print(f"  [skip] {name} - khong co URL hop le")

    return channels


def main():
    print(f"[*] Fetching {JSON_URL}")
    try:
        data = fetch_json(JSON_URL)
    except Exception as e:
        print(f"[!] Loi fetch: {e}")
        sys.exit(1)

    channels = extract_channels(data)
    print(f"[+] Tong so kenh: {len(channels)}")

    if not channels:
        print("[!] Khong tim thay kenh nao!")
        sys.exit(1)

    print("[*] Mau 5 kenh dau:")
    for ch in channels[:5]:
        print(f"    {ch['name']} | {ch['group']} | {ch['url'][:60]}")

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

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[OK] Luu: {out} ({os.path.getsize(out)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
