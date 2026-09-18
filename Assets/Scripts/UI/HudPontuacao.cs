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

        private void Awake()
        {
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
            }
        }

        private void AoClicarReiniciar()
        {
            QuizManager.Instance?.Reiniciar();
        }
    }
}
