#!/usr/bin/env python3
import json
import urllib.request
import os
import sys
from datetime import datetime, timezone

JSON_URL      = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/thapcam.json"
OUTPUT_FILE   = "thapcam.m3u"
PLAYLIST_NAME = "ThapCam Live Sports"
DEFAULT_UA    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_headers(request_headers):
    referer = ""
    ua = DEFAULT_UA
    if isinstance(request_headers, list):
        for h in request_headers:
            k = str(h.get("key", "")).lower().strip()
            v = str(h.get("value", "")).strip()
            if k == "referer":
                referer = v
            elif k == "user-agent":
                ua = v
    return referer, ua


def get_best_link(stream_links):
    if not stream_links:
        return None, "", ""
    # Ưu tiên default=true
    for lnk in stream_links:
        if lnk.get("default") is True and str(lnk.get("url", "")).startswith("http"):
            ref, ua = parse_headers(lnk.get("request_headers", []))
            return lnk["url"], ref, ua
    # Fallback: link đầu tiên có URL hợp lệ
    for lnk in stream_links:
        url = str(lnk.get("url", ""))
        if url.startswith("http"):
            ref, ua = parse_headers(lnk.get("request_headers", []))
            return url, ref, ua
    return None, "", ""


def extract_channels(data):
    channels = []
    groups = data.get("groups", [])
    print(f"[*] So nhom: {len(groups)}")

    for group in groups:
        group_name = group.get("name", "The thao").strip()
        ch_list = group.get("channels", [])

        for ch in ch_list:
            ch_name = ch.get("name", "Kenh").strip()
            img = ch.get("image")
            ch_logo = img.get("url", "") if isinstance(img, dict) else ""

            added = False
            for src in ch.get("sources", []):
                for content in src.get("contents", []):
                    for stream in content.get("streams", []):
                        url, referer, ua = get_best_link(stream.get("stream_links", []))
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
                    if added: break
                if added: break

    print(f"[+] Tong kenh: {len(channels)}")
    return channels


def build_m3u(channels):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f'#EXTM3U x-playlist-title="{PLAYLIST_NAME}"',
        f'# Cap nhat: {now}',
    ]

    for ch in channels:
        url     = ch["url"]
        name    = ch["name"]
        logo    = ch["logo"]
        group   = ch["group"]
        referer = ch["referer"]
        ua      = ch["ua"]

        # --- EXTINF với http-referrer và http-user-agent ---
        # Được hỗ trợ bởi: TiviMate, IPTV Smarters Pro, GSE IPTV
        extinf = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}"'
        if referer:
            extinf += f' http-referrer="{referer}"'
        extinf += f' http-user-agent="{ua}"'
        extinf += f',{name}'
        lines.append(extinf)

        # --- #EXTVLCOPT để VLC đọc được ---
        if referer:
            lines.append(f'#EXTVLCOPT:http-referrer={referer}')
        lines.append(f'#EXTVLCOPT:http-user-agent={ua}')

        # --- URL thuần (không pipe) ---
        # Một số app đọc EXTINF headers tốt hơn pipe
        lines.append(url)

    return "\n".join(lines) + "\n"


def main():
    print(f"[*] Fetching {JSON_URL}")
    try:
        data = fetch_json(JSON_URL)
    except Exception as e:
        print(f"[!] Loi: {e}")
        sys.exit(1)

    channels = extract_channels(data)

    if not channels:
        print("[!] Khong co kenh nao!")
        sys.exit(1)

    print("[*] 3 kenh mau:")
    for ch in channels[:3]:
        print(f"    {ch['name']} | {ch['url'][:60]}")
        print(f"    referer: {ch['referer'][:50] if ch['referer'] else 'none'}")

    m3u = build_m3u(channels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    print(f"[OK] Saved: {out} ({os.path.getsize(out)/1024:.1f} KB) | {len(channels)} kenh")


if __name__ == "__main__":
    main()
