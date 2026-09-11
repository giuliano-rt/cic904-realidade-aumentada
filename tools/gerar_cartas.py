"""
gerar_cartas.py - Gera as cartas imprimiveis que servem de Image Target na Vuforia.

Cada carta combina:
  * um QR Code real (gerado por qrgen.py, sem dependencias externas);
  * tipografia grande e um padrao de pontos assimetrico unico por carta.

O padrao assimetrico existe por um motivo tecnico: a Vuforia rastreia por
pontos de caracteristica naturais, e QR Codes "puros" sao parecidos entre si
(os tres marcadores de canto sao identicos em todos). Sem elementos proprios,
o rastreador pode confundir uma carta com outra. Os elementos extras sao
deterministicos (derivados do id), entao a carta e sempre reproduzivel.

Uso:
    python gerar_cartas.py
"""

import json
import os
import random
import unicodedata

from PIL import Image, ImageDraw, ImageFont

import qrgen

# ------------------------------------------------------------- Parametros ---
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
JSON_PERGUNTAS = os.path.join(RAIZ, "UnityAssets", "Resources", "perguntas.json")
SAIDA = os.path.join(RAIZ, "cartas")

LARGURA, ALTURA = 1000, 1400
MARGEM = 46
PRETO = (17, 17, 17)
BRANCO = (255, 255, 255)

# Versao minima do QR: 3 (29x29 modulos) deixa a malha mais densa,
# o que da mais pontos de caracteristica para a Vuforia rastrear.
QR_VERSAO_MINIMA = 3


def carregar_fonte(nomes, tamanho):
    for nome in nomes:
        caminho = os.path.join("C:\\", "Windows", "Fonts", nome)
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                pass
    return ImageFont.load_default()


def fonte_bold(tamanho):
    return carregar_fonte(["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"], tamanho)


def fonte_regular(tamanho):
    return carregar_fonte(["arial.ttf", "segoeui.ttf", "calibri.ttf"], tamanho)


def fonte_mono(tamanho):
    return carregar_fonte(["consolab.ttf", "consola.ttf", "cour.ttf"], tamanho)


def hex_para_rgb(valor):
    valor = valor.lstrip("#")
    return tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))


def sem_acento(texto):
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def centralizar(draw, texto, fonte, y, largura=LARGURA, cor=PRETO):
    esq, topo, dir_, base = draw.textbbox((0, 0), texto, font=fonte)
    draw.text(((largura - (dir_ - esq)) / 2 - esq, y - topo), texto,
              font=fonte, fill=cor)
    return base - topo


# ------------------------------------------------------------ Desenho -------
def desenhar_qr(img, texto, caixa):
    """Desenha o QR dentro de 'caixa' (x0, y0, lado), alinhado ao pixel."""
    matriz = qrgen.gerar_matriz(texto, min_version=QR_VERSAO_MINIMA)
    n = len(matriz)
    x0, y0, lado = caixa

    # arredonda o modulo para um numero inteiro de pixels: sem isso o QR
    # sai com modulos de larguras diferentes e fica dificil de escanear.
    modulo = max(1, lado // (n + 8))       # +8 = zona de silencio (4 de cada lado)
    total = modulo * (n + 8)
    ox = x0 + (lado - total) // 2
    oy = y0 + (lado - total) // 2

    draw = ImageDraw.Draw(img)
    draw.rectangle([ox, oy, ox + total, oy + total], fill=BRANCO)
    for r in range(n):
        for c in range(n):
            if matriz[r][c]:
                px = ox + (c + 4) * modulo
                py = oy + (r + 4) * modulo
                draw.rectangle([px, py, px + modulo - 1, py + modulo - 1],
                               fill=PRETO)
    return ox, oy, total


def padrao_unico(draw, semente, cor):
    """Constelacao assimetrica deterministica, unica por carta.

    As zonas evitam de proposito a area do QR e sua zona de silencio:
    ocupam a faixa acima dele e as duas colunas laterais, que ficariam
    brancas e sem pontos de caracteristica para a Vuforia.
    """
    rnd = random.Random(semente)
    zonas = [
        (MARGEM + 18, 424, LARGURA - MARGEM - 18, 566),   # faixa superior
        (MARGEM + 18, 620, 188, 1150),                    # coluna esquerda
        (LARGURA - 188, 620, LARGURA - MARGEM - 18, 1150),  # coluna direita
    ]
    for x0, y0, x1, y1 in zonas:
        for _ in range(26):
            x = rnd.randint(x0, x1)
            y = rnd.randint(y0, y1)
            raio = rnd.choice([3, 4, 5, 7, 9, 12])
            if rnd.random() < 0.35:
                draw.ellipse([x - raio, y - raio, x + raio, y + raio],
                             outline=PRETO, width=3)
            elif rnd.random() < 0.5:
                draw.ellipse([x - raio, y - raio, x + raio, y + raio], fill=cor)
            else:
                draw.ellipse([x - raio, y - raio, x + raio, y + raio], fill=PRETO)
        # tracos ligando pontos: quebram a simetria e ajudam o rastreio
        for _ in range(4):
            ax, ay = rnd.randint(x0, x1), rnd.randint(y0, y1)
            bx, by = rnd.randint(x0, x1), rnd.randint(y0, y1)
            draw.line([ax, ay, bx, by], fill=PRETO, width=2)


def gerar_carta(pergunta, indice, total):
    cor = hex_para_rgb(pergunta["corHex"])
    img = Image.new("RGB", (LARGURA, ALTURA), BRANCO)
    draw = ImageDraw.Draw(img)

    # moldura colorida dupla
    draw.rectangle([0, 0, LARGURA - 1, ALTURA - 1], fill=cor)
    draw.rectangle([MARGEM, MARGEM, LARGURA - MARGEM - 1, ALTURA - MARGEM - 1],
                   fill=BRANCO)
    draw.rectangle([MARGEM + 12, MARGEM + 12,
                    LARGURA - MARGEM - 13, ALTURA - MARGEM - 13],
                   outline=PRETO, width=4)

    # cabecalho
    faixa_y = MARGEM + 12
    draw.rectangle([MARGEM + 12, faixa_y, LARGURA - MARGEM - 13, faixa_y + 96],
                   fill=PRETO)
    centralizar(draw, "SISTEMA SOLAR  ·  REALIDADE AUMENTADA",
                fonte_bold(30), faixa_y + 33, cor=BRANCO)

    # titulo do planeta
    centralizar(draw, pergunta["titulo"].upper(), fonte_bold(104), 232)
    draw.line([260, 372, LARGURA - 260, 372], fill=cor, width=9)

    # constelacao assimetrica (unica por carta)
    padrao_unico(draw, pergunta["id"], cor)

    # QR Code (a zona de silencio branca fica intocada abaixo dele)
    desenhar_qr(img, pergunta["id"], (200, 600, 600))

    # rodape com o identificador, fora da zona de silencio do QR
    centralizar(draw, pergunta["id"], fonte_mono(54), 1232)
    centralizar(draw, "Aponte a câmera do aplicativo para esta carta",
                fonte_regular(27), 1300)

    # selo com o numero da carta
    cx, cy, r = LARGURA - MARGEM - 74, MARGEM + 152, 44
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor, outline=PRETO, width=4)
    rotulo = f"{indice}/{total}"
    esq, topo, dir_, base = draw.textbbox((0, 0), rotulo, font=fonte_bold(30))
    draw.text((cx - (dir_ - esq) / 2 - esq, cy - (base - topo) / 2 - topo),
              rotulo, font=fonte_bold(30), fill=PRETO)

    return img


def gerar_folha(cartas):
    """Monta uma folha A4 (300 dpi) com quatro cartas para impressao."""
    A4 = (2480, 3508)
    folha = Image.new("RGB", A4, BRANCO)
    largura_alvo = 1120
    escala = largura_alvo / LARGURA
    altura_alvo = int(ALTURA * escala)

    margem_x = (A4[0] - largura_alvo * 2) // 3
    margem_y = (A4[1] - altura_alvo * 2) // 3

    for i, carta in enumerate(cartas[:4]):
        col, lin = i % 2, i // 2
        x = margem_x + col * (largura_alvo + margem_x)
        y = margem_y + lin * (altura_alvo + margem_y)
        folha.paste(carta.resize((largura_alvo, altura_alvo), Image.LANCZOS), (x, y))
    return folha


def main():
    with open(JSON_PERGUNTAS, encoding="utf-8") as f:
        dados = json.load(f)

    perguntas = dados["perguntas"]
    os.makedirs(SAIDA, exist_ok=True)

    cartas = []
    for i, pergunta in enumerate(perguntas, start=1):
        img = gerar_carta(pergunta, i, len(perguntas))
        nome = f"{pergunta['id']}_{sem_acento(pergunta['titulo'])}.png"
        img.save(os.path.join(SAIDA, nome), dpi=(300, 300))
        cartas.append(img)
        print(f"  carta gerada: {nome}")

    for bloco in range(0, len(cartas), 4):
        folha = gerar_folha(cartas[bloco:bloco + 4])
        nome = f"folha_impressao_{bloco // 4 + 1}.png"
        folha.save(os.path.join(SAIDA, nome), dpi=(300, 300))
        print(f"  folha A4 gerada: {nome}")

    print(f"\n{len(cartas)} cartas em {SAIDA}")
    print("Envie os PNGs individuais para o Target Manager da Vuforia")
    print("e imprima as folhas A4 para usar na demonstracao.")


if __name__ == "__main__":
    main()
