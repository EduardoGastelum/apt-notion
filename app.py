import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

notion = Client(auth=NOTION_TOKEN)

app = Flask(__name__)

COORD_ENCARGADOS = {
    "Académica": ["Sebas"],
    "Administrativa": ["Archie"],
    "Calidad": ["Diana"],
    "Organización": ["Joss", "Gaste"],
    "RRPP": ["Denisse"],
    "Sebas": ["Académica"],
    "Archie": ["Administrativa"],
    "Diana": ["Calidad"],
    "Joss": ["Organización"],
    "Gaste": ["Organización"],
    "Denisse": ["RRPP"]
}

# Para obtener todas las personas y coordinaciones
TODAS_COORDINACIONES = ["Académica", "Administrativa", "Calidad", "Organización", "RRPP"]
TODOS_ENCARGADOS = ["Sebas", "Archie", "Diana", "Joss", "Gaste", "Denisse"]

def add_task_notion(encargados, coordinaciones, tarea):
    notion.pages.create(
        parent={"database_id": NOTION_DB_ID},
        properties={
            "Actividad": {"title": [{"text": {"content": tarea}}]},
            "Encargado": {"rich_text": [{"text": {"content": ', '.join(encargados)}}] if encargados else []},
            "Coordinación": {"multi_select": [{"name": coord} for coord in coordinaciones] if coordinaciones else []}
        }
    )

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    lineas = texto.split('\n')

    encargado_input = None
    tareas_lineas = []

    if lineas[0].startswith("Encargado:"):
        encargado_input = lineas[0].replace("Encargado:", "").strip().lower()
        tareas_lineas = lineas[2:] if len(lineas) > 2 else []
    elif lineas[0].startswith("Tareas:"):
        tareas_lineas = lineas[1:]
    else:
        await update.message.reply_text("Formato incorrecto. Usa al menos 'Tareas:' o 'Encargado:'")
        return

    encargados = []
    coordinaciones = []

    if encargado_input:
        if encargado_input == "todos":
            encargados = TODOS_ENCARGADOS
            coordinaciones = TODAS_COORDINACIONES
        else:
            encargados = COORD_ENCARGADOS.get(encargado_input.capitalize(), [encargado_input.capitalize()])
            # Identifica automáticamente coordinaciones
            for enc in encargados:
                coords = COORD_ENCARGADOS.get(enc, [])
                for coord in coords:
                    if coord in TODAS_COORDINACIONES and coord not in coordinaciones:
                        coordinaciones.append(coord)

    # Añadir cada tarea individualmente
    tareas_creadas = 0
    for tarea in tareas_lineas:
        tarea = tarea.strip("- ").strip()
        if tarea:
            add_task_notion(encargados, coordinaciones, tarea)
            tareas_creadas += 1

    if tareas_creadas > 0:
        await update.message.reply_text(f"✅ {tareas_creadas} tareas añadidas correctamente a Notion.")
    else:
        await update.message.reply_text("⚠️ No se encontró ninguna tarea válida para añadir.")

telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), procesar_mensaje))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    telegram_app.update_queue.put_nowait(Update.de_json(request.get_json(), telegram_app.bot))
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "API Telegram-Notion lista ✅", 200

if __name__ == "__main__":
    app.run()
