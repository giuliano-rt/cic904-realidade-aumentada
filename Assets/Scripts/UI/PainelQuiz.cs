using ARQuiz.Core;
using ARQuiz.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ARQuiz.UI
{
    /// <summary>
    /// Painel que aparece na tela quando uma carta e reconhecida: mostra o
    /// enunciado e as alternativas, e devolve a escolha do jogador ao QuizManager.
    ///
    /// As alternativas sao embaralhadas, mas com uma semente derivada do id da
    /// pergunta. Assim a ordem muda de pergunta para pergunta (o jogador nao
    /// decora "a resposta e sempre a letra C") e ao mesmo tempo continua estavel
    /// quando a mesma carta sai e volta ao campo de visao da camera.
    /// </summary>
    public class PainelQuiz : MonoBehaviour
    {
        [Header("Estrutura")]
        [SerializeField] private CanvasGroup painel;
        [SerializeField] private TMP_Text textoTitulo;
        [SerializeField] private TMP_Text textoEnunciado;
        [SerializeField] private Button[] botoesAlternativa = new Button[4];

        [Header("Cores do feedback")]
        [SerializeField] private Color corAcerto = new Color(0.20f, 0.71f, 0.39f);
        [SerializeField] private Color corErro = new Color(0.86f, 0.27f, 0.27f);

        private static readonly string[] Letras = { "A", "B", "C", "D", "E", "F" };

        private Pergunta _perguntaAtual;
        private int[] _ordem;                 // posicao na tela -> indice original
        private ColorBlock[] _coresOriginais;
        private bool _travado;

        // --- Ciclo de vida ----------------------------------------------------
        private void Awake()
        {
            _coresOriginais = new ColorBlock[botoesAlternativa.Length];
            for (int i = 0; i < botoesAlternativa.Length; i++)
            {
                if (botoesAlternativa[i] == null)
                {
                    continue;
                }
                _coresOriginais[i] = botoesAlternativa[i].colors;

                int posicao = i;   // copia local: sem isso todo botao usaria o ultimo i
                botoesAlternativa[i].onClick.AddListener(() => AoClicarAlternativa(posicao));
            }

            Esconder();
        }

        private void OnEnable()
        {
            QuizManager.AoAbrirPergunta += Abrir;
            QuizManager.AoRevisitarPergunta += Revisitar;
            QuizManager.AoFecharPergunta += Esconder;
        }

        private void OnDisable()
        {
            QuizManager.AoAbrirPergunta -= Abrir;
            QuizManager.AoRevisitarPergunta -= Revisitar;
            QuizManager.AoFecharPergunta -= Esconder;
        }

        // --- Reacoes aos eventos ----------------------------------------------
        private void Abrir(Pergunta pergunta)
        {
            Montar(pergunta);
            _travado = false;
            DefinirVisibilidade(true);
        }

        private void Revisitar(Pergunta pergunta, bool acertouAntes)
        {
            Montar(pergunta);
            _travado = true;

            // A carta ja foi respondida: mostra o gabarito em vez de deixar
            // o jogador pontuar de novo com a mesma carta.
            for (int i = 0; i < botoesAlternativa.Length; i++)
            {
                Button botao = botoesAlternativa[i];
                if (botao == null || !botao.gameObject.activeSelf)
                {
                    continue;
                }
                bool ehCorreta = _ordem[i] == pergunta.correta;
                Pintar(i, ehCorreta ? corAcerto : corErro);
            }

            textoTitulo.text = acertouAntes
                ? $"{pergunta.titulo}  ·  já respondida (acertou)"
                : $"{pergunta.titulo}  ·  já respondida";

            DefinirVisibilidade(true);
        }

        private void Esconder()
        {
            _perguntaAtual = null;
            DefinirVisibilidade(false);
        }

        // --- Montagem do painel -----------------------------------------------
        private void Montar(Pergunta pergunta)
        {
            _perguntaAtual = pergunta;
            _ordem = EmbaralharEstavel(pergunta.alternativas.Length, SementeDe(pergunta.id));

            textoTitulo.text = pergunta.titulo;
            textoEnunciado.text = pergunta.enunciado;

            for (int i = 0; i < botoesAlternativa.Length; i++)
            {
                Button botao = botoesAlternativa[i];
                if (botao == null)
                {
                    continue;
                }

                bool usado = i < _ordem.Length;
                botao.gameObject.SetActive(usado);
                if (!usado)
                {
                    continue;
                }

                botao.interactable = true;
                botao.colors = _coresOriginais[i];

                TMP_Text rotulo = botao.GetComponentInChildren<TMP_Text>();
                if (rotulo != null)
                {
                    string letra = i < Letras.Length ? Letras[i] : (i + 1).ToString();
                    rotulo.text = $"{letra}.  {pergunta.alternativas[_ordem[i]]}";
                }
            }
        }

        private void AoClicarAlternativa(int posicaoNaTela)
        {
            if (_travado || _perguntaAtual == null || _ordem == null)
            {
                return;
            }
            if (posicaoNaTela < 0 || posicaoNaTela >= _ordem.Length)
            {
                return;
            }
            if (QuizManager.Instance == null)
            {
                Debug.LogError("[PainelQuiz] Nenhum QuizManager na cena para receber a resposta.");
                return;
            }

            _travado = true;   // impede toque duplo antes do feedback aparecer

            int indiceOriginal = _ordem[posicaoNaTela];
            bool acertou = QuizManager.Instance.Responder(_perguntaAtual.id, indiceOriginal);

            Pintar(posicaoNaTela, acertou ? corAcerto : corErro);

            if (!acertou)
            {
                // Destaca tambem qual era a alternativa certa.
                for (int i = 0; i < _ordem.Length; i++)
                {
                    if (_ordem[i] == _perguntaAtual.correta)
                    {
                        Pintar(i, corAcerto);
                        break;
                    }
                }
            }

            for (int i = 0; i < botoesAlternativa.Length; i++)
            {
                if (botoesAlternativa[i] != null)
                {
                    botoesAlternativa[i].interactable = false;
                }
            }
        }

        private void Pintar(int posicao, Color cor)
        {
            Button botao = botoesAlternativa[posicao];
            if (botao == null)
            {
                return;
            }

            // O botao fica desabilitado depois de responder, e com a transicao
            // ColorTint quem vale nessa hora e o disabledColor.
            ColorBlock cores = botao.colors;
            cores.normalColor = cor;
            cores.disabledColor = cor;
            cores.highlightedColor = cor;
            cores.selectedColor = cor;
            botao.colors = cores;
        }

        private void DefinirVisibilidade(bool visivel)
        {
            if (painel == null)
            {
                return;
            }
            painel.alpha = visivel ? 1f : 0f;
            painel.interactable = visivel;
            painel.blocksRaycasts = visivel;
        }

        // --- Embaralhamento determinístico ------------------------------------
        /// <summary>
        /// Hash FNV-1a do id. Nao uso string.GetHashCode porque ele nao tem
        /// valor garantido entre plataformas (PC e Android poderiam embaralhar
        /// de formas diferentes).
        /// </summary>
        private static int SementeDe(string id)
        {
            unchecked
            {
                const uint offset = 2166136261;
                const uint primo = 16777619;
                uint hash = offset;
                foreach (char c in id)
                {
                    hash ^= c;
                    hash *= primo;
                }
                return (int)(hash & 0x7FFFFFFF);
            }
        }

        private static int[] EmbaralharEstavel(int tamanho, int semente)
        {
            int[] ordem = new int[tamanho];
            for (int i = 0; i < tamanho; i++)
            {
                ordem[i] = i;
            }

            var rnd = new System.Random(semente);
            for (int i = tamanho - 1; i > 0; i--)
            {
                int j = rnd.Next(i + 1);
                (ordem[i], ordem[j]) = (ordem[j], ordem[i]);
            }
            return ordem;
        }
    }
}
