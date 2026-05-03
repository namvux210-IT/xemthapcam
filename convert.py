#!/usr/bin/env python3
"""
ThapCam JSON → M3U Converter
Tự động fetch JSON từ nguồn và xuất file M3U chuẩn IPTV.
"""

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime, timezone

# ─── CẤU HÌNH ────────────────────────────────────────────────────────────────
JSON_URL   = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/thapcam.json"
OUTPUT_FILE = "thapcam.m3u"
PLAYLIST_NAME = "ThapCam Live Sports"
DEFAULT_GROUP = "Thể thao"

# Danh sách field ưu tiên để tự động detect
NAME_FIELDS  = ["name", "title", "channel_name", "channel", "ten", "label", "Name"]
URL_FIELDS   = ["url", "stream", "link", "stream_url", "m3u_url", "source", "src", "Url", "URL"]
LOGO_FIELDS  = ["logo", "icon", "thumb", "thumbnail", "image", "img", "Logo"]
GROUP_FIELDS = ["group", "category", "sport", "type", "group-title", "genre", "Group"]
# ─────────────────────────────────────────────────────────────────────────────


def fetch_json(url: str) -> dict | list:
    print(f"[*] Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    print(f"[+] Fetched OK — type={type(data).__name__}")
    return data


def find_array(data: dict | list) -> list:
    """Tìm mảng kênh trong JSON dù cấu trúc lồng nhau."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Thử các key phổ biến trước
        for key in ("channels", "items", "data", "streams", "list", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        # Tìm key bất kỳ chứa list
        for val in data.values():
            if isinstance(val, list) and len(val) > 0:
                return val
    return []


def detect_field(sample: dict, candidates: list[str]) -> str | None:
    """Tìm field phù hợp trong một dict mẫu."""
    keys_lower = {k.lower(): k for k in sample.keys()}
    for c in candidates:
        if c in sample:
            return c
        if c.lower() in keys_lower:
            return keys_lower[c.lower()]
    return None


def get_val(item: dict, field: str | None) -> str:
    if not field or field not in item:
        return ""
    val = item[field]
    if isinstance(val, list):
        val = val[0] if val else ""
    return str(val).strip() if val is not None else ""


def build_m3u(channels: list, name_f, url_f, logo_f, group_f) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f'#EXTM3U x-tvg-url="" x-playlist-title="{PLAYLIST_NAME}"',
        f'# Cập nhật: {now} | Nguồn: {JSON_URL}',
    ]

    count = 0
    skipped = 0
    for i, ch in enumerate(channels):
        url = get_val(ch, url_f)
        if not url or not url.startswith(("http", "rtmp", "rtsp")):
            skipped += 1
            continue

        name  = get_val(ch, name_f)  or f"Kênh {i+1}"
        logo  = get_val(ch, logo_f)  or ""
        group = get_val(ch, group_f) or DEFAULT_GROUP

        lines.append(
            f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}'
        )
        lines.append(url)
        count += 1

    print(f"[+] Tổng kênh hợp lệ: {count} | Bỏ qua: {skipped}")
    return "\n".join(lines) + "\n"


def main():
    try:
        data = fetch_json(JSON_URL)
    except urllib.error.URLError as e:
        print(f"[!] Lỗi fetch: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[!] Lỗi parse JSON: {e}")
        sys.exit(1)

    channels = find_array(data)
    if not channels:
        print("[!] Không tìm thấy dữ liệu kênh trong JSON!")
        sys.exit(1)

    print(f"[*] Tìm thấy {len(channels)} kênh")

    sample = channels[0]
    print(f"[*] Các field trong JSON: {list(sample.keys())}")

    name_f  = detect_field(sample, NAME_FIELDS)
    url_f   = detect_field(sample, URL_FIELDS)
    logo_f  = detect_field(sample, LOGO_FIELDS)
    group_f = detect_field(sample, GROUP_FIELDS)

    print(f"[*] Mapping: name={name_f} | url={url_f} | logo={logo_f} | group={group_f}")

    if not url_f:
        print("[!] Không tìm thấy field URL. Vui lòng kiểm tra JSON và cập nhật URL_FIELDS.")
        sys.exit(1)

    m3u = build_m3u(channels, name_f, url_f, logo_f, group_f)

    out_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(m3u)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"[✓] Đã lưu: {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
