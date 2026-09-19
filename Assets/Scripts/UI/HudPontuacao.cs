using ARQuiz.Core;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ARQuiz.UI
{
    /// <summary>
    /// Barra fixa no topo da tela com a pontuacao e o progresso do jogo.
    /// Tambem liga o botao de reiniciar, quando existir.
    /// </summary>
    public class HudPontuacao : MonoBehaviour
    {
        [Header("Textos")]
        [SerializeField] private TMP_Text textoPontos;
        [SerializeField] private TMP_Text textoProgresso;

        [Header("Progresso (opcional)")]
        [SerializeField] private Image barraProgresso;

        [Header("Reiniciar (opcional)")]
        [SerializeField] private Button botaoReiniciar;
        [Tooltip("Espaco entre o texto de progresso e o botao, quando o botao aparece.")]
        [SerializeField] private float espacoAteBotao = 16f;

        private float _bordaDireitaProgresso;

        private void Awake()
        {
            if (textoProgresso != null)
            {
                _bordaDireitaProgresso = textoProgresso.rectTransform.offsetMax.x;
            }

            if (botaoReiniciar != null)
            {
                botaoReiniciar.onClick.AddListener(AoClicarReiniciar);

                var rotulo = botaoReiniciar.GetComponentInChildren<TMP_Text>();
                if (rotulo != null)
                {
                    rotulo.text = "Jogar de novo";
                }
                botaoReiniciar.gameObject.SetActive(false);
            }
        }

        private void OnEnable()
        {
            QuizManager.AoAtualizarPlacar += Atualizar;
        }

        private void OnDisable()
        {
            QuizManager.AoAtualizarPlacar -= Atualizar;
        }

        private void OnDestroy()
        {
            if (botaoReiniciar != null)
            {
                botaoReiniciar.onClick.RemoveListener(AoClicarReiniciar);
            }
        }

        private void Atualizar(int pontos, int acertos, int respondidas, int total)
        {
            if (textoPontos != null)
            {
                textoPontos.text = $"{pontos} pts";
            }

            if (textoProgresso != null)
            {
                string rotuloAcertos = acertos == 1 ? "1 acerto" : $"{acertos} acertos";
                textoProgresso.text = $"{rotuloAcertos}  ·  {respondidas}/{total} cartas";
            }

            if (barraProgresso != null)
            {
                barraProgresso.fillAmount = total > 0 ? (float)respondidas / total : 0f;
            }

            // O botao so aparece quando a partida acabou, e vira "Jogar de novo".
            // Um botao desabilitado no meio da partida so geraria a pergunta
            // "por que nao consigo clicar?"; escondido, a pergunta nem surge.
            if (botaoReiniciar != null)
            {
                bool terminou = total > 0 && respondidas >= total;
                botaoReiniciar.gameObject.SetActive(terminou);
                AbrirEspacoParaBotao(terminou);
            }
        }

        /// <summary>
        /// Durante a partida o botao fica escondido e o texto de progresso usa a
        /// largura toda. Quando o botao aparece, o texto termina antes dele, em vez
        /// de ficar por baixo. A borda e calculada a partir do proprio botao, entao
        /// continua certa se o botao mudar de tamanho.
        /// </summary>
        private void AbrirEspacoParaBotao(bool botaoVisivel)
        {
            if (textoProgresso == null)
            {
                return;
            }

            var rt = textoProgresso.rectTransform;
            float direita = _bordaDireitaProgresso;
            if (botaoVisivel)
            {
                var botao = (RectTransform)botaoReiniciar.transform;
                // os dois estao ancorados na borda direita da barra, entao a borda
                // esquerda do botao (offsetMin.x) esta no mesmo referencial
                direita = botao.offsetMin.x - espacoAteBotao;
            }
            rt.offsetMax = new Vector2(direita, rt.offsetMax.y);
        }

        private void AoClicarReiniciar()
        {
            QuizManager.Instance?.Reiniciar();
        }
    }
}
