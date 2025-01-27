from openai import OpenAI
from selenium.webdriver import Keys
from selenium.webdriver.support.wait import WebDriverWait

from credentials import OPENAI_API_KEY, NOTION_API_KEY, CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
import requests
from pydantic import BaseModel
from typing import Optional
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
import psutil


# IMPORTANT: Notion to Anki flow
# 1. Take initial notes in Notion: Unstructured section.
# 2. Automation of organization and improvement with ChatGPT API: A script organizes notes directly in Notion.

NOTION_BASE_URL = "https://api.notion.com/v1"

allowed_block_types = ["paragraph", "heading_1", "heading_2", "heading_3"]
ignored_block_types = ["divider"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

class Card(BaseModel):
        question: str
        answer: str
        image: Optional[str]
class Anki(BaseModel):
        anki: list[Card]

def get_notion_page_content(page_id):
    # Get the content of the first block level of a Notion page
    url = f"{NOTION_BASE_URL}/blocks/{page_id}/children"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    print("Página de Notion obtenida con éxito")
    return response.json()

def format_with_openai(notes, language):
    prompt = ""
    if language == "es":
        prompt_1 = """
                Tu tarea consiste en revisar, corregir y organizar los apuntes de los cursos de matemáticas y programación. Tu objetivo es transformar estos apuntes potencialmente desorganizados, incompletos o incorrectos en un conjunto bien estructurado de flashcards al estilo Anki. Estos son los apuntes con los que trabajarás:

                <notas>
                """

        prompt_2 = """
                </notas>

                Sigue estos pasos para procesar las notas:

                1. Lea detenidamente todo el conjunto de notas.

                2. Identifique y corrija cualquier error o inexactitud en la información.

                3. Completar cualquier concepto o información que falte y que sea necesaria para una comprensión completa del tema.

                4. Establecer y aclarar conexiones entre diferentes ideas y conceptos.

                5. Añadir el contexto necesario para mejorar la comprensión del tema.

                6. Organizar la información en conceptos discretos que puedan transformarse en pares pregunta-respuesta.

                7. Crear flashcards al estilo Anki formulando preguntas claras y concisas y respuestas completas para cada concepto.

                8. Si los apuntes hacen referencia a imágenes, incluye el enlace de la imagen en la parte de la respuesta de la flashcard.

                Al redactar preguntas y respuestas
                - Asegúrese de que las preguntas sean específicas y sin ambigüedades.
                - Proporcione respuestas detalladas que expliquen completamente el concepto.
                - Utilice un lenguaje claro, conciso y adecuado al tema.
                - Incluya ejemplos o aplicaciones pertinentes cuando proceda.

                Formatee su resultado como un objeto JSON con la siguiente estructura:
                {
                  "anki": [
                    {
                      "question": "Tu pregunta aquí",
                      "answer": "Tu respuesta aquí",
                      "image": "Enlace de imagen aquí (si procede, de lo contrario omita este campo)"
                    },
                    {
                      "question": "Siguiente pregunta",
                      "answer": "Siguiente respuesta"
                    }
                  ]
                }

                Notas importantes sobre las imágenes:
                - Si se hace referencia a una imagen en las notas (por ejemplo, "En la figura 7 se puede ver..."), incluya el enlace de la imagen en el campo "image" de la flashcard correspondiente.
                - Sólo incluya el campo "imagen" si hay una referencia de imagen real para esa flashcard específica.
                - Asegurate de incluir todas las imagenes en al menos una flashcard.
                - No te limites en la cantidad de flashcards que creas necesarias para cubrir todos los conceptos y temas de los apuntes.

                Acuérdate de procesar toda la información de las notas, creando tantas fichas como sea necesario para cubrir todos los conceptos e ideas importantes. El objetivo es crear un conjunto completo de fichas que ayuden a los alumnos a repasar y reforzar su comprensión de los temas de matemáticas y programación tratados en los apuntes originales.
                El formato de respuesta debe ser solo un objeto JSON con la estructura dada. No incluya ninguna información adicional en su respuesta.
                """
        prompt = prompt_1 + notes + prompt_2
    elif language == "en":
        prompt_1 = """
                Your task is to review, correct, and organize the notes from the math and programming courses. Your goal is to transform these potentially disorganized, incomplete, or incorrect notes into a well-structured set of Anki-style flashcards. Here are the notes you'll be working with:

                <notes>
                """

        prompt_2 = """
                </notes>

                Follow these steps to process the notes:

                1. Read through the entire set of notes carefully.

                2. Identify and correct any errors or inaccuracies in the information.

                3. Fill in any missing concepts or information that is necessary for a complete understanding of the topic.

                4. Establish and clarify connections between different ideas and concepts.

                5. Add any necessary context to enhance the understanding of the topic.

                6. Organize the information into discrete concepts that can be transformed into question-answer pairs.

                7. Create Anki-style flashcards by formulating clear and concise questions and complete answers for each concept.

                8. If the notes reference images, include the image link in the answer part of the flashcard.

                When crafting questions and answers:
                - Ensure that questions are specific and unambiguous.
                - Provide detailed answers that fully explain the concept.
                - Use clear, concise language that is appropriate to the topic.
                - Include relevant examples or applications where appropriate.

                Format your output as a JSON object with the following structure:
                {
                  "anki": [
                    {
                      "question": "Your question here",
                      "answer": "Your answer here",
                      "image": "Image link here (if applicable, otherwise omit this field)"
                    },
                    {
                      "question": "Next question",
                      "answer": "Next answer"
                    }
                  ]
                }

                Important notes about images:
                - If an image is referenced in the notes (e.g., "Figure 7 shows..."), include the image link in the "image" field of the corresponding flashcard.
                - Only include the "image" field if there is an actual image reference for that specific flashcard.
                - Make sure to include all images in at least one flashcard.
                - Do not limit yourself in the number of flashcards you create to cover all the important concepts and topics from the notes.

                Remember to process all the information from the notes, creating as many cards as necessary to cover all the important concepts and ideas. The goal is to create a comprehensive set of cards that will help students review and reinforce their understanding of the math and programming topics covered in the original notes. 
                The response format should be a JSON object with the given structure only. Do not include any additional information in your response.
                """
        prompt = prompt_1 + notes + prompt_2


    """
    Using structured output to get the response in JSON format
    """


    client = OpenAI(
        api_key= OPENAI_API_KEY
    )
    # Assuming max_tokens is by default the maximum value
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant helping a student organize their notes into Anki flashcards."},
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=Anki,
    )

    response_parsed = completion.choices[0].message.parsed
    print("Contenido formateado con éxito")
    return response_parsed

def update_notion_page(page_id, formatted_content):
    """Actualiza una página de Notion con contenido en formato toggle list."""
    url = f"{NOTION_BASE_URL}/blocks/{page_id}/children"
    # Convertir el contenido formateado en bloques de Notion
    toggle_blocks = []
    for card in formatted_content.anki:
        toggle_block ={
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [
                    {
                        "type": "text",
                        "text":
                        {
                            "content": card.question,
                            "link": None
                        }
                    }
                ],
                "color": "default",
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text":
                                    {
                                        "content": card.answer,
                                        "link": None
                                    }
                                }
                            ],
                            "color": "default"
                        }
                    }
                ]
            }
        }
        if card.image is not None:
            toggle_block["toggle"]["children"].append({
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": card.image
                    }
                }
            })
        toggle_blocks.append(toggle_block)
    # Send data to existing page
    data = {"children": toggle_blocks}
    response = requests.patch(url, headers=HEADERS, json=data)
    response.raise_for_status()
    print("Página de Notion actualizada con éxito")

    # Create a new temporary page with the content
    new_page_data = {
        "parent": {
            "type": "page_id",
            "page_id": page_id
        },
        "properties": {
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": "TempPage"
                        }
                    }
                ]
            }
        },
        "children": toggle_blocks

    }
    response = requests.post(f"{NOTION_BASE_URL}/pages", headers=HEADERS, json=new_page_data)
    response.raise_for_status()
    temp_page_url = response.json()["url"]
    print("Página de Notion temporal creada con exito")

    return temp_page_url

def process_raw_notion_page(page_content):

    if not os.path.exists("images"):
        os.makedirs("images")


    cloudinary.config(
            cloud_name = CLOUDINARY_CLOUD_NAME,
            api_key = CLOUDINARY_API_KEY,
            api_secret = CLOUDINARY_API_SECRET,
            secure=True
        )
    clean_content = []
    for block in page_content["results"]:
        try:
            temp_type = block["type"]
            if temp_type in allowed_block_types:
                if len(block[temp_type]["rich_text"]) == 0:
                    continue
                clean_content.append(block[temp_type]["rich_text"][0]["plain_text"])
            elif temp_type == "image":
                image_info = ""
                if block[temp_type]["caption"]:
                    image_info = block[temp_type]["caption"][0]["plain_text"]
                # Save the image locally
                temp_image = requests.get(block[temp_type]["file"]["url"]).content
                new_image_path = f"images/{block['id']}.png"
                with open(new_image_path, "wb") as f:
                    f.write(temp_image)
                # Post the image to Cloudinary
                new_url_image = cloudinary.uploader.upload(new_image_path)


                image_info = image_info + " : " + new_url_image["url"]
                clean_content.append(image_info)
            elif temp_type in ignored_block_types:
                pass
            else :
                print("Block type not supported", temp_type)
        except Exception as e:
            print("Error processing block:", block)


    clean_content = "\n".join(clean_content)
    print("Contenido de Notion procesado con éxito")
    return clean_content

def notion_to_notion(page_id_source, page_id_destine, language):

    # IMPORTANT: This code only support the first level of blocks of a Notion page and certain block types

    try:
        raw_page_content = get_notion_page_content(page_id_source)
        # extract only the text content from the page
        processed_page_content = process_raw_notion_page(raw_page_content)

        # return a JSON object with the structure of the Anki object
        formatted_content = format_with_openai(processed_page_content, language)


        # Updated Notion page (appends the new content)
        temp_page_url = update_notion_page(page_id_destine, formatted_content)
        print("Done")
        return temp_page_url

    except Exception as e:
        print("Error:", e)

def notion_to_2anki(temp_page_url):
    try:

        # Open Chrome with new profile bc of the remote debugging and default profile looks corrupted
        # whateva is the directory where the new profile was created
        port_chrome = 8989
        os.system(f'start chrome --remote-debugging-port={port_chrome} --user-data-dir=C:\\Code\\whateva"')
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "localhost:8989")
        driver = webdriver.Chrome(options=chrome_options)
        time.sleep(5)

        """
        Notion
        """

        # Assuming you are already logged in Notion
        driver.get(temp_page_url)
        time.sleep(5)
        driver.find_element(By.CLASS_NAME, "notion-topbar-more-button").click()
        time.sleep(1)

        # Get the export button by its svg icon
        menu_item_with_arrow = driver.find_element(By.CSS_SELECTOR, 'div[role="menuitem"] svg.arrowUpLine')
        export_button = menu_item_with_arrow.find_element(By.XPATH, './ancestor::div[@role="menuitem"]')
        export_button.click()
        time.sleep(1)

        """
        If HTML was selected previously, the selection will be remembered
        """
        # # Open the export format menu
        # markdown_div = driver.find_element(By.XPATH, '//div[text()="Markdown & CSV"]')
        # markdown_div.click()
        # time.sleep(1)
        #
        # # Select HTML format
        # html_div = driver.find_element(By.XPATH, '//div[text()="HTML"]')
        # html_div.click()
        # time.sleep(1)

        # Click Export button
        export_button = driver.find_element(By.XPATH, '//div[text()="Export"]')
        export_button.click()
        time.sleep(1)
        # Wait until the dialog of waiting for the export is gone
        WebDriverWait(driver, 60).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "notion-dialog"))
        )
        time.sleep(3)

        """
        2Anki
        """

        # IMPORTANT: There is no guarantee that latest file is the correct one
        # Get the latest zip that contains the Notion page in the downloads folder
        download_folder = r'C:\Users\Usuario\Downloads'
        latest_file_path = get_latest_file_with_extension(download_folder, '.zip')

        # Verification if the file was created at maximum 5 minutes ago
        is_the_correct_file = verify_file_creation_time(latest_file_path, 300)
        if not is_the_correct_file:
            print("The file was not created in the last 5 minutes")
            exit(1)

        driver.get("https://2anki.net/")
        time.sleep(5)

        # Upload the notion page in .zip format
        file_input = driver.find_element(By.CLASS_NAME, 'file-input')
        file_input.send_keys(latest_file_path)
        time.sleep(5) # Wait for the file to be uploaded

        # Wait for the Anki deck to be downloaded
        download_wait(download_folder, 60)

        latest_anki_deck_file_path = get_latest_file_with_extension(download_folder, '.apkg')
        # Verification if the file was created at maximum 5 minutes ago
        is_the_correct_file = verify_file_creation_time(latest_anki_deck_file_path, 300)
        if not is_the_correct_file:
            print("The file was not created in the last 5 minutes")
            exit(1)


        cerrar_chrome_por_puerto(port_chrome)
        driver.quit()

        # return the path of Notion page zip and the Anki deck file
        return latest_file_path, latest_anki_deck_file_path
    except Exception as e:
        print("Error in notion_to_2anki:", e)

def encontrar_proceso_por_puerto(puerto):
    for process in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            if process.info['name'] == 'chrome.exe':
                for conn in process.connections(kind='inet'):
                    if conn.laddr.port == puerto:  # Verifica si el puerto coincide
                        return process  # Devuelve el proceso si lo encuentra
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return None

def cerrar_chrome_por_puerto(puerto):
    proceso = encontrar_proceso_por_puerto(puerto)
    if proceso:
        proceso.terminate()  # Finaliza el proceso
        print(f"Proceso de Chrome en el puerto {puerto} cerrado.")
    else:
        print(f"No se encontró un proceso de Chrome en el puerto {puerto}.")

def download_wait(directory, timeout):
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < timeout:
        time.sleep(1)
        dl_wait = False
        for fname in os.listdir(directory):
            if fname.endswith('.crdownload') and verify_file_creation_time(os.path.join(directory, fname), 300):
                dl_wait = True
        seconds += 1
    return seconds

def get_latest_file_with_extension(directory, extension):
    files = os.listdir(directory)
    # Filtrar solo los archivos .zip
    files = [f for f in files if f.endswith(extension)]
    files = [os.path.join(directory, f) for f in files]
    # Obtener el archivo más reciente
    latest_file = max(files, key=os.path.getctime)

    return latest_file

def verify_file_creation_time(file_path, timeout):
    creation_time_file = os.path.getctime(file_path)
    now = time.time()
    difference_time = now - creation_time_file
    if difference_time > timeout:
        return False
    return True


def execute_action(action):
    r = requests.post('http://localhost:8765', json=action)
    r_json = r.json()
    if r_json['error'] is not None:
        print("Error in Anki Connect:", r_json['error'])
        exit(2)
    return r_json

def two_anki_to_anki_connect(notion_deck_path, name_deck_destiny):
    deckName = notion_deck_path.split('\\')[-1]
    deckName = '.'.join(deckName.split('.')[:-1])
    # Get only the name if the deck name is repeated
    if deckName[-3] and deckName[-3] == '(' and deckName[-2].isdigit() and deckName[-1] == ')':
        deckName = ' '.join(deckName.split(' ')[:-1])

    action = {
        "action": "importPackage",
        "version": 6,
        "params": {
            "path": notion_deck_path
        }
    }
    execute_action(action)


    action = {
        "action": "findCards",
        "version": 6,
        "params": {
            "query": f"deck:{deckName}"
        }
    }
    card_ids = execute_action(action)['result']
    if len(card_ids) == 0:
        print("No cards found in deck")
        exit(1)

    action = {
        "action": "changeDeck",
        "version": 6,
        "params": {
            "cards": card_ids,
            "deck": name_deck_destiny
        }
    }
    execute_action(action)

    # IMPORTANT: This function doesn't detect error
    action = {
        "action": "deleteDecks",
        "version": 6,
        "params": {
            "decks": [deckName],
            "cardsToo": True
        }
    }
    execute_action(action)
    print("Deck importado con éxito")

def clean_files(temp_page_url, notion_deck_path, notion_page_zip_path):
    # Delete files from the download folder
    try:
        os.remove(notion_deck_path)
        os.remove(notion_page_zip_path)
        print("Archivos eliminados con éxito de Descargas")
    except Exception as e:
        print("Error deleting files from downloads folder:", e)

    # Delete the TempPage from Notion
    id_page = temp_page_url.split("/")[-1].split("-")[-1]
    try:
        url = f"{NOTION_BASE_URL}/pages/{id_page}"
        data = {"archived": True}
        response = requests.patch(url, headers=HEADERS, json=data)
        response.raise_for_status()
        print("Página de Notion Temp eliminada con éxito")
    except Exception as e:
        print("Error deleting TempPage from Notion:", e)

def main():

    page_id_source =  "15a869c35fd38051a77de06fe6423dc8"
    page_id_destine = "188869c35fd38011aca6c22370bbadc3"
    language = "es"
    #deck_name_destiny = "Artificial Intelligence"
    deck_name_destiny = "IdeaVim"

    # 1. Reorganize the notes from the source page to the destine page using the ChatGPT API
    temp_page_url = notion_to_notion(page_id_source, page_id_destine, language)

    # 2. Convert the notes from Notion to html and then to Anki format using 2Anki
    notion_page_zip_path, notion_deck_path = notion_to_2anki(temp_page_url)

    # 3. Import the Anki deck file using Anki Connect as API
    two_anki_to_anki_connect(notion_deck_path, deck_name_destiny)

    # 4. Delete the remanent files
    clean_files(temp_page_url, notion_deck_path, notion_page_zip_path)

    # TODO: delete the remanent images and notion blocks (tempPage, newNotionPage, local images)
    # TODO: add support to bullet items and code blocks


    # TODO: delete the tempPage from Notion
    # TODO: improve comments about the stages of the process
    # TODO: clean content of tempPage source page
    # TODO: verificar la elimnacion de tempPage from Notion
if __name__ == "__main__":
    main()
