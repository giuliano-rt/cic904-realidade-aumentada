# AR Quiz QR — Jogo Educacional em Realidade Aumentada

Projeto da disciplina **CIC904 — Multimídia e Realidade Virtual** (Prof. Isaac).

Jogo educacional de perguntas e respostas em Realidade Aumentada. Ao apontar a
câmera para uma carta impressa com QR Code, o aplicativo reconhece o marcador,
exibe um objeto virtual 3D sobre a carta e abre uma pergunta sobre o tema. O
jogador responde tocando em uma das alternativas na tela, recebe o retorno de
acerto ou erro com uma explicação, e acumula pontos ao longo das 8 cartas.

**Tema do conteúdo:** Sistema Solar.

<!-- TODO antes da entrega final: substituir por um GIF real do jogo rodando -->
<!-- ![Demonstração](docs/img/demo.gif) -->

---

## Funcionalidades

- **Reconhecimento de marcadores** — 8 cartas impressas rastreadas pela Vuforia
  Engine, cada uma ligada a uma pergunta diferente.
- **Objeto virtual sobre a carta** — um planeta 3D que gira e flutua enquanto o
  marcador está em vista, e some quando a carta sai do campo de visão.
- **Quiz com 4 alternativas** — enunciado e opções montados em tempo de
  execução a partir de um arquivo de dados, sem nada escrito na cena.
- **Alternativas embaralhadas de forma determinística** — a ordem muda de
  pergunta para pergunta (o jogador não decora a posição da resposta), mas
  permanece a mesma quando a carta sai e volta ao campo de visão.
- **Retorno imediato** — a alternativa escolhida fica verde ou vermelha, a
  correta é destacada, e uma faixa mostra a explicação do conteúdo.
- **Pontuação e progresso** — 10 pontos por acerto, com contagem de acertos,
  cartas respondidas e barra de progresso.
- **Proteção contra repontuação** — reapontar a câmera para uma carta já
  respondida mostra o gabarito em vez de somar pontos de novo.
- **Reiniciar** — zera o progresso sem recarregar a cena.
- **Gerador de cartas próprio** — script em Python que codifica os QR Codes do
  zero e monta as cartas prontas para impressão.

---

## Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Motor | Unity 6 LTS (`6000.0.x`), Universal Render Pipeline |
| Realidade Aumentada | Vuforia Engine — *Image Targets* (rastreamento por marcador) |
| Linguagem do jogo | C# |
| Interface | Unity UI (uGUI) + TextMeshPro |
| Dados | JSON lido com `JsonUtility` a partir de `Assets/Resources` |
| Geração das cartas | Python 3 + Pillow, com codificador de QR Code próprio |
| Build Android | Android Build Support + `bundletool` |

### Sobre o codificador de QR Code

O arquivo [`tools/qrgen.py`](tools/qrgen.py) implementa a codificação de QR Code
**em Python puro, sem bibliotecas externas**: campo de Galois GF(256),
correção de erro Reed–Solomon, construção da matriz com os padrões de
localização, alinhamento e tempo, avaliação das 8 máscaras pelas quatro regras
de penalidade do padrão, e a informação de formato com BCH(15,5).

A verificação está em [`tools/teste_qrgen.py`](tools/teste_qrgen.py), que
decodifica a matriz gerada e compara com o texto de entrada:

```bash
cd tools
python teste_qrgen.py
```

---

## Como as peças conversam

```
  Carta impressa                Vuforia Engine
  (QR + arte única)  ──────>  reconhece o Image Target
                                      │
                                      ▼
                            MarcadorPergunta.cs
                       (lê o nome do target: "SOLAR-03")
                                      │
                                      ▼
                              QuizManager.cs
                   procura a pergunta no perguntas.json
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             PainelQuiz.cs   PainelFeedback.cs   HudPontuacao.cs
```

A comunicação entre o `QuizManager` e a interface acontece por **eventos
estáticos** (`event Action`), o mesmo padrão apresentado na Aula 04. O
`QuizManager` não guarda referência a nenhum objeto de UI, e os scripts de UI
não procuram o `QuizManager` na cena — cada um apenas assina os eventos que lhe
interessam em `OnEnable` e cancela a assinatura em `OnDisable`.

O nome do Image Target na Vuforia é a chave que liga o mundo físico ao banco de
perguntas: o target `SOLAR-03` encontra a pergunta de `id` `SOLAR-03`. Por isso
dá para acrescentar perguntas sem tocar em nenhuma linha de C#.

---

## Estrutura do repositório

```
├── UnityAssets/
│   ├── Scripts/
│   │   ├── Data/Pergunta.cs            modelo de dados do JSON
│   │   ├── Core/QuizManager.cs         regras do jogo, pontuação e eventos
│   │   ├── AR/MarcadorPergunta.cs      ponte entre a Vuforia e o jogo
│   │   ├── AR/GiroObjeto.cs            animação do objeto 3D
│   │   └── UI/                         painel do quiz, feedback e HUD
│   └── Resources/perguntas.json        banco de perguntas
├── tools/
│   ├── qrgen.py                        codificador de QR Code
│   ├── teste_qrgen.py                  verificação por round-trip
│   └── gerar_cartas.py                 monta as cartas imprimíveis
├── cartas/                             PNGs prontos para imprimir e para a Vuforia
└── docs/PASSO_A_PASSO.md               montagem do projeto na Unity
```

---

## Dependências, versões e build

### Requisitos

- **Unity 6 LTS**, linha `6000.0.x` (mínimo `6000.0.38f1`, conforme a tabela
  de compatibilidade da Vuforia)
- **Android Build Support** (SDK + NDK + JDK) — apenas para gerar o APK
- **Vuforia Engine** — https://developer.vuforia.com/downloads/sdk
- Conta gratuita na Vuforia (para a *App License Key* e o *Target Manager*)
- **Python 3** com **Pillow** — apenas para regerar as cartas
- **Java** + **bundletool** — apenas para gerar o APK

### Montagem do projeto

O roteiro completo, do projeto vazio até o APK, está em
**[`docs/PASSO_A_PASSO.md`](docs/PASSO_A_PASSO.md)**.

Resumo:

1. Projeto Unity **Universal 3D** → `Build Profiles` → **Android** → *Switch Platform*
2. Importar o `.unitypackage` da Vuforia Engine
3. Colar a *App License Key* em `Window → Vuforia Configuration`
4. Criar o database `QuizSistemaSolar` no *Target Manager* e subir os PNGs de
   `cartas/`, **nomeando cada alvo exatamente como o `id` do JSON** (`SOLAR-01`…)
5. Copiar `UnityAssets/Scripts` e `UnityAssets/Resources` para `Assets/`
6. Montar a cena: `AR Camera`, os 8 `Image Target` e o `QuizManager`
7. `File → Build Profiles` → **Build App Bundle** → **Build**

### Do `.aab` para o APK

```bash
java -jar bundletool.jar build-apks --bundle=ARQuizQR.aab --output=ARQuizQR.apks --mode=universal
```

Depois descompacte o `.apks` como um `.zip` e instale o `universal.apk` no celular.

### Regerar as cartas

Para trocar o tema ou acrescentar perguntas, edite
`UnityAssets/Resources/perguntas.json` e rode:

```bash
cd tools
python gerar_cartas.py
```

Os PNGs individuais vão para o *Target Manager* da Vuforia; as folhas A4
(`folha_impressao_*.png`) são para imprimir e usar no jogo.

---

## Por que as cartas não são QR Codes "puros"

A Vuforia rastreia por **pontos de característica naturais** da imagem, e não
decodifica o QR. QR Codes isolados são parecidos entre si — os três marcadores
de canto são idênticos em todos —, o que aumenta a chance de o rastreador
confundir uma carta com outra.

Por isso cada carta combina o QR Code com elementos próprios: o nome do planeta
em tipografia grande, uma moldura colorida e uma constelação assimétrica de
pontos e traços nas laterais, gerada de forma determinística a partir do `id`.
São esses elementos que empurram a avaliação dos alvos no *Target Manager* para
4–5 estrelas e deixam o rastreamento estável.

---

## Equipe

<!-- TODO: preencher com os nomes dos integrantes -->

| Integrante | Responsabilidade |
|---|---|
| | |
