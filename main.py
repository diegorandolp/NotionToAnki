from openai import OpenAI
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
    return response.json()

def format_with_openai(notes):

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
            - Sólo incluya el campo "imagen" si hay una referencia de imagen real para esa ficha específica.

            Acuérdate de procesar toda la información de las notas, creando tantas fichas como sea necesario para cubrir todos los conceptos e ideas importantes. El objetivo es crear un conjunto completo de fichas que ayuden a los alumnos a repasar y reforzar su comprensión de los temas de matemáticas y programación tratados en los apuntes originales.
            El formato de respuesta debe ser solo un objeto JSON con la estructura dada. No incluya ninguna información adicional en su respuesta.
            """
    prompt = prompt_1 + notes + prompt_2

    """
    Using structured output to get the response in JSON format
    """


    client = OpenAI(
        api_key= OPENAI_API_KEY
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "Eres un experto asistente de estudio que ayuda a organizar apuntes en formato de flashcards"},
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=Anki,
    )

    response_parsed = completion.choices[0].message.parsed

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
    # Enviar a Notion
    data = {"children": toggle_blocks}
    response = requests.patch(url, headers=HEADERS, json=data)
    response.raise_for_status()

    return response.json()
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
                if len(block[temp_type]["rich_text"]) > 0:
                    pass
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

                print("URL Cloudinary: ", new_url_image)

                image_info = image_info + " : " + new_url_image["url"]
                clean_content.append(image_info)
            elif temp_type in ignored_block_types:
                pass
            else :
                print("Block type not supported", temp_type)
        except Exception as e:
            print("Error processing block:", block)


    clean_content = "\n".join(clean_content)
    return clean_content

def main():

    page_id_source = "158869c35fd380cd9d88cbd06bb969c0"
    page_id_destine = "159869c35fd3806e9c5cd2919c70ef3e"
    # IMPORTANT: This code only support the first level of blocks of a Notion page and certain block types

    try:
        raw_page_content = get_notion_page_content(page_id_source)
        # extract only the text content from the page
        processed_page_content = process_raw_notion_page(raw_page_content)

        print("Clean content:")
        print(processed_page_content)
        # return a JSON object with the structure of the Anki object
        formatted_content = format_with_openai(processed_page_content)
        # TODO: , add support to claude and mistral
        # TODO: delete the remanent images and notion blocks
        # Updated Notion page (appends the new content)
        update_notion_page(page_id_destine, formatted_content)
        print("Página actualizada con éxito.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
