using System.Collections;
using ARQuiz.Core;
using ARQuiz.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ARQuiz.UI
{
    /// <summary>
    /// Faixa de retorno que aparece logo apos o jogador responder: diz se acertou
    /// ou errou e mostra a explicacao da pergunta. Some sozinha depois de alguns
    /// segundos, sem precisar de nenhum botao.
    /// </summary>
    public class PainelFeedback : MonoBehaviour
    {
        [Header("Estrutura")]
        [SerializeField] private CanvasGroup painel;
        [SerializeField] private Image fundo;
        [SerializeField] private TMP_Text textoResultado;
        [SerializeField] private TMP_Text textoExplicacao;

        [Header("Aparencia")]
        [SerializeField] private Color corAcerto = new Color(0.20f, 0.71f, 0.39f);
        [SerializeField] private Color corErro = new Color(0.86f, 0.27f, 0.27f);
        [SerializeField] private float segundosVisivel = 4.5f;
        [SerializeField] private float segundosFade = 0.35f;

        [Header("Som (opcional)")]
        [SerializeField] private AudioSource audioSource;
        [SerializeField] private AudioClip somAcerto;
        [SerializeField] private AudioClip somErro;

        private Coroutine _rotina;

        private void Awake()
        {
            DefinirAlfa(0f);
        }

        private void OnEnable()
        {
            QuizManager.AoResponder += Mostrar;
            QuizManager.AoConcluirJogo += MostrarConclusao;
        }

        private void OnDisable()
        {
            QuizManager.AoResponder -= Mostrar;
            QuizManager.AoConcluirJogo -= MostrarConclusao;
        }

        private void Mostrar(bool acertou, Pergunta pergunta, int indiceEscolhido)
        {
            if (fundo != null)
            {
                fundo.color = acertou ? corAcerto : corErro;
            }

            if (textoResultado != null)
            {
                textoResultado.text = acertou
                    ? "Resposta certa!"
                    : $"Resposta errada — a correta era: {pergunta.alternativas[pergunta.correta]}";
            }

            if (textoExplicacao != null)
            {
                textoExplicacao.text = pergunta.explicacao;
            }

            Tocar(acertou ? somAcerto : somErro);
            Reiniciar(segundosVisivel);
        }

        private void MostrarConclusao(int pontos, int acertos, int total)
        {
            if (fundo != null)
            {
                fundo.color = corAcerto;
            }
            if (textoResultado != null)
            {
                textoResultado.text = "Jogo concluído!";
            }
            if (textoExplicacao != null)
            {
                textoExplicacao.text =
                    $"Você acertou {acertos} de {total} perguntas e fez {pontos} pontos.";
            }

            // Fica mais tempo na tela: e a tela final da demonstracao.
            Reiniciar(segundosVisivel * 2f);
        }

        private void Tocar(AudioClip clipe)
        {
            if (audioSource != null && clipe != null)
            {
                audioSource.PlayOneShot(clipe);
            }
        }

        private void Reiniciar(float duracao)
        {
            if (_rotina != null)
            {
                StopCoroutine(_rotina);
            }
            _rotina = StartCoroutine(Exibir(duracao));
        }

        private IEnumerator Exibir(float duracao)
        {
            yield return Fade(1f);
            yield return new WaitForSeconds(duracao);
            yield return Fade(0f);
            _rotina = null;
        }

        private IEnumerator Fade(float alvo)
        {
            float inicio = painel != null ? painel.alpha : 0f;
            float t = 0f;

            while (t < segundosFade)
            {
                t += Time.deltaTime;
                DefinirAlfa(Mathf.Lerp(inicio, alvo, t / segundosFade));
                yield return null;
            }
            DefinirAlfa(alvo);
        }

        private void DefinirAlfa(float valor)
        {
            if (painel == null)
            {
                return;
            }
            painel.alpha = valor;
            painel.blocksRaycasts = false;   // a faixa nunca bloqueia os botoes
            painel.interactable = false;
        }
    }
}
