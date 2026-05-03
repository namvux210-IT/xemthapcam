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
    if not stream_links:
        return None
    for lnk in stream_links:
        if lnk.get("default") is True and str(lnk.get("url", "")).startswith("http"):
            return lnk["url"]
    for lnk in stream_links:
        if str(lnk.get("url", "")).startswith("http"):
            return lnk["url"]
    return None


def extract_channels(data):
    channels = []

    groups = data.get("groups", [])
    print(f"[*] So nhom (groups): {len(groups)}")

    for group in groups:
        group_name = group.get("name", "The thao").strip()
        # Bỏ emoji khỏi tên nhóm nếu cần
        group_name = group_name.encode("ascii", "ignore").decode() or group_name

        ch_list = group.get("channels", [])
        print(f"  [group] '{group_name}' - {len(ch_list)} kenh")

        for ch in ch_list:
            ch_name = ch.get("name", "Kenh").strip()
            ch_logo = (ch.get("image") or {}).get("url", "") if isinstance(ch.get("image"), dict) else ""

            sources = ch.get("sources", [])
            added = False

            for src in sources:
                src_name = src.get("name", "")
                contents = src.get("contents", [])

                for content in contents:
                    streams = content.get("streams", [])

                    for stream in streams:
                        stream_links = stream.get("stream_links", [])
                        url = get_best_url(stream_links)

                        if url:
                            display = f"{ch_name}"
                            channels.append({
                                "name":  display,
                                "url":   url,
                                "logo":  ch_logo,
                                "group": group_name if group_name else "The thao",
                            })
                            added = True
                            break  # Chỉ lấy stream đầu tiên có URL

                    if added:
                        break
                if added:
                    break

            if not added:
                print(f"    [skip] '{ch_name}' - khong co URL")

    return channels


def main():
    print(f"[*] Fetching {JSON_URL}")
    try:
        data = fetch_json(JSON_URL)
    except Exception as e:
        print(f"[!] Loi fetch: {e}")
        sys.exit(1)

    channels = extract_channels(data)
    print(f"\n[+] Tong so kenh hop le: {len(channels)}")

    if not channels:
        print("[!] Khong co kenh nao!")
        sys.exit(1)

    print("[*] 5 kenh dau:")
    for ch in channels[:5]:
        print(f"    {ch['name']} | {ch['group']} | {ch['url'][:70]}")

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

    size = os.path.getsize(out) / 1024
    print(f"[OK] Luu thanh cong: {out} ({size:.1f} KB) - {len(channels)} kenh")


if __name__ == "__main__":
    main()
