import os
import zipfile
import sqlite3
import json
import tempfile
import csv


BACKUP_FILE = "backUp/collection-20260705001609.colpkg"

OUTPUT_FILE = "extracted_vocab.csv"


# مدل‌هایی که احتمال می‌دهیم دک لغت باشند
TARGET_MODELS = [
    "Mamad_Ultimate_Model_V2",
    "Mamad_Click_Audio_Model",
    "Mamad_Audio_Model",
    "Mamad_TwoWay_Model",
]


def extract_database(backup_file):

    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(backup_file, "r") as z:

        database_name = None

        for name in z.namelist():

            if name == "collection.anki21":
                database_name = name
                break

            if name == "collection.anki2":
                database_name = name


        if not database_name:
            raise Exception(
                "collection database not found"
            )


        output = os.path.join(
            temp_dir,
            database_name
        )


        with z.open(database_name) as src:
            with open(output, "wb") as dst:
                dst.write(src.read())


        return output



def load_models(cursor):

    cursor.execute(
        "SELECT models FROM col"
    )

    result = cursor.fetchone()

    if not result:
        raise Exception(
            "models not found"
        )


    return json.loads(result[0])



def find_target_models(models):

    result = {}

    for model_id, model in models.items():

        name = model["name"]

        if name in TARGET_MODELS:

            result[int(model_id)] = model


    return result



def get_field_names(model):

    return [
        field["name"]
        for field in model["flds"]
    ]

def convert_note(fields, field_names):

    data = dict(
        zip(
            field_names,
            fields
        )
    )


    pure_word = (
        data.get("PureWord")
        or ""
    ).strip()


    full_word = (
        data.get("FullWord")
        or ""
    ).strip()


    if not pure_word:
        return None


    german = pure_word


    article = ""


    # استخراج آرتیکل از FullWord
    if full_word:

        parts = full_word.split()

        if len(parts) >= 2:

            first = parts[0].lower()

            if first in [
                "der",
                "die",
                "das"
            ]:
                article = first
                german = " ".join(parts[1:])


    # بزرگ کردن اسم‌ها
    grammar = (
        data.get("Grammar")
        or ""
    ).strip()


    if grammar.lower() in [
        "nomen",
        "noun"
    ]:
        german = german.capitalize()



    meaning = (
        data.get("Meaning")
        or ""
    ).strip()


    example_de = (
        data.get("Example_DE")
        or data.get("Example")
        or ""
    ).strip()


    example_fa = (
        data.get("Example_FA")
        or ""
    ).strip()


    lesson = (
        data.get("Lesson")
        or ""
    ).strip()


    tags = "A1"

    if lesson:
        tags = f"A1_Lektion_{lesson}"


    return {

        "German": german,

        "Type": grammar,

        "Article": article,

        "Plural": "",

        "Persian": meaning,

        "Example": example_de,

        "Example Persian": example_fa,

        "Tags": tags
    }


def extract_notes(db_path):

    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()


    models = load_models(cursor)


    target_models = find_target_models(models)


    if not target_models:

        raise Exception(
            "No target models found"
        )


    print("\nModels found:")

    for model in target_models.values():

        print(
            "-",
            model["name"]
        )



    rows = []

    seen = set()



    for model_id, model in target_models.items():


        field_names = get_field_names(model)



        cursor.execute(
            """
            SELECT flds
            FROM notes
            WHERE mid = ?
            """,
            (model_id,)
        )


        notes = cursor.fetchall()


        print(
            model["name"],
            "notes:",
            len(notes)
        )



        for note in notes:


            fields = note[0].split("\x1f")


            row = convert_note(
                fields,
                field_names
            )


            if not row:
                continue



            key = row["German"].lower()



            if key in seen:
                continue



            seen.add(key)

            rows.append(row)



    conn.close()


    return rows



def save_csv(rows):

    headers = [

        "German",
        "Type",
        "Article",
        "Plural",
        "Persian",
        "Example",
        "Example Persian",
        "Tags"

    ]


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:


        writer = csv.DictWriter(
            f,
            fieldnames=headers
        )


        writer.writeheader()


        writer.writerows(rows)



def main():


    print(
        "[1] Extracting database..."
    )


    db = extract_database(
        BACKUP_FILE
    )


    print(
        "[2] Reading notes..."
    )


    rows = extract_notes(
        db
    )


    print(
        "[3] Saving CSV..."
    )


    save_csv(
        rows
    )


    print()
    print(
        "Done!"
    )

    print(
        "Extracted notes:",
        len(rows)
    )

    print(
        "File:",
        OUTPUT_FILE
    )



if __name__ == "__main__":
    main()