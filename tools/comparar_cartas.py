"""
comparar_cartas.py - Mede o quanto as cartas se parecem para um rastreador de imagem.

A Vuforia reconhece uma carta casando pontos de caracteristica da imagem da
camera com os pontos de cada alvo do database. Se duas cartas compartilham
muitos pontos, a Vuforia pode reconhecer uma pela outra -- e foi exatamente isso
que aconteceu com a primeira versao das cartas, que tinham cabecalho, rodape e
moldura identicos.

Este script aproxima esse processo:
  1. detecta cantos com o detector de Harris
  2. descreve cada canto por um recorte normalizado da vizinhanca
  3. casa os descritores de duas cartas, com o teste de razao de Lowe
  4. calcula que fracao dos pontos da carta A encontra par na carta B

Nao e o algoritmo da Vuforia, que e proprietario; e o mesmo principio. A nota
serve para COMPARAR versoes de cartas entre si, nao como previsao exata.

As cartas sao reduzidas antes da analise para imitar o que a webcam enxerga de
uma carta impressa a uns 30 cm: detalhe fino demais nao sobrevive e nao deve
contar.

Uso:
    python comparar_cartas.py              # compara cartas/ (versao atual)
    python comparar_cartas.py cartas/v2    # compara outra pasta
"""

import glob
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial.distance import cdist

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

LARGURA_ANALISE = 320        # pixels: ~ o que a webcam capta da carta
MAX_PONTOS = 350
RAIO_DESCRITOR = 7           # recorte de 15 x 15 em volta de cada canto
RAZAO_LOWE = 0.75


def carregar_cinza(caminho):
    """Carrega em tons de cinza, como a Vuforia faz antes de procurar pontos."""
    img = Image.open(caminho).convert("L")
    altura = round(img.height * LARGURA_ANALISE / img.width)
    img = img.resize((LARGURA_ANALISE, altura), Image.LANCZOS)
    return np.asarray(img, dtype=float) / 255.0


def cantos_harris(img, sigma=1.4, k=0.05):
    ix = ndimage.sobel(img, axis=1)
    iy = ndimage.sobel(img, axis=0)
    ixx = ndimage.gaussian_filter(ix * ix, sigma)
    iyy = ndimage.gaussian_filter(iy * iy, sigma)
    ixy = ndimage.gaussian_filter(ix * iy, sigma)
    resposta = ixx * iyy - ixy ** 2 - k * (ixx + iyy) ** 2

    # supressao de nao-maximos: so o canto mais forte de cada vizinhanca
    maximos = ndimage.maximum_filter(resposta, size=9)
    candidatos = (resposta == maximos) & (resposta > resposta.max() * 0.01)

    # descarta a borda, onde o recorte do descritor nao cabe
    r = RAIO_DESCRITOR
    candidatos[:r, :] = candidatos[-r:, :] = False
    candidatos[:, :r] = candidatos[:, -r:] = False

    ys, xs = np.nonzero(candidatos)
    ordem = np.argsort(resposta[ys, xs])[::-1][:MAX_PONTOS]
    return ys[ordem], xs[ordem]


def descritores(img, ys, xs):
    r = RAIO_DESCRITOR
    lista = []
    for y, x in zip(ys, xs):
        recorte = img[y - r:y + r + 1, x - r:x + r + 1]
        recorte = recorte - recorte.mean()
        norma = np.linalg.norm(recorte)
        lista.append((recorte / norma).ravel() if norma > 1e-6 else np.zeros(recorte.size))
    return np.array(lista)


def analisar(caminho):
    img = carregar_cinza(caminho)
    ys, xs = cantos_harris(img)
    return descritores(img, ys, xs)


def fracao_casada(d_a, d_b):
    """Fracao dos pontos de A que tem um par inequivoco em B."""
    if len(d_a) == 0 or len(d_b) < 2:
        return 0.0
    dist = cdist(d_a, d_b)
    duas = np.sort(dist, axis=1)[:, :2]
    bons = duas[:, 0] < RAZAO_LOWE * duas[:, 1]
    return float(bons.mean())


def comparar(pasta):
    arquivos = sorted(glob.glob(os.path.join(pasta, "SOLAR-*.png")))
    if not arquivos:
        sys.exit(f"Nenhuma carta SOLAR-*.png em {pasta}")

    nomes = [os.path.basename(a).split("_")[1].rsplit(".", 1)[0][:8] for a in arquivos]
    desc = [analisar(a) for a in arquivos]
    n = len(arquivos)

    matriz = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                # simetrica: a pior das duas direcoes e a que importa
                matriz[i, j] = max(fracao_casada(desc[i], desc[j]),
                                   fracao_casada(desc[j], desc[i]))

    print(f"\nSemelhanca entre cartas em {os.path.relpath(pasta, RAIZ)}")
    print("(fracao dos pontos de uma carta que casa com a outra)\n")
    print(" " * 10 + "".join(f"{nm:>9}" for nm in nomes))
    for i in range(n):
        linha = "".join("        -" if i == j else f"{matriz[i, j]:>9.0%}" for j in range(n))
        print(f"{nomes[i]:>10}{linha}")

    fora_diagonal = matriz[~np.eye(n, dtype=bool)]
    i, j = np.unravel_index(np.argmax(matriz), matriz.shape)
    print(f"\n  media entre pares : {fora_diagonal.mean():.0%}")
    print(f"  par mais parecido : {nomes[i]} x {nomes[j]} ({matriz[i, j]:.0%})")
    print(f"  pontos por carta  : {int(np.mean([len(d) for d in desc]))}")
    return matriz


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "cartas"
    comparar(os.path.join(RAIZ, alvo))
