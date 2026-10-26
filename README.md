<<<<<<< HEAD
# llm-frases-vercel
=======
# Gerador de Frases LLM (Python / Flask)

Página com duas abas:

- **Entrada**: escolha o **Idioma** e o **Comportamento** e clique em **Run**.
- **Resposta**: mostra a frase gerada pela LLM e a tradução para português.

No topo da página há um **GIF animado** que aparece assim que o link abre. Quando
a LLM responde, o GIF é regenerado com a **frase** (grande) e a **tradução**
(na caixa de baixo). Cada comportamento tem seu visual: Romântico solta
corações, Triste faz chover, Irritado solta faíscas, etc.

Fluxo: a página envia um JSON para `POST /api/gerar`, a API monta o prompt,
chama a LLM e devolve um JSON com `frase` e `traducao`. Depois a página aponta o `<img>` para
`GET /api/gif?frase=...&traducao=...&comportamento=...`, que desenha o GIF com
Pillow (`gifs.py`) usando a fonte em `fonts/` (cobre latim, cirílico, grego e japonês).

## Rodar na sua máquina

```bash
pip install -r requirements.txt
python app.py
```

Abra http://localhost:5000

- **Com OpenAI (paga):** defina `OPENAI_API_KEY` antes de rodar.
  - PowerShell: `$env:OPENAI_API_KEY="sua-chave"`
  - Linux/Mac: `export OPENAI_API_KEY="sua-chave"`
- **Sem chave (grátis):** instale o [Ollama](https://ollama.com), rode
  `ollama pull llama3.2:1b` e deixe `ollama serve` aberto.

## Publicar na Vercel

1. Suba esta pasta para um repositório no GitHub (a chave NÃO fica no código).
2. Em vercel.com: **Add New -> Project**, escolha o repositório e **Import**.
3. Em **Environment Variables**, crie `OPENAI_API_KEY` com a sua chave.
4. Clique em **Deploy**.

Online só funciona com a OpenAI, pois o Ollama roda apenas na sua máquina.
>>>>>>> 4a439b2436400b998b2a090578c49127a381667d
