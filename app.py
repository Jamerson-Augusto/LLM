import os
from flask import Flask, render_with_template, render_template # Ajustado conforme o padrão Flask comum se necessário, mas mantendo a base
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env se ele existir localmente
load_dotenv()

app = Flask(__name__)

# Exemplo de como capturar a chave no código:
# openai_api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
