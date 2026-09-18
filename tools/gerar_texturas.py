"""
gerar_texturas.py - Texturas procedurais dos oito planetas e dos aneis de Saturno.

As texturas sao equiretangulares (proporcao 2:1), que e o mapeamento UV da
esfera padrao da Unity: a largura percorre a longitude e a altura a latitude.

O ruido nao e gerado sobre a imagem, e sim sobre a SUPERFICIE DA ESFERA: cada
pixel e convertido num ponto (x, y, z) da esfera unitaria, e e esse ponto que
consulta o ruido 3D. Isso elimina os dois defeitos classicos de textura de
planeta gerada em 2D:
  * a costura vertical onde a borda esquerda encontra a direita;
  * o esticamento do padrao perto dos polos.

As cores partem da cor de cada carta (campo corHex do perguntas.json), para a
carta impressa e o planeta em cima dela combinarem.

Uso:
    python gerar_texturas.py
"""

import os

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SAIDA = os.path.join(RAIZ, "Assets", "Texturas", "Planetas")

LARGURA, ALTURA = 1024, 512


# ------------------------------------------------------------- geometria ----
def pontos_na_esfera(w=LARGURA, h=ALTURA):
    """Coordenadas 3D e de latitude/longitude de cada pixel da textura."""
    lon = (np.arange(w) + 0.5) / w * 2 * np.pi - np.pi
    lat = np.pi / 2 - (np.arange(h) + 0.5) / h * np.pi   # linha 0 = polo norte
    LON, LAT = np.meshgrid(lon, lat)
    x = np.cos(LAT) * np.cos(LON)
    y = np.cos(LAT) * np.sin(LON)
    z = np.sin(LAT)
    return x, y, z, LAT, LON


# ---------------------------------------------------------------- ruido -----
class Ruido3D:
    """Ruido de valor 3D com interpolacao suave, e fBm por cima dele."""

    def __init__(self, semente):
        rng = np.random.default_rng(semente)
        perm = rng.permutation(256)
        self.perm = np.concatenate([perm, perm])      # evita estouro no indice
        self.valores = rng.random(256)

    def _canto(self, xi, yi, zi):
        p = self.perm
        return self.valores[p[p[p[xi & 255] + (yi & 255)] + (zi & 255)]]

    def valor(self, x, y, z):
        xi = np.floor(x).astype(np.int64)
        yi = np.floor(y).astype(np.int64)
        zi = np.floor(z).astype(np.int64)
        xf, yf, zf = x - xi, y - yi, z - zi
        u = xf * xf * (3 - 2 * xf)       # smoothstep: sem quinas na interpolacao
        v = yf * yf * (3 - 2 * yf)
        w = zf * zf * (3 - 2 * zf)

        c000 = self._canto(xi, yi, zi)
        c100 = self._canto(xi + 1, yi, zi)
        c010 = self._canto(xi, yi + 1, zi)
        c110 = self._canto(xi + 1, yi + 1, zi)
        c001 = self._canto(xi, yi, zi + 1)
        c101 = self._canto(xi + 1, yi, zi + 1)
        c011 = self._canto(xi, yi + 1, zi + 1)
        c111 = self._canto(xi + 1, yi + 1, zi + 1)

        x00 = c000 + u * (c100 - c000)
        x10 = c010 + u * (c110 - c010)
        x01 = c001 + u * (c101 - c001)
        x11 = c011 + u * (c111 - c011)
        y0 = x00 + v * (x10 - x00)
        y1 = x01 + v * (x11 - x01)
        return y0 + w * (y1 - y0)

    def fbm(self, x, y, z, oitavas=5, ganho=0.5, lacunaridade=2.0):
        """Soma de oitavas: detalhe grosso somado a detalhes cada vez mais finos."""
        total = np.zeros_like(x)
        amp, freq, norma = 1.0, 1.0, 0.0
        for _ in range(oitavas):
            total += amp * self.valor(x * freq, y * freq, z * freq)
            norma += amp
            amp *= ganho
            freq *= lacunaridade
        return total / norma


# ------------------------------------------------------------ utilitarios ---
def cor(hexa):
    hexa = hexa.lstrip("#")
    return np.array([int(hexa[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0


def mistura(a, b, t):
    """Interpola duas cores (arrays RGB 0..1) por um mapa t."""
    t = np.clip(t, 0, 1)[..., None]
    return a * (1 - t) + b * t


def degraus(t, paleta):
    """Mapeia t (0..1) numa paleta de varias cores, interpolando entre vizinhas."""
    t = np.clip(t, 0, 1) * (len(paleta) - 1)
    i = np.clip(np.floor(t).astype(int), 0, len(paleta) - 2)
    f = (t - i)[..., None]
    pal = np.array(paleta)
    return pal[i] * (1 - f) + pal[i + 1] * f


def suave(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normalizar(m):
    return (m - m.min()) / (m.max() - m.min() + 1e-9)


def crateras(x, y, z, quantidade, semente, raio_min=0.015, raio_max=0.12):
    """Mapa de relevo com crateras: fundo mais escuro e borda mais clara.

    O raio segue uma distribuicao de potencia, como nas superficies reais:
    muitas crateras pequenas e poucas grandes.
    """
    rng = np.random.default_rng(semente)
    relevo = np.zeros_like(x)
    centros = rng.normal(size=(quantidade, 3))
    centros /= np.linalg.norm(centros, axis=1, keepdims=True)
    raios = raio_min + (raio_max - raio_min) * rng.random(quantidade) ** 3

    for (cx, cy, cz), r in zip(centros, raios):
        d = np.arccos(np.clip(x * cx + y * cy + z * cz, -1, 1))   # distancia angular
        dentro = d < r
        relevo[dentro] -= 0.55 * (1 - (d[dentro] / r) ** 2)       # fundo em cuia
        borda = (d >= r) & (d < r * 1.25)
        relevo[borda] += 0.35 * (1 - (d[borda] - r) / (0.25 * r))
    return relevo


def salvar(rgb, nome):
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")
    img.save(os.path.join(SAIDA, nome), quality=92)
    return img


# --------------------------------------------------------------- planetas ---
def mercurio(x, y, z, lat, lon):
    r = Ruido3D(101)
    base = r.fbm(x * 3, y * 3, z * 3, oitavas=6)
    tons = mistura(cor("#5F5B57"), cor("#B4AEA6"), normalizar(base))
    relevo = crateras(x, y, z, 320, 11)
    tons = tons * (1 + relevo[..., None] * 0.55)
    grao = r.fbm(x * 40, y * 40, z * 40, oitavas=2)
    return tons * (0.92 + 0.16 * grao[..., None])


def venus(x, y, z, lat, lon):
    r = Ruido3D(202)
    q = r.fbm(x * 2, y * 2, z * 2, oitavas=4)
    # nuvens esticadas na horizontal: z pesa mais que x e y
    nuvem = r.fbm(x * 1.6 + q * 2.2, y * 1.6 + q * 2.2, z * 4.5, oitavas=6)
    return degraus(normalizar(nuvem),
                   [cor("#B8844A"), cor("#D6A55C"), cor("#E6C184"), cor("#F1DDB0")])


def terra(x, y, z, lat, lon):
    r = Ruido3D(303)
    continentes = r.fbm(x * 1.8, y * 1.8, z * 1.8, oitavas=7)
    # o limiar e o percentil 71: ~71% da superficie vira oceano,
    # que e exatamente a resposta da pergunta SOLAR-03
    limiar = np.percentile(continentes, 71)
    terra_firme = continentes > limiar

    profundidade = normalizar(np.where(terra_firme, 0, limiar - continentes))
    oceano = mistura(cor("#2C6AB5"), cor("#0E2A5C"), profundidade * 1.4)

    umidade = r.fbm(x * 4 + 7, y * 4 + 7, z * 4 + 7, oitavas=5)
    solo = mistura(cor("#3F7A36"), cor("#9C8454"), suave(0.4, 0.62, umidade))
    rgb = np.where(terra_firme[..., None], solo, oceano)

    gelo = suave(0.72, 0.82, np.abs(lat) / (np.pi / 2) + 0.06 * (r.fbm(x * 6, y * 6, z * 6) - 0.5))
    rgb = mistura(rgb, np.ones(3), gelo)

    w = r.fbm(x * 2, y * 2, z * 2, oitavas=3)
    nuvens = r.fbm(x * 3 + w * 1.5, y * 3 + w * 1.5, z * 5, oitavas=6)
    return mistura(rgb, np.ones(3), suave(0.52, 0.72, nuvens) * 0.85)


def marte(x, y, z, lat, lon):
    r = Ruido3D(404)
    base = r.fbm(x * 2.5, y * 2.5, z * 2.5, oitavas=6)
    rgb = mistura(cor("#A8461E"), cor("#D88A52"), normalizar(base))
    escuras = suave(0.55, 0.7, r.fbm(x * 1.4 + 3, y * 1.4 + 3, z * 1.4 + 3, oitavas=5))
    rgb = mistura(rgb, cor("#5A2A18"), escuras * 0.7)
    rgb = rgb * (1 + crateras(x, y, z, 90, 44, raio_max=0.08)[..., None] * 0.35)
    calota = suave(0.86, 0.92, np.abs(lat) / (np.pi / 2))
    return mistura(rgb, cor("#F4EEE6"), calota)


def gigante_com_faixas(x, y, z, lat, lon, semente, paleta, faixas, turbulencia):
    r = Ruido3D(semente)
    ondulacao = r.fbm(x * 3, y * 3, z * 3, oitavas=5) - 0.5
    t = lat / (np.pi / 2) + turbulencia * ondulacao
    padrao = (0.55 * np.sin(t * faixas) + 0.3 * np.sin(t * faixas * 2.3 + 1.1)
              + 0.15 * np.sin(t * faixas * 5.1 + 2.0))
    return degraus(normalizar(padrao), paleta), r


def jupiter(x, y, z, lat, lon):
    rgb, r = gigante_com_faixas(
        x, y, z, lat, lon, 505,
        [cor("#8A5A36"), cor("#B07A3C"), cor("#D9B98E"), cor("#EFE3CC"), cor("#C99567")],
        faixas=14, turbulencia=0.10)
    # Grande Mancha Vermelha: elipse em torno de 22 graus sul
    dlon = np.angle(np.exp(1j * (lon - 0.9)))          # diferenca com volta no 180
    dlat = lat - np.radians(-22)
    elipse = (dlon / 0.34) ** 2 + (dlat / 0.13) ** 2
    mancha = 1 - suave(0.55, 1.0, elipse)
    miolo = 1 - suave(0.0, 0.45, elipse)
    rgb = mistura(rgb, cor("#B5553A"), mancha * 0.85)
    return mistura(rgb, cor("#9A3E2A"), miolo * 0.5)


def saturno(x, y, z, lat, lon):
    rgb, _ = gigante_com_faixas(
        x, y, z, lat, lon, 606,
        [cor("#B8975E"), cor("#D4B483"), cor("#E6D2A6"), cor("#F0E4C4")],
        faixas=10, turbulencia=0.04)
    return rgb


def urano(x, y, z, lat, lon):
    rgb, r = gigante_com_faixas(
        x, y, z, lat, lon, 707,
        [cor("#7FC4D1"), cor("#94D3DE"), cor("#A9DEE6")],
        faixas=6, turbulencia=0.02)
    return rgb * (0.97 + 0.06 * r.fbm(x * 5, y * 5, z * 5)[..., None])


def netuno(x, y, z, lat, lon):
    rgb, r = gigante_com_faixas(
        x, y, z, lat, lon, 808,
        [cor("#1C3F8C"), cor("#2E5EAA"), cor("#4A7ACB"), cor("#3561B0")],
        faixas=8, turbulencia=0.08)
    # Grande Mancha Escura
    dlon = np.angle(np.exp(1j * (lon + 1.4)))
    elipse = (dlon / 0.28) ** 2 + ((lat - np.radians(-20)) / 0.11) ** 2
    rgb = mistura(rgb, cor("#0F2560"), (1 - suave(0.5, 1.0, elipse)) * 0.8)
    # nuvens altas brancas, em fiapos horizontais
    fiapos = r.fbm(x * 3, y * 3, z * 14, oitavas=4)
    return mistura(rgb, cor("#E6F0FF"), suave(0.66, 0.76, fiapos) * 0.7)


def aneis_de_saturno(tamanho=1024):
    """Textura RGBA dos aneis, vista de cima, para um Quad deitado."""
    c = (np.arange(tamanho) + 0.5) / tamanho * 2 - 1
    X, Y = np.meshgrid(c, c)
    r = np.sqrt(X * X + Y * Y)                          # 0 no centro, 1 na borda

    interno, externo = 0.46, 0.98
    dentro = (r > interno) & (r < externo)
    s = np.clip((r - interno) / (externo - interno), 0, 1)

    # Perfil radial dos tres aneis principais, de dentro para fora:
    #   C - fraco e translucido
    #   B - o mais largo e brilhante
    #   divisao de Cassini - o vao escuro
    #   A - brilho medio, com o vao de Encke perto da borda
    anel_c = 0.28 * (1 - suave(0.24, 0.30, s))
    anel_b = 0.92 * suave(0.26, 0.32, s) * (1 - suave(0.58, 0.61, s))
    anel_a = 0.62 * suave(0.66, 0.69, s)
    densidade = anel_c + anel_b + anel_a
    densidade *= 1 - 0.85 * np.exp(-((s - 0.925) / 0.006) ** 2)      # vao de Encke

    # textura fina e irregular: ruido 1D sobre o raio, nao senoides regulares
    ruido = Ruido3D(909)
    fino = ruido.fbm(s * 60, np.zeros_like(s), np.zeros_like(s), oitavas=4)
    densidade *= 0.72 + 0.56 * fino
    densidade *= suave(0.0, 0.04, s) * (1 - suave(0.94, 1.0, s))
    alfa = np.where(dentro, np.clip(densidade, 0, 1) * 0.95, 0)

    rgb = degraus(s, [cor("#8C7A5C"), cor("#D8C49A"), cor("#EADBB6"), cor("#B8A47E")])
    rgba = np.dstack([np.clip(rgb, 0, 1), alfa])
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


PLANETAS = [
    ("Mercurio", mercurio), ("Venus", venus), ("Terra", terra), ("Marte", marte),
    ("Jupiter", jupiter), ("Saturno", saturno), ("Urano", urano), ("Netuno", netuno),
]


def main():
    os.makedirs(SAIDA, exist_ok=True)
    x, y, z, lat, lon = pontos_na_esfera()

    miniaturas = []
    for nome, funcao in PLANETAS:
        img = salvar(funcao(x, y, z, lat, lon), f"{nome}.jpg")
        miniaturas.append(img.resize((512, 256), Image.LANCZOS))
        print(f"  textura: {nome}.jpg")

    anel = aneis_de_saturno()
    anel.save(os.path.join(SAIDA, "Saturno_Aneis.png"))
    print("  textura: Saturno_Aneis.png")

    # folha de conferencia (nao vai para a Unity)
    folha = Image.new("RGB", (512 * 2, 256 * 4), (20, 19, 32))
    for i, m in enumerate(miniaturas):
        folha.paste(m, ((i % 2) * 512, (i // 2) * 256))
    folha.save(os.path.join(AQUI, "_previa_texturas.png"))
    print(f"\n{len(PLANETAS)} planetas + aneis em {SAIDA}")


if __name__ == "__main__":
    main()
