import asyncio
import csv
import hashlib
import os
import re

import edge_tts
import genanki

VOICE = "de-DE-KatjaNeural"
AUDIO_DIR = "audio"
CSV_FILE = "my_vocab.csv"
TEMPLATE_DIR = "templates"

# تعیین نام فایل خروجی از طریق ترمینال
custom_name = input("Enter output file name (default: Goethe_A1_Wortschatz): ").strip()
if not custom_name:
    custom_name = "Goethe_A1_Wortschatz"

custom_name = re.sub(r'\.apkg$', '', custom_name, flags=re.IGNORECASE)
OUTPUT_FILE = f"{custom_name}.apkg"

DECK_NAME = "Goethe A1 Wortschatz"
MODEL_NAME = "Goethe_A1_2Way_Model"

MODEL_ID = 1607392320
DECK_ID = 2059400110

REQUIRED_FIELDS = [
    "German",
    "Type",
    "Article",
    "Plural",
    "Persian",
    "Example",
    "Example Persian",
    "Tags",
]

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)


def read_template_file(filename, default_content=""):
    path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(default_content)
        return default_content


# خواندن استایل و قالب‌ها
style_css = read_template_file("style.css", "/* CSS style */")
front_de_fa = read_template_file("front_de_fa.html", "<div>{{FullWord}}</div>")
back_de_fa = read_template_file("back_de_fa.html", "<div>{{Meaning}}</div>")
front_fa_de = read_template_file("front_fa_de.html", "<div>{{Meaning}}</div>")
back_fa_de = read_template_file("back_fa_de.html", "<div>{{FullWord}}</div>")


def clean_filename(text):
    if not text:
        return "empty"
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z0-9äöüß]+", "_", text)
    return text.strip("_")[:50] or "empty"


def generate_guid(text):
    normalized = text.lower().strip()
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return int(digest, 16) % (10 ** 10)


async def generate_audio(text, prefix):
    if not text or not text.strip() or text.lower().strip() == "none":
        return "", ""

    filename = f"{prefix}_{clean_filename(text)}.mp3"
    path = os.path.join(AUDIO_DIR, filename)

    if os.path.exists(path):
        return filename, path

    try:
        communicator = edge_tts.Communicate(text, VOICE)
        await communicator.save(path)
        print(f"[audio] generated: {text}")
        return filename, path
    except Exception as exc:
        print(f"[audio] failed for '{text}': {exc}")
        return "", ""


def build_full_word(word, word_type, article):
    """
    فقط آرتیکل + کلمه را می‌سازد.
    جمع (Plural) در فیلد جداگانه ذخیره می‌شود و روی Front نمایش داده می‌شود.
    """
    word_type = (word_type or "").strip().lower()
    article = (article or "").strip()

    if word_type == "noun":
        has_article = any(
            word.lower().startswith(a + " ")
            for a in ["der", "die", "das"]
        )

        if article and not has_article:
            return f"{article} {word}"

    return word


def normalize_plural(word_type, plural):
    """
    فقط برای اسم‌ها جمع را نگه می‌دارد.
    اگر مقدار '-' یا خالی باشد، رشته خالی برمی‌گرداند تا در Front نمایش داده نشود.
    """
    word_type = (word_type or "").strip().lower()
    plural = (plural or "").strip()

    if word_type == "noun" and plural and plural != "-":
        return plural

    return ""


def normalize_tags(tag_string):
    if not tag_string:
        return ["A1"]

    result = []
    for tag in tag_string.split(";"):
        cleaned = re.sub(r"\s+", "_", tag.strip())
        if cleaned:
            result.append(cleaned)

    return result or ["A1"]


# مدل Anki
anki_model = genanki.Model(
    MODEL_ID,
    MODEL_NAME,
    fields=[
        {"name": "PureWord"},
        {"name": "FullWord"},
        {"name": "Plural"},
        {"name": "Meaning"},
        {"name": "Example_DE"},
        {"name": "Example_FA"},
        {"name": "Grammar"},
        {"name": "Tags"},
        {"name": "WordAudio"},
        {"name": "ExampleAudio"},
    ],
    templates=[
        {
            "name": "Card 1: DE -> FA",
            "qfmt": front_de_fa,
            "afmt": back_de_fa,
        },
        {
            "name": "Card 2: FA -> DE",
            "qfmt": front_fa_de,
            "afmt": back_fa_de,
        }
    ],
    css=style_css,
)

deck = genanki.Deck(DECK_ID, DECK_NAME)


async def main():
    media_files = []
    processed_words = set()

    if not os.path.exists(CSV_FILE):
        print(f"[error] CSV file not found: {CSV_FILE}")
        return

    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            print("[error] CSV file is empty or has no header.")
            return

        missing_fields = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
        if missing_fields:
            print("[error] CSV header is invalid.")
            print(f"[error] missing fields: {missing_fields}")
            return

        for row in reader:
            german_word = (row.get("German") or "").strip()
            if not german_word or german_word.lower() == "german":
                continue

            normalized_word = german_word.lower()
            if normalized_word in processed_words:
                continue

            processed_words.add(normalized_word)

            word_type = (row.get("Type") or "noun").strip()
            article = (row.get("Article") or "").strip()
            plural = (row.get("Plural") or "").strip()
            persian = (row.get("Persian") or "").strip()
            example_de = (row.get("Example") or "").strip()
            example_fa = (row.get("Example Persian") or "").strip()
            tags_str = (row.get("Tags") or "A1").strip()

            full_word = build_full_word(german_word, word_type, article)
            plural_value = normalize_plural(word_type, plural)

            note_tags = normalize_tags(tags_str)
            display_tags = ", ".join(note_tags)

            print(f"[process] {german_word}")

            word_audio_file, word_audio_path = await generate_audio(german_word, "w")
            if word_audio_path:
                media_files.append(word_audio_path)

            example_audio_file, example_audio_path = await generate_audio(example_de, "e")
            if example_audio_path:
                media_files.append(example_audio_path)

            note = genanki.Note(
                model=anki_model,
                fields=[
                    german_word,
                    full_word,
                    plural_value,
                    persian,
                    example_de,
                    example_fa,
                    word_type.upper(),
                    display_tags,
                    f"[sound:{word_audio_file}]" if word_audio_file else "",
                    f"[sound:{example_audio_file}]" if example_audio_file else "",
                ],
                guid=generate_guid(german_word),
                tags=note_tags,
            )
            deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = list(dict.fromkeys(media_files))

    try:
        package.write_to_file(OUTPUT_FILE)
        print()
        print("[done] Anki package created successfully.")
        print(f"[file] {OUTPUT_FILE}")
        print(f"[notes] {len(processed_words)}")
        print(f"[total cards] {len(processed_words) * 2}")
    except Exception as exc:
        print(f"[error] failed to write package: {exc}")


if __name__ == "__main__":
    asyncio.run(main())