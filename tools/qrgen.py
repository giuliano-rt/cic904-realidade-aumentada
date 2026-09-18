"""
qrgen.py - Codificador de QR Code em Python puro (sem dependencias externas).

Suporta modo byte, nivel de correcao de erro M, versoes 1 a 6.
Escrito para o projeto "Jogo Educacional em Realidade Aumentada com QR Codes"
(CIC904 - Multimidia e Realidade Virtual).

Uso como biblioteca:
    from qrgen import gerar_matriz
    matriz = gerar_matriz("SOLAR-01")   # lista de listas com 0/1
"""

# ---------------------------------------------------------------- GF(256) ---
# Campo de Galois usado pelo Reed-Solomon do QR (polinomio primitivo 0x11D).
EXP = [0] * 512
LOG = [0] * 256

_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def rs_generator_poly(nsym):
    """Polinomio gerador de grau nsym."""
    g = [1]
    for i in range(nsym):
        # multiplica g por (x - alpha^i)
        novo = [0] * (len(g) + 1)
        for j, coef in enumerate(g):
            novo[j] ^= coef
            novo[j + 1] ^= gf_mul(coef, EXP[i])
        g = novo
    return g


def rs_encode(data, nsym):
    """Devolve os nsym codewords de correcao de erro para 'data'."""
    gen = rs_generator_poly(nsym)
    res = list(data) + [0] * nsym
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= gf_mul(gen[j], coef)
    return res[len(data):]


# ------------------------------------------------- Tabelas do padrao QR -----
# Nivel de correcao M, versoes 1..6.
# versao: (num_blocos, data_codewords_por_bloco, ec_codewords_por_bloco)
EC_M = {
    1: (1, 16, 10),
    2: (1, 28, 16),
    3: (1, 44, 26),
    4: (2, 32, 18),
    5: (2, 43, 24),
    6: (4, 27, 16),
}

# Centros dos padroes de alinhamento por versao.
ALIGN = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
}

# Bits remanescentes apos os codewords (versoes 2-6 usam 7).
REMAINDER = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7}

EC_LEVEL_BITS = 0b00  # nivel M


# ------------------------------------------------------------ Codificacao ---
def _escolher_versao(n_bytes, min_version=1):
    for v in range(max(1, min_version), 7):
        blocos, dados_por_bloco, _ = EC_M[v]
        capacidade = blocos * dados_por_bloco
        # 4 bits de modo + 8 bits de contagem + 8 bits por byte
        necessario = (4 + 8 + 8 * n_bytes + 7) // 8
        if necessario <= capacidade:
            return v
    raise ValueError("Conteudo grande demais para as versoes 1-6 (nivel M).")


def _bitstream(dados, versao):
    blocos, dados_por_bloco, _ = EC_M[versao]
    total_dados = blocos * dados_por_bloco

    bits = []

    def push(valor, n):
        for i in range(n - 1, -1, -1):
            bits.append((valor >> i) & 1)

    push(0b0100, 4)          # indicador de modo byte
    push(len(dados), 8)      # contagem (8 bits para versoes 1-9 em modo byte)
    for b in dados:
        push(b, 8)

    # terminador
    for _ in range(min(4, total_dados * 8 - len(bits))):
        bits.append(0)
    # alinha em byte
    while len(bits) % 8:
        bits.append(0)

    codewords = [int("".join(str(b) for b in bits[i:i + 8]), 2)
                 for i in range(0, len(bits), 8)]

    # bytes de preenchimento alternados ate encher a capacidade
    pad = [0xEC, 0x11]
    i = 0
    while len(codewords) < total_dados:
        codewords.append(pad[i % 2])
        i += 1
    return codewords


def _intercalar(codewords, versao):
    blocos, dados_por_bloco, ec_por_bloco = EC_M[versao]

    grupos_dados = [codewords[i * dados_por_bloco:(i + 1) * dados_por_bloco]
                    for i in range(blocos)]
    grupos_ec = [rs_encode(g, ec_por_bloco) for g in grupos_dados]

    final = []
    for i in range(dados_por_bloco):
        for g in grupos_dados:
            final.append(g[i])
    for i in range(ec_por_bloco):
        for g in grupos_ec:
            final.append(g[i])

    bits = []
    for cw in final:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)
    bits.extend([0] * REMAINDER[versao])
    return bits


# ---------------------------------------------------------------- Matriz ----
def _matriz_base(versao):
    size = 17 + 4 * versao
    m = [[None] * size for _ in range(size)]
    reservado = [[False] * size for _ in range(size)]

    def finder(r0, c0):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < size and 0 <= c < size:
                    if dr in (-1, 7) or dc in (-1, 7):
                        val = 0                      # separador branco
                    elif dr in (0, 6) or dc in (0, 6):
                        val = 1                      # moldura externa
                    elif 2 <= dr <= 4 and 2 <= dc <= 4:
                        val = 1                      # nucleo 3x3
                    else:
                        val = 0
                    m[r][c] = val
                    reservado[r][c] = True

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    # padroes de tempo
    for i in range(size):
        if m[6][i] is None:
            m[6][i] = 1 if i % 2 == 0 else 0
            reservado[6][i] = True
        if m[i][6] is None:
            m[i][6] = 1 if i % 2 == 0 else 0
            reservado[i][6] = True

    # padroes de alinhamento
    centros = ALIGN[versao]
    for r in centros:
        for c in centros:
            if reservado[r][c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    val = 1 if (abs(dr) == 2 or abs(dc) == 2 or
                                (dr == 0 and dc == 0)) else 0
                    m[r + dr][c + dc] = val
                    reservado[r + dr][c + dc] = True

    # modulo escuro fixo
    m[size - 8][8] = 1
    reservado[size - 8][8] = True

    # areas de informacao de formato (preenchidas depois de escolher a mascara)
    for i in range(9):
        reservado[8][i] = True
        reservado[i][8] = True
    for i in range(8):
        reservado[8][size - 1 - i] = True
    for i in range(7):
        reservado[size - 1 - i][8] = True

    return m, reservado, size


def _colocar_dados(m, reservado, size, bits):
    idx = 0
    col = size - 1
    subindo = True
    while col > 0:
        if col == 6:          # pula a coluna do padrao de tempo
            col -= 1
        for i in range(size):
            linha = (size - 1 - i) if subindo else i
            for c in (col, col - 1):
                if not reservado[linha][c]:
                    m[linha][c] = bits[idx] if idx < len(bits) else 0
                    idx += 1
        subindo = not subindo
        col -= 2


def _mascara(i, j, padrao):
    if padrao == 0:
        return (i + j) % 2 == 0
    if padrao == 1:
        return i % 2 == 0
    if padrao == 2:
        return j % 3 == 0
    if padrao == 3:
        return (i + j) % 3 == 0
    if padrao == 4:
        return (i // 2 + j // 3) % 2 == 0
    if padrao == 5:
        return (i * j) % 2 + (i * j) % 3 == 0
    if padrao == 6:
        return ((i * j) % 2 + (i * j) % 3) % 2 == 0
    return ((i + j) % 2 + (i * j) % 3) % 2 == 0


def _bits_formato(mascara):
    """15 bits de informacao de formato (BCH 15,5 + mascara fixa 0x5412)."""
    dados = (EC_LEVEL_BITS << 3) | mascara
    d = dados << 10
    g = 0b10100110111
    for i in range(4, -1, -1):
        if d & (1 << (i + 10)):
            d ^= g << i
    return ((dados << 10) | d) ^ 0b101010000010010


def _aplicar_formato(m, size, mascara):
    fmt = _bits_formato(mascara)
    # copia 1: canto superior esquerdo
    for i in range(6):
        m[8][i] = (fmt >> (14 - i)) & 1
    m[8][7] = (fmt >> 8) & 1
    m[8][8] = (fmt >> 7) & 1
    m[7][8] = (fmt >> 6) & 1
    for i in range(6):
        m[5 - i][8] = (fmt >> (5 - i)) & 1
    # copia 2: bordas direita e inferior
    for i in range(8):
        m[8][size - 1 - i] = (fmt >> i) & 1
    for i in range(7):
        m[size - 1 - i][8] = (fmt >> (14 - i)) & 1
    m[size - 8][8] = 1


def _penalidade(m, size):
    total = 0

    # Regra 1: sequencias de 5 ou mais modulos iguais em linha/coluna
    for k in range(size):
        for eixo in range(2):
            atual, cont = None, 0
            for i in range(size):
                v = m[k][i] if eixo == 0 else m[i][k]
                if v == atual:
                    cont += 1
                else:
                    if cont >= 5:
                        total += 3 + (cont - 5)
                    atual, cont = v, 1
            if cont >= 5:
                total += 3 + (cont - 5)

    # Regra 2: blocos 2x2 da mesma cor
    for r in range(size - 1):
        for c in range(size - 1):
            v = m[r][c]
            if v == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                total += 3

    # Regra 3: padrao 1:1:3:1:1 acompanhado de area clara
    alvo1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    alvo2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]
    for k in range(size):
        linha = list(m[k])
        coluna = [m[i][k] for i in range(size)]
        for seq in (linha, coluna):
            for c in range(size - 10):
                trecho = seq[c:c + 11]
                if trecho == alvo1 or trecho == alvo2:
                    total += 40

    # Regra 4: desvio da proporcao ideal de modulos escuros (50%)
    escuros = sum(sum(l) for l in m)
    percent = escuros * 100 // (size * size)
    total += 10 * (abs(percent - 50) // 5)

    return total


# ------------------------------------------------------------ API publica ---
def gerar_matriz(texto, min_version=1, mascara=None):
    """Codifica 'texto' e devolve a matriz final do QR (lista de listas 0/1).

    Por padrao escolhe, entre as 8 mascaras, a de menor penalidade -- o que o
    padrao recomenda. Passar 'mascara' (0 a 7) forca uma mascara especifica.
    Qualquer uma e valida: o leitor descobre qual foi usada pela informacao de
    formato gravada no proprio codigo.

    Forcar a mascara serve para deixar QRs de conteudo parecido com aparencia
    diferente: e a mascara que domina o visual do miolo do codigo.
    """
    dados = texto.encode("utf-8")
    versao = _escolher_versao(len(dados), min_version)
    codewords = _bitstream(dados, versao)
    bits = _intercalar(codewords, versao)

    candidatas = range(8) if mascara is None else [mascara]
    melhor, melhor_nota = None, None
    for mascara in candidatas:
        m, reservado, size = _matriz_base(versao)
        _colocar_dados(m, reservado, size, bits)
        for r in range(size):
            for c in range(size):
                if not reservado[r][c] and _mascara(r, c, mascara):
                    m[r][c] ^= 1
        _aplicar_formato(m, size, mascara)
        nota = _penalidade(m, size)
        if melhor_nota is None or nota < melhor_nota:
            melhor, melhor_nota = m, nota

    return melhor


def para_ascii(matriz):
    """Renderiza a matriz no terminal (util para conferir visualmente)."""
    largura = len(matriz) + 4
    linhas = ["  " * largura, "  " * largura]
    for linha in matriz:
        linhas.append("    " + "".join("##" if v else "  " for v in linha) + "    ")
    linhas.append("  " * largura)
    linhas.append("  " * largura)
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    conteudo = sys.argv[1] if len(sys.argv) > 1 else "SOLAR-01"
    print(para_ascii(gerar_matriz(conteudo)))
