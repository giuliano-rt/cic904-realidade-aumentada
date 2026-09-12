using ARQuiz.Core;
using UnityEngine;
using Vuforia;

namespace ARQuiz.AR
{
    /// <summary>
    /// Vai em cada Image Target da cena. Escuta o rastreamento da Vuforia e avisa
    /// o QuizManager quando a carta entra ou sai do campo de visao da camera.
    ///
    /// O id da pergunta e, por padrao, o proprio nome do target na Vuforia, entao
    /// basta que o nome do Image Target seja igual ao campo "id" do perguntas.json
    /// (ex.: SOLAR-03). Isso evita ter que preencher o campo na mao em cada carta.
    /// </summary>
    [RequireComponent(typeof(ObserverBehaviour))]
    public class MarcadorPergunta : MonoBehaviour
    {
        [Tooltip("Deixe vazio para usar o nome do Image Target da Vuforia.")]
        [SerializeField] private string idPergunta;

        [Tooltip("Objeto 3D mostrado sobre a carta. Se vazio, usa todos os filhos.")]
        [SerializeField] private GameObject conteudoVirtual;

        private ObserverBehaviour _observer;
        private bool _rastreando;

        public string Id => string.IsNullOrWhiteSpace(idPergunta)
            ? (_observer != null ? _observer.TargetName : string.Empty)
            : idPergunta.Trim();

        private void Awake()
        {
            _observer = GetComponent<ObserverBehaviour>();
            MostrarConteudo(false);
        }

        private void OnEnable()
        {
            if (_observer != null)
            {
                _observer.OnTargetStatusChanged += AoMudarStatus;
            }
        }

        private void OnDisable()
        {
            if (_observer != null)
            {
                _observer.OnTargetStatusChanged -= AoMudarStatus;
            }

            // Se o objeto for desativado enquanto a carta estava visivel, a UI
            // ficaria presa na tela. Fecha explicitamente.
            if (_rastreando)
            {
                _rastreando = false;
                QuizManager.Instance?.MarcadorPerdido(Id);
            }
        }

        private void AoMudarStatus(ObserverBehaviour observer, TargetStatus status)
        {
            bool visivel = status.Status == Status.TRACKED
                           || status.Status == Status.EXTENDED_TRACKED;

            if (visivel == _rastreando)
            {
                return;   // nada mudou de fato
            }

            _rastreando = visivel;
            MostrarConteudo(visivel);

            if (QuizManager.Instance == null)
            {
                Debug.LogWarning("[MarcadorPergunta] Nenhum QuizManager na cena. " +
                                 "Crie um GameObject vazio chamado 'QuizManager' com o script.");
                return;
            }

            if (visivel)
            {
                QuizManager.Instance.MarcadorDetectado(Id);
            }
            else
            {
                QuizManager.Instance.MarcadorPerdido(Id);
            }
        }

        private void MostrarConteudo(bool visivel)
        {
            if (conteudoVirtual != null)
            {
                conteudoVirtual.SetActive(visivel);
                return;
            }

            // Sem um objeto definido no Inspector, liga/desliga todos os filhos.
            for (int i = 0; i < transform.childCount; i++)
            {
                transform.GetChild(i).gameObject.SetActive(visivel);
            }
        }
    }
}
