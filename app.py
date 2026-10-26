import json
import os

import requests
from flask import Flask, Response, jsonify, render_template, request

from gifs import gerar_gif

app = Flask(__name__)

# --- Configuração -----------------------------------------------------------
# A chave NUNCA vai no código: ela vem da variável de ambiente OPENAI_API_KEY
# (na Vercel: Settings -> Environment Variables).
# Se a chave existir, usa a OpenAI (paga). Senão, tenta o Llama local (Ollama),
# que só funciona rodando na sua máquina.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

IDIOMAS = ["Português", "Inglês", "Espanhol", "Francês", "Italiano",
           "Alemão", "Japonês", "Latim"]
COMPORTAMENTOS = ["Alegre", "Triste", "Piadista", "Irritado", "Formal",
                  "Romântico", "Sarcástico", "Pirata"]


def montar_prompt(idioma: str, comportamento: str) -> str:
    return (
        f"Gere uma frase em {idioma} que seja {comportamento}. "
        "Depois traduza essa frase para português do Brasil. "
        'Responda SOMENTE com JSON no formato: '
        '{"frase": "...", "traducao": "..."}'
    )


def chamar_openai(prompt: str) -> dict:
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def chamar_ollama(prompt: str) -> dict:
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


@app.get("/api/gif")
def gif():
    """Devolve um GIF animado com o texto recebido (usado como <img src>)."""
    frase = request.args.get("frase", "").strip()[:240] or "Gerador de Frases LLM"
    traducao = request.args.get("traducao", "").strip()[:240]
    comportamento = request.args.get("comportamento", "")
    if comportamento not in COMPORTAMENTOS:
        comportamento = ""
    return Response(
        gerar_gif(frase, traducao, comportamento),
        mimetype="image/gif",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/")
def index():
    return render_template(
        "index.html",
        idiomas=IDIOMAS,
        comportamentos=COMPORTAMENTOS,
        provedor="OpenAI" if OPENAI_API_KEY else f"Ollama ({OLLAMA_MODEL})",
    )


@app.post("/api/gerar")
def gerar():
    dados = request.get_json(force=True)
    idioma = dados.get("idioma", "Inglês")
    comportamento = dados.get("comportamento", "Alegre")
    prompt = montar_prompt(idioma, comportamento)
    try:
        resultado = chamar_openai(prompt) if OPENAI_API_KEY else chamar_ollama(prompt)
    except requests.ConnectionError:
        return jsonify(
            erro="Não consegui conectar na LLM. Defina a variável OPENAI_API_KEY "
                 "ou rode o Ollama na sua máquina."
        ), 502
    except Exception as e:  # noqa: BLE001
        return jsonify(erro=f"Falha ao gerar: {e}"), 500

    return jsonify(
        idioma=idioma,
        comportamento=comportamento,
        prompt=prompt,
        frase=resultado.get("frase", ""),
        traducao=resultado.get("traducao", ""),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
