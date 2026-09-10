"""
teste_qrgen.py - Verificacao do codificador: codifica e decodifica de volta.

Nao usa correcao de erro (a matriz gerada nao tem ruido), apenas desfaz
os passos do qrgen para conferir se o conteudo sobrevive ao round-trip.
"""
import qrgen


def _ler_formato(m, size):
    bits = 0
    for i in range(6):
        bits = (bits << 1) | m[8][i]
    bits = (bits << 1) | m[8][7]
    bits = (bits << 1) | m[8][8]
    bits = (bits << 1) | m[7][8]
    for i in range(6):
        bits = (bits << 1) | m[5 - i][8]
    bits ^= 0b101010000010010
    dados = bits >> 10
    nivel = dados >> 3
    mascara = dados & 0b111
    return nivel, mascara


def decodificar(m):
    size = len(m)
    versao = (size - 17) // 4
    nivel, mascara = _ler_formato(m, size)
    assert nivel == qrgen.EC_LEVEL_BITS, f"nivel de EC inesperado: {nivel}"

    _, reservado, _ = qrgen._matriz_base(versao)

    # desfaz a mascara
    desmascarado = [linha[:] for linha in m]
    for r in range(size):
        for c in range(size):
            if not reservado[r][c] and qrgen._mascara(r, c, mascara):
                desmascarado[r][c] ^= 1

    # le os bits na mesma ordem em ziguezague
    bits = []
    col = size - 1
    subindo = True
    while col > 0:
        if col == 6:
            col -= 1
        for i in range(size):
            linha = (size - 1 - i) if subindo else i
            for c in (col, col - 1):
                if not reservado[linha][c]:
                    bits.append(desmascarado[linha][c])
        subindo = not subindo
        col -= 2

    # bits -> codewords
    codewords = []
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        codewords.append(v)

    # desfaz a intercalacao (apenas a parte de dados)
    blocos, dados_por_bloco, ec_por_bloco = qrgen.EC_M[versao]
    total_dados = blocos * dados_por_bloco
    grupos = [[] for _ in range(blocos)]
    for i in range(total_dados):
        grupos[i % blocos].append(codewords[i])
    dados = [cw for g in grupos for cw in g]

    # le o payload em modo byte
    fluxo = []
    for cw in dados:
        for i in range(7, -1, -1):
            fluxo.append((cw >> i) & 1)

    def take(n):
        nonlocal fluxo
        v = 0
        for b in fluxo[:n]:
            v = (v << 1) | b
        fluxo = fluxo[n:]
        return v

    modo = take(4)
    assert modo == 0b0100, f"modo inesperado: {modo:04b}"
    tamanho = take(8)
    conteudo = bytes(take(8) for _ in range(tamanho))
    return conteudo.decode("utf-8"), versao, mascara


CASOS = [
    "SOLAR-01",
    "SOLAR-08",
    "https://github.com/usuario/ar-quiz-qr#q03",
    "Q1",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghij",
]

falhas = 0
for caso in CASOS:
    for minv in (1, 3):
        m = qrgen.gerar_matriz(caso, min_version=minv)
        try:
            lido, versao, mascara = decodificar(m)
        except Exception as e:
            print(f"ERRO   {caso!r} (minv={minv}): {e}")
            falhas += 1
            continue
        ok = lido == caso
        falhas += 0 if ok else 1
        marca = "ok  " if ok else "FALHA"
        print(f"{marca} v{versao} mascara={mascara} {len(m)}x{len(m)} "
              f"{caso!r} -> {lido!r}")

print()
print("TODOS OS TESTES PASSARAM" if falhas == 0 else f"{falhas} FALHA(S)")
