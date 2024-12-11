from openai import OpenAI
from credentials import OPENAI_API_KEY, NOTION_API_KEY
import requests





# TODO: Setup ChatGPT API to generate notes

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

    client = OpenAI(
        api_key= OPENAI_API_KEY
    )

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto asistente de estudio que ayuda a organizar apuntes en formato de flashcards"},
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    response_string = completion.choices[0].message.content



    # return response['choices'][0]['message']['content']

def update_notion_page(page_id, formatted_content):
    """Actualiza una página de Notion con contenido en formato toggle list."""
    url = f"{NOTION_BASE_URL}/blocks/{page_id}/children"
    # Convertir el contenido formateado en bloques de Notion
    toggle_blocks = []
    for line in formatted_content.split("\n"):
        if line.strip():
            toggle_blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "text": [{"type": "text", "text": {"content": line.strip()}}]
                }
            })
    # Enviar a Notion
    data = {"children": toggle_blocks}
    response = requests.patch(url, headers=HEADERS, json=data)
    response.raise_for_status()
    return response.json()

def main():

    page_id = "158869c35fd380cd9d88cbd06bb969c0"

    # IMPORTANT: This code only support the first level of blocks of a Notion page and certain block types
    page_content = get_notion_page_content(page_id)

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
                image_info = image_info + " : " + block[temp_type]["file"]["url"]
                clean_content.append(image_info)
            elif temp_type in ignored_block_types:
                pass
            else :
                print("Block type not supported", temp_type)
        except Exception as e:
            print("Error processing block:", block)


    clean_content = "\n".join(clean_content)
    print("Clean content:")
    print(clean_content)

    format_with_openai(clean_content)
    # TODO: string to json, add support to claude and mistral
    # # Paso 3: Actualizar la página de Notion
    # update_notion_page(page_id, formatted_content)
    # print("Página actualizada con éxito.")

if __name__ == "__main__":
    main()
