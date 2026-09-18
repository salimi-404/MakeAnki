import asyncio
import csv
import hashlib
import os
import re

import edge_tts
import genanki


VOICE = "de-DE-KatjaNeural"

CSV_FILE = "menschen_vocab_final.csv"

AUDIO_DIR = "audio"

TEMPLATE_DIR = "templates"

OUTPUT_FILE = "Menschen_A1.1.apkg"


DECK_NAME = "Menschen A1.1"


# ID های کاملاً جدید
MODEL_ID = 4567891230
DECK_ID = 4567891231


MODEL_NAME = "Menschen_A1.1_Passive_Model"



os.makedirs(
    AUDIO_DIR,
    exist_ok=True
)



def read_template(filename):

    path = os.path.join(
        TEMPLATE_DIR,
        filename
    )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()



style_css = read_template("style.css")

front_de_fa = read_template("front_de_fa.html")

back_de_fa = read_template("back_de_fa.html")





def clean_filename(text):

    text = text.lower().strip()

    text = re.sub(
        r"[^a-zA-Z0-9äöüß]+",
        "_",
        text
    )

    return text[:50]





def generate_guid(text):

    # GUID مخصوص Menschen
    value = (
        "MENSCHEN_A1_1_PASSIVE_"
        + text.lower().strip()
    )


    digest = hashlib.md5(
        value.encode("utf-8")
    ).hexdigest()


    return int(digest,16) % (10**10)






async def generate_audio(text, prefix):

    if not text.strip():
        return ""


    filename = (
        f"{prefix}_{clean_filename(text)}.mp3"
    )


    path = os.path.join(
        AUDIO_DIR,
        filename
    )


    if os.path.exists(path):

        return filename



    try:

        communicate = edge_tts.Communicate(
            text,
            VOICE
        )


        await communicate.save(
            path
        )


        print(
            "[audio]",
            text
        )


        return filename


    except Exception as e:

        print(
            "[audio error]",
            text,
            e
        )

        return ""






anki_model = genanki.Model(

    MODEL_ID,

    MODEL_NAME,


    fields=[

        {"name":"PureWord"},

        {"name":"FullWord"},

        {"name":"Plural"},

        {"name":"Meaning"},

        {"name":"Example_DE"},

        {"name":"Example_FA"},

        {"name":"Grammar"},

        {"name":"Tags"},

        {"name":"WordAudio"},

        {"name":"ExampleAudio"},

    ],



    templates=[

        {

            "name":"Deutsch -> Persisch",

            "qfmt":front_de_fa,

            "afmt":back_de_fa,

        }

    ],


    css=style_css

)





deck = genanki.Deck(

    DECK_ID,

    DECK_NAME

)







async def main():

    media_files = []

    processed = set()



    with open(

        CSV_FILE,

        "r",

        encoding="utf-8-sig",

        newline=""

    ) as file:


        reader = csv.DictReader(file)



        for row in reader:


            german = (
                row.get("German")
                or ""
            ).strip()



            if not german:

                continue



            key = german.lower()



            if key in processed:

                continue



            processed.add(key)



            persian = (
                row.get("Persian")
                or ""
            ).strip()



            example_de = (
                row.get("Example")
                or ""
            ).strip()



            example_fa = (
                row.get("Example Persian")
                or ""
            ).strip()



            print(
                "[card]",
                german
            )



            word_audio = await generate_audio(
                german,
                "w"
            )


            example_audio = await generate_audio(
                example_de,
                "e"
            )



            if word_audio:

                media_files.append(
                    os.path.join(
                        AUDIO_DIR,
                        word_audio
                    )
                )



            if example_audio:

                media_files.append(
                    os.path.join(
                        AUDIO_DIR,
                        example_audio
                    )
                )




            note = genanki.Note(

                model=anki_model,


                fields=[

                    german,        # PureWord

                    german,        # FullWord

                    "",            # Plural

                    persian,       # Meaning

                    example_de,    # Example_DE

                    example_fa,    # Example_FA

                    "",            # Grammar

                    "Menschen_A1.1",


                    (
                        f"[sound:{word_audio}]"
                        if word_audio
                        else ""
                    ),



                    (
                        f"[sound:{example_audio}]"
                        if example_audio
                        else ""
                    )

                ],



                guid=generate_guid(
                    german
                ),



                tags=[
                    "Menschen_A1.1"
                ]

            )


            deck.add_note(note)






    package = genanki.Package(deck)


    package.media_files = list(
        dict.fromkeys(media_files)
    )



    package.write_to_file(
        OUTPUT_FILE
    )



    print()
    print("====================")
    print("DONE")
    print("FILE:", OUTPUT_FILE)
    print("NOTES:", len(processed))
    print("====================")







if __name__ == "__main__":

    asyncio.run(main())