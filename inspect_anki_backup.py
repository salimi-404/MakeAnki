import os
import zipfile
import sqlite3
import json
import tempfile


# BACKUP_FILE = "backup.apkg"   # اسم فایل بکاپ خودت را اینجا بگذار
BACKUP_FILE = "backUp/collection-20260705001609.colpkg"

def extract_collection(apkg_path):

    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(apkg_path, "r") as z:

        print("[files inside backup]")
        for name in z.namelist():
            print(" -", name)

        for target in [
            "collection.anki21",
            "collection.anki2"
        ]:
            if target in z.namelist():
                output = os.path.join(temp_dir, target)

                with z.open(target) as src:
                    with open(output, "wb") as dst:
                        dst.write(src.read())

                return output

    raise Exception(
        "collection database not found"
    )


def inspect_database(db_path):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    print("\n===== TABLES =====")

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )

    for row in cursor.fetchall():
        print(row[0])


    print("\n===== NOTE TYPES =====")


    cursor.execute(
        "SELECT models FROM col"
    )

    models = cursor.fetchone()[0]

    models = json.loads(models)


    for model_id, model in models.items():

        print("\n----------------")
        print("Model:", model["name"])

        print("Fields:")

        for field in model["flds"]:
            print(
                "  -",
                field["name"]
            )


    print("\n===== SAMPLE NOTES =====")


    cursor.execute(
        """
        SELECT id, mid, flds
        FROM notes
        LIMIT 5
        """
    )


    for note in cursor.fetchall():

        print("\nNOTE ID:", note[0])
        print("MODEL:", note[1])

        print("FIELDS:")

        fields = note[2].split("\x1f")

        for i, f in enumerate(fields):
            print(
                i,
                ":",
                f[:100]
            )


    conn.close()



if __name__ == "__main__":

    db = extract_collection(BACKUP_FILE)

    print("\nDatabase extracted:")
    print(db)

    inspect_database(db)
