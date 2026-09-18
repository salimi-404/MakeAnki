import csv


INPUT_FILE = "menschen_vocab.csv"
OUTPUT_FILE = "menschen_vocab_final.csv"


REMOVE_WORDS = {
    "Berufe",
    "Familienstand",
    "Zahlen",
}



def fix_word(word):

    word = word.strip()


    replacements = {
        "Diplom-informatiker": "Diplom-Informatiker",
        "It-spezialist": "IT-Spezialist",
    }


    if word in replacements:
        return replacements[word]


    return word



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

            german = fix_word(
                row["German"]
            )


            if german in REMOVE_WORDS:
                continue


            rows.append({

                "German": german,

                "Persian": row["Persian"],

                "Example": row["Example"],

                "Example Persian": row["Example Persian"]

            })



    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:


        writer = csv.DictWriter(
            f,
            fieldnames=[
                "German",
                "Persian",
                "Example",
                "Example Persian"
            ]
        )


        writer.writeheader()

        writer.writerows(rows)



    print("Done!")
    print(
        "Created:",
        OUTPUT_FILE
    )

    print(
        "Words:",
        len(rows)
    )



if __name__ == "__main__":
    main()