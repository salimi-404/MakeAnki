import csv
import re


INPUT_FILE = "extracted_vocab.csv"
OUTPUT_FILE = "menschen_vocab.csv"


FIELDS = [
    "German",
    "Persian",
    "Example",
    "Example Persian",
]


def clean_german(word):

    if not word:
        return ""

    word = word.strip()


    # حذف موارد مثل:
    # Journalistin, "-nen"
    # Architekt, "-en"

    word = re.sub(
        r',\s*".*?"$',
        '',
        word
    )


    word = re.sub(
        r',\s*[-\w]+$',
        '',
        word
    )


    return word.strip()



def main():

    rows = []

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)


        for row in reader:

            german = clean_german(
                row.get("German", "")
            )


            if not german:
                continue


            rows.append({

                "German": german,

                "Persian": row.get(
                    "Persian",
                    ""
                ).strip(),

                "Example": row.get(
                    "Example",
                    ""
                ).strip(),

                "Example Persian": row.get(
                    "Example Persian",
                    ""
                ).strip(),

            })



    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:


        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS
        )

        writer.writeheader()

        writer.writerows(rows)



    print("Done")
    print(
        "Created:",
        OUTPUT_FILE
    )
    print(
        "Rows:",
        len(rows)
    )



if __name__ == "__main__":
    main()