"""
gerar_cartas_v2.py - Segunda versao das cartas, desenhada para a Vuforia nao
confundir uma com a outra.

POR QUE EXISTE UMA V2

Com as cartas da v1, a Vuforia reconhecia varias cartas ao mesmo tempo sobre
uma unica carta fisica. O comparar_cartas.py mediu a semelhanca entre elas e
encontrou tres grupos -- e cada grupo era formado pelas cartas cujo QR Code
tinha a mesma MASCARA:

    mascara 1: Venus, Marte, Saturno, Urano  -> detectadas juntas no teste
    mascara 6: Terra, Jupiter                -> Jupiter lido como Terra
    mascara 4: Mercurio, Netuno

O QR era a maior regiao da carta e a mais rica em pontos. Como 'SOLAR-01' e
'SOLAR-08' diferem num unico caractere, dois QRs com a mesma mascara saiam
quase identicos. Por cima disso, cabecalho, rodape e moldura eram iguais nas
oito cartas -- e a moldura colorida nao ajudava em nada, porque a Vuforia
trabalha em tons de cinza.

O QUE MUDA

  * cada carta usa uma mascara diferente: o padrao QR tem exatamente 8
    mascaras, e o jogo tem exatamente 8 planetas;
  * o QR fica menor e num canto (versao 2), deixando de dominar a carta;
  * sai o cabecalho e o rodape, que eram identicos;
  * um mapa estelar denso e unico por carta cobre toda a superficie;
  * o planeta aparece renderizado a partir da propria textura do jogo.

O tamanho (1000 x 1400 px) e o mesmo da v1, entao o Width de 0,095 m no Target
Manager e a configuracao da cena continuam valendo.

Uso:
    python gerar_cartas_v2.py
    python comparar_cartas.py cartas/v2      # confere a semelhanca
"""

import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import qrgen
from gerar_cartas import (LARGURA, ALTURA, BRANCO, PRETO, fonte_bold, fonte_mono,
                          gerar_folha, hex_para_rgb, sem_acento)

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
JSON_PERGUNTAS = os.path.join(RAIZ, "Assets", "Resources", "perguntas.json")
TEXTURAS = os.path.join(RAIZ, "Assets", "Texturas", "Planetas")
SAIDA = os.path.join(RAIZ, "cartas", "v2")


# ------------------------------------------------------------ utilitarios ---
def escurecer(rgb, fator):
    return tuple(int(c * fator) for c in rgb)


def placa(draw, caixa, raio=26):
    """Area branca para o conteudo, sem contorno: cantos redondos e sem borda
    nao criam pontos de caracteristica iguais em todas as cartas."""
    draw.rounded_rectangle(caixa, radius=raio, fill=BRANCO)


# ------------------------------------------------------- mapa estelar -------
def mapa_estelar(img, semente, cor_carta):
    """Padrao denso de formas em alto contraste, deterministico e unico por id.

    E ele que carrega a maior parte dos pontos de caracteristica da carta. As
    formas sao grandes o bastante para sobreviver a impressao e a webcam; a cor
    da carta aparece em parte delas so para a vista humana, sempre escura o
    suficiente para manter contraste em tons de cinza.
    """
    rnd = random.Random(semente)
    draw = ImageDraw.Draw(img)
    escura = escurecer(cor_carta, 0.45)
    tintas = [PRETO, PRETO, PRETO, escura]

    # distribuicao por rejeicao: evita aglomerados e buracos grandes
    pontos = []
    tentativas = 0
    while len(pontos) < 175 and tentativas < 6000:
        tentativas += 1
        x = rnd.uniform(-20, LARGURA + 20)
        y = rnd.uniform(-20, ALTURA + 20)
        if all((x - px) ** 2 + (y - py) ** 2 > 58 ** 2 for px, py in pontos):
            pontos.append((x, y))

    for x, y in pontos:
        tinta = rnd.choice(tintas)
        tipo = rnd.random()
        if tipo < 0.28:                                  # astro cheio
            r = rnd.uniform(8, 30)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=tinta)
        elif tipo < 0.46:                                # anel
            r = rnd.uniform(16, 50)
            draw.ellipse([x - r, y - r, x + r, y + r], outline=tinta,
                         width=rnd.randint(5, 9))
        elif tipo < 0.62:                                # trecho de orbita
            rx, ry = rnd.uniform(40, 110), rnd.uniform(24, 80)
            ini = rnd.uniform(0, 360)
            draw.arc([x - rx, y - ry, x + rx, y + ry], ini, ini + rnd.uniform(70, 200),
                     fill=tinta, width=rnd.randint(5, 8))
        elif tipo < 0.78:                                # triangulo
            s, ang = rnd.uniform(18, 44), rnd.uniform(0, 2 * math.pi)
            vert = [(x + s * math.cos(ang + k * 2.1 + rnd.uniform(-0.3, 0.3)),
                     y + s * math.sin(ang + k * 2.1 + rnd.uniform(-0.3, 0.3))) for k in range(3)]
            draw.polygon(vert, fill=tinta)
        elif tipo < 0.90:                                # traco grosso
            comp, ang = rnd.uniform(30, 90), rnd.uniform(0, math.pi)
            dx, dy = comp * math.cos(ang) / 2, comp * math.sin(ang) / 2
            draw.line([x - dx, y - dy, x + dx, y + dy], fill=tinta,
                      width=rnd.randint(6, 10))
        else:                                            # estrela de quatro pontas
            s = rnd.uniform(14, 30)
            estrela = [(x, y - s), (x + s * .28, y - s * .28), (x + s, y),
                       (x + s * .28, y + s * .28), (x, y + s), (x - s * .28, y + s * .28),
                       (x - s, y), (x - s * .28, y - s * .28)]
            draw.polygon(estrela, fill=tinta)


# ------------------------------------------------------- disco do planeta ---
def disco_planeta(nome, diametro, rotacao=0.7):
    """Renderiza o planeta como uma esfera vista de frente, a partir da mesma
    textura equiretangular usada no jogo, com iluminacao de Lambert."""
    tex = np.asarray(Image.open(os.path.join(TEXTURAS, f"{nome}.jpg")).convert("RGB"),
                     dtype=float) / 255.0
    th, tw = tex.shape[:2]

    c = (np.arange(diametro) + 0.5) / diametro * 2 - 1
    x, y = np.meshgrid(c, -c)
    r2 = x * x + y * y
    z = np.sqrt(np.clip(1 - r2, 0, 1))

    lat = np.arcsin(np.clip(y, -1, 1))
    lon = np.arctan2(x, z) + rotacao
    u = ((lon + np.pi) / (2 * np.pi)) % 1.0
    v = (np.pi / 2 - lat) / np.pi
    rgb = tex[(v * (th - 1)).astype(int), (u * (tw - 1)).astype(int)]

    luz = np.array([-0.55, 0.45, 0.70])
    luz /= np.linalg.norm(luz)
    sombra = np.clip(x * luz[0] + y * luz[1] + z * luz[2], 0, 1) * 0.88 + 0.12
    rgb = np.clip(rgb * sombra[..., None], 0, 1)

    # borda suavizada em 1,5 px
    alfa = np.clip((1 - np.sqrt(r2)) * diametro / 3, 0, 1)
    rgba = np.dstack([rgb, alfa])
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


def planeta_na_carta(img, nome, centro, diametro):
    cx, cy = centro
    halo = diametro // 2 + 34
    ImageDraw.Draw(img).ellipse([cx - halo, cy - halo, cx + halo, cy + halo], fill=BRANCO)

    disco = disco_planeta(nome, diametro)
    pos = (cx - diametro // 2, cy - diametro // 2)

    if nome != "Saturno":
        img.paste(disco, pos, disco)
        return

    # Saturno: o anel passa ATRAS do planeta em cima e NA FRENTE embaixo.
    # O anel e dividido ao meio no PROPRIO eixo, antes de ser inclinado, e as
    # duas metades sao giradas juntas. Cortar depois de girar faria o corte
    # atravessar o anel na diagonal e deixar uma aresta reta sobre o planeta.
    anel = Image.open(os.path.join(TEXTURAS, "Saturno_Aneis.png")).convert("RGBA")
    largura_anel = int(diametro * 2.05)
    altura_anel = int(largura_anel * 0.30)
    anel = anel.resize((largura_anel, altura_anel), Image.LANCZOS)

    meio = altura_anel // 2
    tras = anel.copy()
    tras.paste((0, 0, 0, 0), (0, meio, largura_anel, altura_anel))   # so a metade de cima
    frente = anel.copy()
    frente.paste((0, 0, 0, 0), (0, 0, largura_anel, meio))            # so a metade de baixo

    inclinacao = -14
    tras = tras.rotate(inclinacao, expand=True, resample=Image.BICUBIC)
    frente = frente.rotate(inclinacao, expand=True, resample=Image.BICUBIC)
    pos_anel = (cx - tras.width // 2, cy - tras.height // 2)

    img.paste(tras, pos_anel, tras)
    img.paste(disco, pos, disco)
    img.paste(frente, pos_anel, frente)


# ------------------------------------------------------------------ QR ------
def qr_na_carta(img, texto, mascara, canto_esquerdo):
    """QR menor e num canto; a mascara e escolhida, nao calculada."""
    matriz = qrgen.gerar_matriz(texto, min_version=2, mascara=mascara)
    n = len(matriz)
    modulo = 9
    lado = modulo * (n + 8)                                  # com zona de silencio
    margem = 34
    x0 = margem if canto_esquerdo else LARGURA - margem - lado
    y0 = ALTURA - margem - lado

    draw = ImageDraw.Draw(img)
    placa(draw, [x0, y0, x0 + lado, y0 + lado], raio=18)
    for r in range(n):
        for c in range(n):
            if matriz[r][c]:
                px = x0 + (c + 4) * modulo
                py = y0 + (r + 4) * modulo
                draw.rectangle([px, py, px + modulo - 1, py + modulo - 1], fill=PRETO)
    return (x0, y0, lado)


# --------------------------------------------------------------- carta ------
def gerar_carta(pergunta, indice):
    nome_arquivo = sem_acento(pergunta["titulo"])
    cor = hex_para_rgb(pergunta["corHex"])
    mascara = indice - 1                   # SOLAR-01 -> mascara 0 ... SOLAR-08 -> 7

    img = Image.new("RGB", (LARGURA, ALTURA), BRANCO)
    mapa_estelar(img, pergunta["id"] + "/v2", cor)
    draw = ImageDraw.Draw(img)

    # nome do planeta: a maior tipografia da carta, e unica por carta
    fonte_nome = fonte_bold(118)
    texto = pergunta["titulo"].upper()
    e, t, d, b = draw.textbbox((0, 0), texto, font=fonte_nome)
    larg, alt = d - e, b - t
    px = (LARGURA - larg) // 2
    placa(draw, [px - 36, 58, px + larg + 36, 58 + alt + 56])
    draw.text((px - e, 58 + 28 - t), texto, font=fonte_nome, fill=PRETO)
    faixa_y = 58 + alt + 56 - 16
    draw.rounded_rectangle([px + 10, faixa_y, px + larg - 10, faixa_y + 9], radius=4, fill=cor)

    # planeta no centro
    planeta_na_carta(img, nome_arquivo, (LARGURA // 2, 640), 430)

    # QR alternando de canto, e o identificador no canto oposto
    canto_esquerdo = indice % 2 == 0
    qr_na_carta(img, pergunta["id"], mascara, canto_esquerdo)

    draw = ImageDraw.Draw(img)
    fonte_id = fonte_mono(46)
    e, t, d, b = draw.textbbox((0, 0), pergunta["id"], font=fonte_id)
    lx = LARGURA - 34 - (d - e) - 44 if canto_esquerdo else 34
    ly = ALTURA - 34 - (b - t) - 40
    placa(draw, [lx, ly, lx + (d - e) + 44, ly + (b - t) + 40], raio=16)
    draw.text((lx + 22 - e, ly + 20 - t), pergunta["id"], font=fonte_id, fill=PRETO)

    return img, nome_arquivo, mascara


def marcas_de_corte(folha, quantidade):
    """Marcas em L nos cantos de cada carta, do lado de fora.

    A v2 nao tem moldura -- o padrao vai ate a borda --, entao sem as marcas
    nao da para saber onde cortar. Elas ficam so na folha de impressao; as
    imagens individuais que vao para o Target Manager nao mudam.
    """
    # mesma geometria usada por gerar_folha
    a4_w, a4_h = folha.size
    larg = 1120
    alt = int(ALTURA * larg / LARGURA)
    mx = (a4_w - larg * 2) // 3
    my = (a4_h - alt * 2) // 3

    draw = ImageDraw.Draw(folha)
    cinza, afastamento, braco = (150, 150, 150), 14, 46
    for i in range(quantidade):
        x = mx + (i % 2) * (larg + mx)
        y = my + (i // 2) * (alt + my)
        for cx, cy, sx, sy in ((x, y, -1, -1), (x + larg, y, 1, -1),
                               (x, y + alt, -1, 1), (x + larg, y + alt, 1, 1)):
            draw.line([cx + sx * afastamento, cy, cx + sx * (afastamento + braco), cy],
                      fill=cinza, width=3)
            draw.line([cx, cy + sy * afastamento, cx, cy + sy * (afastamento + braco)],
                      fill=cinza, width=3)


def main():
    with open(JSON_PERGUNTAS, encoding="utf-8") as f:
        perguntas = json.load(f)["perguntas"]
    os.makedirs(SAIDA, exist_ok=True)

    cartas = []
    for i, p in enumerate(perguntas, start=1):
        img, nome, mascara = gerar_carta(p, i)
        img.save(os.path.join(SAIDA, f"{p['id']}_{nome}.png"), dpi=(300, 300))
        cartas.append(img)
        print(f"  {p['id']}  {nome:<9} mascara QR {mascara}")

    for bloco in range(0, len(cartas), 4):
        nome = f"folha_impressao_{bloco // 4 + 1}.png"
        folha = gerar_folha(cartas[bloco:bloco + 4])
        marcas_de_corte(folha, len(cartas[bloco:bloco + 4]))
        folha.save(os.path.join(SAIDA, nome), dpi=(300, 300))
        print(f"  folha A4: {nome}")
    print(f"\n{len(cartas)} cartas em {SAIDA}")


if __name__ == "__main__":
    main()
