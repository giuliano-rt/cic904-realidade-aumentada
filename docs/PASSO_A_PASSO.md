# Passo a passo — montar o projeto na Unity

Roteiro completo, do projeto vazio até o APK. Segue a mesma sequência da
**Aula – AR** (Vuforia) e da **Aula – AR – 2** (build Android).

> **Tempo estimado:** 2h a 3h na primeira vez, sendo ~40 min só de espera
> (download da Vuforia, processamento dos alvos, build do Android).

---

## 0. Antes de começar

| Item | Onde conseguir | Quando precisa |
|---|---|---|
| **Unity 6 LTS — linha `6000.0.x`** (mínimo `6000.0.38f1`) | Unity Hub → Installs → Install Editor | sempre |
| Conta Vuforia + *App License Key* | https://developer.vuforia.com | sempre |
| Módulo **Android Build Support** (+ SDK, NDK, JDK) | marque junto com a instalação do editor | só para o APK |
| `bundletool.jar` | https://github.com/google/bundletool/releases | só para o APK |

> ⚠️ **A versão da Unity importa.** A tabela de compatibilidade da Vuforia
> (*Mobile Devices → Developer Tools*) pede **Unity Editor 6 LTS `6.0.38f1+`**,
> ou seja, a linha `6000.0.x`. Versões como `6000.3.x` e `6000.5.x` são
> posteriores, mas pertencem a outras linhas (Unity 6.3 e 6.5) e não são as que
> a Vuforia declara suportar.
>
> Vale testar com o que já estiver instalado — costuma funcionar —, mas **deixe
> o download da `6000.0.x` correndo em paralelo**, para não descobrir uma
> incompatibilidade sem tempo de reagir.

> 💡 **Android só é necessário para o APK.** O fluxo da Vuforia roda no editor
> com a webcam do PC (passo 7). Para uma apresentação em laboratório dá para
> demonstrar o jogo inteiro sem nenhum módulo de Android instalado — o que
> economiza vários GB de download.

---

## 1. Criar o projeto

1. Unity Hub → **New project** → template **Universal 3D** → nome `ARQuizQR`.
2. *(só se for gerar o APK agora)* `File → Build Profiles` → **Android** →
   **Switch Platform**. Fazer isso antes de importar tudo evita reimportar os
   assets depois. Sem o módulo de Android instalado, a plataforma não aparece —
   siga em **Windows** mesmo, que o projeto roda igual no editor.

---

## 2. Instalar a Vuforia Engine

1. Baixe o `add-vuforia-package-*.unitypackage` em
   https://developer.vuforia.com/downloads/sdk
2. Duplo clique no arquivo → **Import** na janela que abrir na Unity.
3. Aguarde a recompilação (a barra de progresso no canto inferior direito).

---

## 3. Licença e banco de alvos na Vuforia

### 3.1 Licença
1. No site: **My Account → License Manager → Get Basic** (gratuita).
2. Copie a **App License Key**.
3. Na Unity: `Window → Vuforia Configuration` → cole em **App License Key**.

### 3.2 Rastreamento — duas configurações obrigatórias

Ainda em `Window → Vuforia Configuration`:

| Campo | Valor | Padrão |
|---|---|---|
| **Max Simultaneous Tracked Images** | `1` | 1 |
| **Device Tracker → Auto Start Tracker** | **desmarcado** | marcado |

> ⚠️ **Com o Device Tracker ligado o jogo reconhece a carta errada.** Essa opção
> fica no `VuforiaConfiguration.asset`, o mesmo arquivo da chave de licença, que
> está no `.gitignore` — então **não vem junto com o repositório** e precisa ser
> refeita em cada máquina.
>
> Com o rastreamento do dispositivo ligado, uma carta que sai de vista vira
> `EXTENDED_TRACKED`: a Vuforia estima onde ela estaria. Na webcam, sem sensores de
> movimento, isso é só um palpite — a carta antiga segue ocupando o único espaço
> de rastreamento e a carta nova é lida como se fosse ela.
>
> O limite de **1 imagem simultânea** é o certo, e foi medido: com 8, as cartas
> parecidas iam travando nos espaços livres até sete alvos apontarem para uma
> única carta. Com 1, a Vuforia escolhe o melhor casamento e para de procurar.

### 3.3 Resolução da webcam

Por padrão a Vuforia pede **640×480** de qualquer webcam no PC, o que apaga
justamente os detalhes que diferenciam uma carta da outra. O projeto traz um
perfil a **1280×720** para a Logitech C922 em
`Assets/Editor/Vuforia/webcamprofiles.xml`. Na máquina de desenvolvimento ele
também foi copiado para o arquivo da própria Vuforia, em
`Library/PackageCache/com.ptc.vuforia.engine@…/Vuforia/Editor/EditorResources/webcamprofiles.xml`
— a `Library/` não vai para o repositório, então em outra máquina copie o bloco
`<webcam deviceName="c922 Pro Stream Webcam">` para lá.

Para outra câmera, o `deviceName` precisa ser o nome exato que a Unity mostra
(`WebCamTexture.devices`). A resolução real que a Vuforia recebe pode ser
conferida em Play Mode lendo `WebCamTexture.width/height`.

### 3.4 Como mostrar as cartas

- **Entre com a carta de uma vez, reta e inteira no quadro.** A primeira
  detecção é a que vale: se a carta entra deslizando, meio cortada, um sósia
  pode vencer — e com um alvo por vez a Vuforia só reavalia depois que a carta
  sai de vista. Se o planeta errado aparecer, tire a carta por 2 segundos e
  mostre de novo.
- **Mesa limpa.** Uma carta esquecida à vista ocupa o único espaço de
  rastreamento e bloqueia todas as outras.

### 3.3 Banco de alvos
1. No site: **My Account → Target Manager → Add Database**.
   - Nome: `QuizSistemaSolar` · Tipo: **Device**
2. Entre no database → **Add Target** para cada uma das 8 cartas:
   - Type: **Image**
   - File: `cartas/SOLAR-01_Mercurio.png` (e assim por diante)
   - Width: **`0.095`** (metros — a largura real da carta impressa)
   - **Name: `SOLAR-01`** ← 🔴 **exatamente igual ao `id` do `perguntas.json`**

> **Sobre o `Width`:** é a largura real da imagem depois de impressa, e é ela
> que define a escala do objeto 3D sobre a carta. Nas folhas A4 geradas por
> `tools/gerar_cartas.py`, cada carta tem 9,5 cm de largura (1120 px de uma
> folha de 2480 px a 210 mm). Se você imprimir os PNGs individuais em vez das
> folhas, meça com uma régua e use o valor medido.

> **O `Name` é a peça central.** O script `MarcadorPergunta` usa o nome do target
> para procurar a pergunta no JSON. Se você digitar `Solar 01` ou `mercurio`,
> a carta é reconhecida mas nenhuma pergunta aparece.

3. Confira o **Rating** de cada alvo: precisa ser ⭐⭐⭐⭐ ou ⭐⭐⭐⭐⭐.
   As cartas foram desenhadas para isso (tipografia grande + padrão de pontos
   assimétrico nas laterais). Se alguma vier com 2 estrelas, reimprima com mais
   contraste ou gere de novo com `python tools/gerar_cartas.py`.
4. **Download Database** → `Unity Editor` → duplo clique no arquivo → **Import**.

---

## 4. Trazer o código para o projeto

Copie para dentro de `Assets/`:

```
UnityAssets/Scripts/     ->  Assets/Scripts/
UnityAssets/Resources/   ->  Assets/Resources/
```

A pasta `Resources` precisa ter esse nome exato e ficar na raiz de `Assets/` —
é de lá que o `QuizManager` carrega o `perguntas.json` em tempo de execução.

Se o Console acusar erro de `TMPro`, vá em
`Window → TextMeshPro → Import TMP Essential Resources`.

---

## 5. Montar a cena

### 5.1 Câmera
1. Delete a **Main Camera** da Hierarchy.
2. Botão direito → `Vuforia Engine → AR Camera`.
3. Dê **Play**: a imagem da webcam deve aparecer na janela Game.
   Se não aparecer, em `Vuforia Configuration` desça até **Camera Device** e
   selecione sua webcam na lista.

### 5.2 Os 8 marcadores
Para cada carta (`SOLAR-01` a `SOLAR-08`):

1. Botão direito → `Vuforia Engine → Image Target`.
2. No Inspector, em **Image Target Behaviour**:
   - Type: `From Database`
   - Database: `QuizSistemaSolar`
   - Image Target: `SOLAR-01`
3. Renomeie o GameObject para `SOLAR-01` (ajuda a se achar na Hierarchy).
4. **Add Component** → `Marcador Pergunta`.
   Deixe o campo *Id Pergunta* **vazio** — ele usa o nome do target sozinho.
5. Crie o objeto 3D: botão direito no Image Target → `3D Object → Sphere`.
   - Scale: `0.08, 0.08, 0.08` · Position: `0, 0.06, 0`
   - **Add Component** → `Giro Objeto`
   - Crie um material em `Assets/Materials` com a cor do planeta e arraste nele.

> **Atalho:** monte o `SOLAR-01` completo, arraste-o para `Assets/Prefabs`, e
> duplique 7 vezes trocando só o *Image Target* e a cor do material.

### 5.3 O gerente do jogo
1. Botão direito → `Create Empty` → renomeie para `QuizManager`.
2. **Add Component** → `Quiz Manager`. Não precisa configurar nada.

---

## 6. Montar a interface

Botão direito → `UI → Canvas` (renomeie para `HUD`). No Canvas:
`Render Mode: Screen Space - Overlay`, `UI Scale Mode: Scale With Screen Size`,
`Reference Resolution: 1080 x 1920`.

### 6.1 Barra de pontuação (topo)
1. Dentro do HUD: `Create Empty` → `BarraPontuacao`, ancorada no topo.
2. Dois `UI → Text - TextMeshPro`: `TextoPontos` e `TextoProgresso`.
3. Um `UI → Image` chamado `BarraProgresso` com `Image Type: Filled`,
   `Fill Method: Horizontal`.
4. Um `UI → Button - TextMeshPro` chamado `BotaoReiniciar`.
5. No `BarraPontuacao`: **Add Component** → `Hud Pontuacao` e arraste
   cada objeto para o campo correspondente.

### 6.2 Painel da pergunta (rodapé)
1. Dentro do HUD: `UI → Panel` → renomeie para `PainelQuiz`.
2. **Add Component** → `Canvas Group`.
3. Dentro dele:
   - `TextoTitulo` (TextMeshPro)
   - `TextoEnunciado` (TextMeshPro)
   - `Create Empty` → `Alternativas` com **Vertical Layout Group**
     (`Child Force Expand Width` ligado, `Spacing` 12)
   - Dentro de `Alternativas`, quatro `UI → Button - TextMeshPro`
4. No `PainelQuiz`: **Add Component** → `Painel Quiz`. Arraste:
   - *Painel* → o próprio Canvas Group
   - *Texto Titulo* / *Texto Enunciado* → os textos
   - *Botoes Alternativa* → Size **4**, e arraste os 4 botões **em ordem**

### 6.3 Faixa de feedback
1. Dentro do HUD: `UI → Panel` → `PainelFeedback`, com **Canvas Group**.
2. Dentro: `TextoResultado` e `TextoExplicacao` (TextMeshPro).
3. **Add Component** → `Painel Feedback`. Arraste o Canvas Group, a `Image` do
   painel (campo *Fundo*) e os dois textos. Os campos de som são opcionais.

> Os três scripts de UI se comunicam com o `QuizManager` por eventos estáticos —
> nenhum deles precisa de referência ao outro. É o mesmo padrão do
> `UIButtonHandler` da Aula 04.

---

## 7. Testar no PC

1. Imprima `cartas/folha_impressao_1.png` e `folha_impressao_2.png`
   (A4, 100% de escala, **sem** "ajustar à página").
2. **Play** → aponte a webcam para uma carta.
3. Esperado: a esfera aparece girando sobre a carta, o painel sobe com a
   pergunta, e ao tocar numa alternativa a faixa de feedback aparece.

### Se algo não funcionar

| Sintoma | Causa provável |
|---|---|
| A carta é reconhecida mas nada aparece | Nome do target ≠ `id` no JSON. Veja o aviso no Console. |
| `Nao encontrei Assets/Resources/perguntas.json` | A pasta `Resources` não está na raiz de `Assets/`. |
| A esfera aparece rosa/sem cor | `Window → Rendering → Render Pipeline Converter` → selecionar tudo → **Initialize And Convert** (mesmo passo da Aula 1). |
| Uma carta abre a pergunta de outra | Rating baixo na Vuforia. Reimprima maior ou com mais contraste. |
| O painel não some ao tirar a carta | O `MarcadorPergunta` não está no Image Target. |

---

## 8. Gerar o APK (Aula – AR – 2)

1. `File → Build Profiles` → **Android** → marque **Build App Bundle**.
2. **Player Settings**:
   - *Product Name*: `AR Quiz Sistema Solar`
   - *Other Settings → Package Name*: `com.cic904.arquizqr`
   - *Other Settings → Minimum API Level*: **24** ou superior
3. **Build** → salve como `ARQuizQR.aab`.
4. Converta o `.aab` em APK instalável:

```bash
java -jar bundletool.jar build-apks --bundle=ARQuizQR.aab --output=ARQuizQR.apks --mode=universal
```

5. Descompacte `ARQuizQR.apks` como se fosse um `.zip`.
6. Copie `universal.apk` para o celular e instale.

---

## 9. Checklist da apresentação

- [ ] As 8 cartas impressas e testadas
- [ ] O jogo roda no PC com webcam **e** no celular
- [ ] Pontuação, feedback e reiniciar funcionando
- [ ] Repositório no GitHub com histórico de commits
- [ ] README com imagens/GIF do funcionamento
- [ ] Cada integrante sabe explicar uma parte do código
