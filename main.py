import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
# import openai
from openai import OpenAI
from notion_client import Client
import logging
logging.basicConfig(level=logging.INFO)

# Carga .env automáticamente
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

# Configuración de API keys
# openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

# Esquema de petición
class ItemRequest(BaseModel):
    text: str

app = FastAPI()

@app.post("/create_item")
async def create_item(req: ItemRequest):
    logging.info(f"Received request text: {req.text}")
    # 1) Llamar a GPT para obtener título y descripción
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae un título y descripción de un texto para Notion."},
                {"role": "user", "content": f"Extrae 'title' y 'description' en JSON del siguiente texto:\n{req.text}"}
            ]
        )
        # Log the raw response content for debugging
        content = resp.choices[0].message.content
        logging.info(f"GPT raw content: {content}")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as jde:
            logging.error(f"JSON decode error: {jde}; raw content: {content}")
            raise HTTPException(500, f"Error parseando JSON del GPT: {jde}; contenido bruto: {content}")
        title = data.get("title")
        description = data.get("description")
    except Exception as e:
        logging.exception("Unhandled exception calling OpenAI")
        raise HTTPException(500, f"Error OpenAI: {e}")

    # 2) Crear página en Notion
    try:
        logging.info(f"Creating Notion page with title: {title} and description: {description}")
        page = notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {"title": [{"text": {"content": title}}]},
                "Description": {"rich_text": [{"text": {"content": description}}]}
            }
        )
    except Exception as e:
        logging.exception("Unhandled exception creating Notion page")
        raise HTTPException(500, f"Error Notion: {e}")

    return {"id": page["id"], "title": title}