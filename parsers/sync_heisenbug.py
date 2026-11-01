#!/usr/bin/env python3
"""Sync heisenbug_speakers.json into the speaker .md files of every community.

For each Heisenbug speaker, tries to find a matching community speaker by name
(Russian first, then English). For every matched speaker, appends missing talks
to their external_talks list. Skips talks whose URL is already recorded.

Usage:
    python parsers/sync_heisenbug.py             # apply changes
    python parsers/sync_heisenbug.py --dry-run   # preview only
    python parsers/sync_heisenbug.py piterqa     # one community only
"""

import json
import sys
import argparse
from pathlib import Path
from common import (
    load_speakers,
    resolve_sites,
    build_name_index,
    find_speaker,
    save_speaker,
    norm_url,
)

HEISENBUG_JSON = Path(__file__).parent.parent / "heisenbug_speakers.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying files")
    parser.add_argument("sites", nargs="*",
                        help="communities from sites/ (default: all of them)")
    args = parser.parse_args()

    if not HEISENBUG_JSON.exists():
        print(f"ERROR: {HEISENBUG_JSON} not found. Run collect_heisenbug.py first.")
        sys.exit(1)

    raw = json.loads(HEISENBUG_JSON.read_text(encoding="utf-8"))
    heisenbug_speakers = raw.get("speakers", {})
    print(f"Loaded {len(heisenbug_speakers)} Heisenbug speakers from {HEISENBUG_JSON.name}")

    total_matched = 0
    total_added = 0

    # Спикеры у каждого сообщества свои: один и тот же человек может быть
    # и в Moscow QA, и в Piter QA — тогда доклады допишутся в оба файла.
    for site in resolve_sites(args.sites):
        community_speakers = load_speakers(site.speakers_dir)
        name_index = build_name_index(community_speakers)
        print(f"[{site.id}] Loaded {len(community_speakers)} "
              f"{site.config['title']} speakers\n")

        for hb_speaker in heisenbug_speakers.values():
            # Try matching by Russian name first, then English
            mq_speaker = None
            matched_as = ""
            for name_field in ("name_ru", "name_en"):
                candidate = hb_speaker.get(name_field, "").strip()
                if candidate:
                    mq_speaker = find_speaker(name_index, candidate)
                    if mq_speaker:
                        matched_as = candidate
                        break

            if not mq_speaker:
                continue

            talks = hb_speaker.get("talks", [])
            if not talks:
                continue

            # Build talk entries in our format, skip already-recorded URLs
            # Deduplicate by URL within this batch too (same talk can appear in multiple slots)
            seen_in_batch: set[str] = set()
            new_entries = []
            for t in talks:
                url = t["url"]
                url_key = norm_url(url)
                if url_key in mq_speaker["existing_urls"] or url_key in seen_in_batch:
                    continue
                seen_in_batch.add(url_key)
                new_entries.append({
                    "title": t.get("title_ru") or t.get("title_en", ""),
                    "event": t["edition"],
                    "date": t.get("date", ""),
                    "url": url,
                    "slides_url": t.get("slides_url", ""),
                })

            if not new_entries:
                continue

            total_matched += 1
            print(f"  {mq_speaker['name']} ← matched as '{matched_as}'")
            for e in new_entries:
                print(f"    + [{e['event']}] {e['title'][:65]}")

            if not args.dry_run:
                added = save_speaker(mq_speaker, new_entries)
                total_added += added
            else:
                total_added += len(new_entries)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done.")
    print(f"Matched speakers: {total_matched}")
    print(f"{'Would add' if args.dry_run else 'Added'}: {total_added} talks")


if __name__ == "__main__":
    main()