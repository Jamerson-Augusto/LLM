"""Gerador de GIF animado com o texto da LLM.

Cada GIF é desenhado frame a frame com Pillow: fundo em degradê que "respira",
partículas animadas (cada comportamento tem o seu estilo) e o texto da frase
pulando em onda. A tradução aparece numa caixa embaixo.
"""
import io
import math
import os
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

LARGURA, ALTURA = 480, 270
FRAMES = 20
DURACAO_MS = 70

FONTE = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Bold-subset.otf")

# comportamento -> (cor A, cor B, tipo de partícula, direção: -1 sobe / +1 desce)
TEMAS = {
    "Alegre":     ((255, 196, 0),  (255, 84, 120), "bolha",  -1),
    "Triste":     ((70, 90, 150),  (15, 25, 60),   "gota",   +1),
    "Piadista":   ((150, 70, 255), (255, 90, 190), "estrela", -1),
    "Irritado":   ((220, 30, 30),  (50, 0, 0),     "faisca", -1),
    "Formal":     ((55, 65, 90),   (130, 140, 160), "bolha", -1),
    "Romântico":  ((255, 110, 160), (150, 25, 90), "coracao", -1),
    "Sarcástico": ((30, 170, 150), (20, 55, 95),   "estrela", -1),
    "Pirata":     ((120, 75, 30),  (10, 30, 55),   "bolha",  -1),
}
TEMA_PADRAO = ((79, 70, 229), (30, 27, 90), "bolha", -1)


def _fonte(tam: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONTE, tam)
    except OSError:
        return ImageFont.load_default(tam)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _quebrar(draw, texto, fonte, largura_max):
    """Quebra por palavras; se uma palavra for maior que a linha (ex.: japonês,
    que não usa espaços), quebra caractere a caractere."""
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
            continue
        if atual:
            linhas.append(atual)
            atual = ""
        if draw.textlength(palavra, font=fonte) <= largura_max:
            atual = palavra
        else:
            for ch in palavra:
                if draw.textlength(atual + ch, font=fonte) > largura_max and atual:
                    linhas.append(atual)
                    atual = ""
                atual += ch
    if atual:
        linhas.append(atual)
    return linhas or [""]


def _ajustar(draw, texto, tam_max, tam_min, largura, altura_max, folga=1.25):
    """Maior fonte em que o texto cabe na caixa largura x altura_max."""
    for tam in range(tam_max, tam_min - 1, -2):
        fonte = _fonte(tam)
        linhas = _quebrar(draw, texto, fonte, largura)
        if len(linhas) * tam * folga <= altura_max:
            return fonte, linhas, tam
    fonte = _fonte(tam_min)
    linhas = _quebrar(draw, texto, fonte, largura)
    max_linhas = max(1, int(altura_max // (tam_min * folga)))
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        linhas[-1] = linhas[-1][:-1] + "…"
    return fonte, linhas, tam_min


def _particulas(seed: str, n=16):
    rnd = random.Random(seed)
    return [
        {
            "x": rnd.uniform(0, LARGURA),
            "y": rnd.uniform(0, ALTURA),
            "r": rnd.uniform(4, 13),
            "v": rnd.choice([1, 2, 3]),     # voltas no loop (mantém o GIF contínuo)
            "ph": rnd.uniform(0, math.tau),
        }
        for _ in range(n)
    ]


def _desenhar_particula(d, tipo, x, y, r, cor):
    if tipo == "gota":
        d.line([(x, y - r * 1.4), (x, y + r * 0.6)], fill=cor, width=max(2, int(r / 3)))
    elif tipo == "faisca":
        d.polygon([(x, y - r), (x + r * 0.5, y), (x, y + r), (x - r * 0.5, y)], fill=cor)
    elif tipo == "estrela":
        pts = []
        for i in range(10):
            ang = math.pi / 5 * i - math.pi / 2
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
        d.polygon(pts, fill=cor)
    elif tipo == "coracao":
        d.ellipse([x - r, y - r, x, y], fill=cor)
        d.ellipse([x, y - r, x + r, y], fill=cor)
        d.polygon([(x - r, y - r * 0.4), (x + r, y - r * 0.4), (x, y + r)], fill=cor)
    else:  # bolha
        d.ellipse([x - r, y - r, x + r, y + r], outline=cor, width=2)


def _contorno(d, xy, texto, fonte, cor, contorno=(0, 0, 0)):
    x, y = xy
    d.text((x + 2, y + 3), texto, font=fonte, fill=(0, 0, 0, 90), anchor="mm")
    d.text((x, y), texto, font=fonte, fill=cor, anchor="mm",
           stroke_width=3, stroke_fill=contorno)


def _frame(i, frase, traducao, tema, particulas):
    cor_a, cor_b, tipo, direcao = tema
    fase = i / FRAMES * math.tau

    # --- fundo: degradê vertical que respira ---------------------------------
    fundo = Image.new("RGB", (LARGURA, ALTURA))
    d = ImageDraw.Draw(fundo)
    desloc = (math.sin(fase) + 1) / 4  # 0..0.5
    for y in range(ALTURA):
        t = min(1, y / ALTURA * 0.8 + desloc)
        d.line([(0, y), (LARGURA, y)], fill=_mix(cor_a, cor_b, t))

    # --- partículas (translúcidas) -------------------------------------------
    camada = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    for p in particulas:
        prog = (i / FRAMES * p["v"]) % 1.0
        y = (p["y"] + direcao * prog * ALTURA) % ALTURA
        x = p["x"] + math.sin(fase * p["v"] + p["ph"]) * 14
        _desenhar_particula(dc, tipo, x, y, p["r"], (255, 255, 255, 120))
    fundo = Image.alpha_composite(fundo.convert("RGBA"), camada)

    # --- texto ---------------------------------------------------------------
    texto_layer = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    dt = ImageDraw.Draw(texto_layer)

    if traducao:
        area_frase = (14, 10, LARGURA - 14, 168)
        # caixa da tradução
        fonte_t, linhas_t, tam_t = _ajustar(dt, traducao, 20, 12, LARGURA - 56, 70)
        altura_caixa = len(linhas_t) * tam_t * 1.25 + 18
        topo = ALTURA - altura_caixa - 12
        dt.rounded_rectangle([14, topo, LARGURA - 14, ALTURA - 12], radius=14,
                             fill=(0, 0, 0, 120))
        for k, linha in enumerate(linhas_t):
            cy = topo + 9 + (k + 0.5) * tam_t * 1.25
            dt.text((LARGURA / 2, cy), linha, font=fonte_t,
                    fill=(255, 255, 255, 235), anchor="mm")
        area_frase = (14, 10, LARGURA - 14, topo - 6)
    else:
        area_frase = (14, 10, LARGURA - 14, ALTURA - 10)

    x0, y0, x1, y1 = area_frase
    fonte, linhas, tam = _ajustar(dt, frase, 44, 16, x1 - x0, y1 - y0)
    alt_linha = tam * 1.25
    inicio = y0 + ((y1 - y0) - alt_linha * len(linhas)) / 2
    for k, linha in enumerate(linhas):
        onda = math.sin(fase * 2 + k * 0.9) * 5            # pulo em onda
        brilho = (math.sin(fase + k * 0.7) + 1) / 2          # cor pulsante
        cor = _mix((255, 255, 255), (255, 240, 150), brilho)
        _contorno(dt, ((x0 + x1) / 2, inicio + (k + 0.5) * alt_linha + onda),
                  linha, fonte, cor, contorno=tuple(int(c * 0.25) for c in cor_b))

    return Image.alpha_composite(fundo, texto_layer).convert("RGB")


@lru_cache(maxsize=64)
def gerar_gif(frase: str, traducao: str = "", comportamento: str = "") -> bytes:
    """Devolve os bytes de um GIF animado em loop. Resultado em cache."""
    tema = TEMAS.get(comportamento, TEMA_PADRAO)
    particulas = _particulas(f"{frase}|{comportamento}")
    frames = [
        _frame(i, frase, traducao, tema, particulas).quantize(
            colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        for i in range(FRAMES)
    ]
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                   duration=DURACAO_MS, loop=0, disposal=1)
    return buf.getvalue()
