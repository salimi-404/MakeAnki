"""Build a one-card-per-row Anki deck from simple custom CSV files.

Required CSV columns: Front, Back
Optional columns: Meaning, Tags
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import html
import re
from pathlib import Path

import genanki

VOICE = "de-DE-KatjaNeural"
OUTPUT_DIR = Path("custom_decks")

CARD_CSS = """
.card { font-family: Arial, sans-serif; background: #f2f4f7; color: #222;
        font-size: 22px; text-align: center; padding: 24px; }
.container { background: #fff; border-radius: 18px; padding: 28px 20px;
             max-width: 620px; margin: 0 auto; box-shadow: 0 4px 18px #0001; }
.label { color: #667085; font-size: 12px; text-transform: uppercase;
         letter-spacing: 1px; margin-bottom: 18px; }
.main { font-size: 30px; font-weight: 700; line-height: 1.45; }
.answer { color: #1670c5; }
.meaning { direction: rtl; text-align: right; color: #a65d00;
           border-top: 1px solid #ddd; margin-top: 22px; padding-top: 18px;
           font-size: 21px; line-height: 1.7; }
.tags { color: #888; font-size: 11px; margin-top: 22px; }
.nightMode .card { background: #18191a; color: #eee; }
.nightMode .container { background: #242526; }
"""

FRONT_TEMPLATE = """
<div class="container">
  <div class="label">{{Tags}}</div>
  <div class="main">{{Front}}</div>
  {{#Audio}}<div>{{Audio}}</div>{{/Audio}}
</div>
"""

BACK_TEMPLATE = """
{{FrontSide}}
<hr id="answer">
<div class="container">
  <div class="main answer">{{Back}}</div>
  {{#Meaning}}<div class="meaning">{{Meaning}}</div>{{/Meaning}}
  <div class="tags">{{Tags}}</div>
</div>
"""


def stable_id(value: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}|{value}".encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") & 0x7FFFFFFF) or 1


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE).strip("._")
    return (value or "custom_deck")[:80]


def unique_output_path(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def normalize_tags(value: str) -> list[str]:
    tags = []
    for tag in re.split(r"[;,]", value or ""):
        tag = re.sub(r"\s+", "_", tag.strip())
        if tag:
            tags.append(tag)
    return tags or ["Custom_CSV"]


async def make_audio(text: str, output_dir: Path) -> tuple[str, str]:
    if not text.strip():
        return "", ""
    try:
        import edge_tts
        filename = f"custom_{safe_filename(text)}.mp3"
        path = output_dir / filename
        if not path.exists():
            await edge_tts.Communicate(text, VOICE).save(str(path))
        return filename, str(path)
    except Exception as exc:
        print(f"[audio warning] Could not create audio for {text!r}: {exc}")
        return "", ""


def read_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header.")

        # Accept headers with accidental surrounding whitespace.
        original_headers = reader.fieldnames
        header_map = {header.strip().casefold(): header for header in original_headers if header}
        missing = [name for name in ("front", "back") if name not in header_map]
        if missing:
            raise ValueError(
                "CSV must contain Front and Back columns. "
                f"Missing: {', '.join(name.title() for name in missing)}"
            )

        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for line_number, raw in enumerate(reader, start=2):
            row = {
                key: (raw.get(source) or "").strip()
                for key, source in header_map.items()
            }
            front = row.get("front", "")
            back = row.get("back", "")
            if not front and not back:
                continue
            if not front or not back:
                print(f"[skip] Row {line_number}: Front or Back is empty.")
                continue
            dedupe_key = front.casefold()
            if dedupe_key in seen:
                print(f"[skip] Duplicate Front value: {front}")
                continue
            seen.add(dedupe_key)
            rows.append({
                "front": front,
                "back": back,
                "meaning": row.get("meaning", ""),
                "tags": row.get("tags", ""),
            })

    if not rows:
        raise ValueError("No valid cards were found in the CSV.")
    return rows, list(header_map.keys())


async def build_deck(csv_path: Path, deck_name: str, output_path: Path,
                     with_audio: bool = False) -> Path:
    rows, _ = read_rows(csv_path)
    output_path = unique_output_path(output_path)

    model_id = stable_id(deck_name, "MakeAnki.CustomCSV.Model.v1")
    deck_id = stable_id(deck_name, "MakeAnki.CustomCSV.Deck.v1")
    model = genanki.Model(
        model_id,
        f"MakeAnki Custom CSV - {deck_name}",
        fields=[
            {"name": "Front"}, {"name": "Back"}, {"name": "Meaning"},
            {"name": "Tags"}, {"name": "Audio"},
        ],
        templates=[{
            "name": "Custom CSV Card",
            "qfmt": FRONT_TEMPLATE,
            "afmt": BACK_TEMPLATE,
        }],
        css=CARD_CSS,
    )
    deck = genanki.Deck(deck_id, deck_name)
    media_files: list[str] = []

    for index, row in enumerate(rows, start=1):
        audio_tag = ""
        if with_audio:
            _, audio_path = await make_audio(row["front"], Path("audio"))
            if audio_path:
                media_files.append(audio_path)
                audio_tag = f"[sound:{Path(audio_path).name}]"

        tags = normalize_tags(row["tags"])
        note = genanki.Note(
            model=model,
            fields=[
                html.escape(row["front"]),
                html.escape(row["back"]).replace("\n", "<br>"),
                html.escape(row["meaning"]).replace("\n", "<br>"),
                html.escape(", ".join(tags)),
                audio_tag,
            ],
            guid=stable_id(row["front"], f"MakeAnki.CustomCSV.{deck_name}"),
            tags=tags,
        )
        deck.add_note(note)
        print(f"[card {index}/{len(rows)}] {row['front']}")

    package = genanki.Package(deck)
    package.media_files = list(dict.fromkeys(media_files))
    package.write_to_file(str(output_path))
    print(f"\n[done] Created: {output_path}")
    print(f"[notes] {len(rows)}")
    print(f"[cards] {len(rows)} (one card per CSV row)")
    return output_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a custom Anki deck from Front/Back CSV data.")
    parser.add_argument("--csv", dest="csv_file", help="Path to the source CSV")
    parser.add_argument("--name", dest="deck_name", help="Anki deck name")
    parser.add_argument("--output", help="Output .apkg path (default: custom_decks/<name>.apkg)")
    parser.add_argument("--audio", action="store_true", help="Generate German audio for Front values")
    args = parser.parse_args()

    csv_value = args.csv_file or input("CSV file path: ").strip().strip('"')
    if not csv_value:
        print("[cancelled] No CSV file selected.")
        return

    csv_path = Path(csv_value).expanduser()
    default_name = csv_path.stem.replace("_", " ").replace("-", " ").title()
    deck_name = args.deck_name or input(f"Deck name [{default_name}]: ").strip() or default_name
    audio_answer = "y" if args.audio else input("Generate German audio? [y/N]: ").strip().lower()
    with_audio = audio_answer in {"y", "yes", "1"}

    output_value = args.output or str(OUTPUT_DIR / f"{safe_filename(deck_name)}.apkg")
    output_path = Path(output_value).expanduser()
    if output_path.suffix.lower() != ".apkg":
        output_path = output_path.with_suffix(".apkg")

    try:
        await build_deck(csv_path, deck_name, output_path, with_audio)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"[error] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
