# Custom CSV Deck Builder

The custom deck builder is an additional workflow. It does not change the existing Goethe vocabulary or Menschen scripts.

## CSV format

Save a CSV file as UTF-8 (Excel's **CSV UTF-8** option is recommended). The required headers are `Front` and `Back`. Optional headers are `Meaning` and `Tags`.

```csv
Front,Back,Meaning,Tags
Deutschland,Berlin,پایتخت آلمان,Laender_Hauptstaedte
der Deutsche,آلمانی (مذکر),,Nationalitaeten
beginnen,begann / hat begonnen,شروع کردن,Unregelmaessige_Verben
```

The column names are case-insensitive. Every valid row creates exactly **one Anki card**. Duplicate Front values are skipped.

## Run

Install dependencies:

```bash
python -m pip install -r requirements-custom-builder.txt
```

Interactive mode:

```bash
python build_custom_deck.py
```

Or pass options directly:

```bash
python build_custom_deck.py --csv "Nationalitaeten.csv" --name "German Nationalities"
python build_custom_deck.py --csv "Laender_Hauptstaedte.csv" --name "German Capitals" --audio
python build_custom_deck.py --csv "Unregelmaessige_Verben.csv" --name "Irregular Verbs" --output "custom_decks/verbs.apkg"
```

The builder asks whether to generate German audio unless `--audio` is supplied. Audio generation uses Edge TTS and requires an internet connection. If audio generation fails, cards are still created without audio.

Output files are written to `custom_decks/` by default. Existing output files are never overwritten; a numeric suffix is added instead.

## Import into Anki

Open Anki and choose **File → Import**, then select the generated `.apkg` file (or double-click it). The deck uses a separate model and deterministic IDs so it remains independent of the existing Goethe and Menschen note types.
