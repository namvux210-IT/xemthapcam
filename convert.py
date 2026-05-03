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


def get_headers(stream_links_item):
    """Lấy Referer và User-Agent từ request_headers nếu có"""
    referer = ""
    ua = "Mozilla/5.0"
    headers = stream_links_item.get("request_headers", [])
    if isinstance(headers, list):
        for h in headers:
            k = h.get("key", "").lower()
            v = h.get("value", "")
            if k == "referer":
                referer = v
            elif k == "user-agent":
                ua = v
    return referer, ua


def get_best_link(stream_links):
    """Lấy link tốt nhất (default=true trước), trả về (url, referer, ua)"""
    if not stream_links:
        return None, "", ""
    # Ưu tiên default=true
    for lnk in stream_links:
        if lnk.get("default") is True and str(lnk.get("url", "")).startswith("http"):
            ref, ua = get_headers(lnk)
            return lnk["url"], ref, ua
    # Fallback link đầu tiên có URL
    for lnk in stream_links:
        if str(lnk.get("url", "")).startswith("http"):
            ref, ua = get_headers(lnk)
            return lnk["url"], ref, ua
    return None, "", ""


def extract_channels(data):
    channels = []
    groups = data.get("groups", [])
    print(f"[*] So nhom: {len(groups)}")

    for group in groups:
        group_name = group.get("name", "The thao")
        # Giữ emoji trong tên nhóm
        ch_list = group.get("channels", [])
        print(f"  [group] '{group_name}' - {len(ch_list)} kenh")

        for ch in ch_list:
            ch_name = ch.get("name", "Kenh").strip()
            img = ch.get("image")
            ch_logo = img.get("url", "") if isinstance(img, dict) else ""

            sources = ch.get("sources", [])
            added = False

            for src in sources:
                contents = src.get("contents", [])
                for content in contents:
                    streams = content.get("streams", [])
                    for stream in streams:
                        stream_links = stream.get("stream_links", [])
                        url, referer, ua = get_best_link(stream_links)
                        if url:
                            channels.append({
                                "name":    ch_name,
                                "url":     url,
                                "logo":    ch_logo,
                                "group":   group_name,
                                "referer": referer,
                                "ua":      ua,
                            })
                            added = True
                            break
                    if added:
                        break
                if added:
                    break

            if not added:
                print(f"    [skip] '{ch_name}' - khong co URL")

    return channels


def build_m3u(channels):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f'#EXTM3U x-playlist-title="{PLAYLIST_NAME}"',
        f'# Cap nhat: {now} | Nguon: {JSON_URL}',
    ]
    for ch in channels:
        url = ch["url"]

        # Nhúng header vào URL theo chuẩn M3U
        # Cách 1: dùng pipe |, hỗ trợ bởi TiviMate, IPTV Smarters
        extra = ""
        if ch["referer"]:
            extra += f"|Referer={ch['referer']}"
        if ch["ua"]:
            extra += f"|User-Agent={ch['ua']}"

        extinf = (
            f'#EXTINF:-1'
            f' tvg-name="{ch["name"]}"'
            f' tvg-logo="{ch["logo"]}"'
            f' group-title="{ch["group"]}"'
        )
        if ch["referer"]:
            extinf += f' http-referrer="{ch["referer"]}"'
        if ch["ua"]:
            extinf += f' http-user-agent="{ch["ua"]}"'
        extinf += f',{ch["name"]}'

        lines.append(extinf)
        lines.append(url + extra)

    return "\n".join(lines) + "\n"


def main():
    print(f"[*] Fetching {JSON_URL}")
    try:
        data = fetch_json(JSON_URL)
    except Exception as e:
        print(f"[!] Loi fetch: {e}")
        sys.exit(1)

    channels = extract_channels(data)
    print(f"\n[+] Tong kenh: {len(channels)}")

    if not channels:
        print("[!] Khong co kenh nao!")
        sys.exit(1)

    print("[*] 3 kenh dau:")
    for ch in channels[:3]:
        print(f"    {ch['name']} | ref={ch['referer'][:40] if ch['referer'] else 'none'}")

    m3u = build_m3u(channels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    print(f"[OK] Luu: {out} ({os.path.getsize(out)/1024:.1f} KB) - {len(channels)} kenh")


if __name__ == "__main__":
    main()
