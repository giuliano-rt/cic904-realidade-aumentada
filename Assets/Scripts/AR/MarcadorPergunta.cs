// Este script depende da Vuforia Engine, que e distribuida como um
// .unitypackage baixado do portal do desenvolvedor e nao pode ser resolvida
// automaticamente. O guard abaixo deixa o projeto compilar antes dela existir.
//
// Depois de importar a Vuforia, ative o simbolo VUFORIA_PRESENT em
// Edit -> Project Settings -> Player -> Other Settings -> Scripting Define Symbols.
#if VUFORIA_PRESENT

using System;
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
    ///
    /// Tres regras decidem o que aparece na tela:
    ///
    /// 1. So TRACKED conta como "estou vendo a carta". EXTENDED_TRACKED significa
    ///    que a Vuforia perdeu a carta de vista e esta estimando onde ela estaria;
    ///    na webcam, sem sensores de movimento, isso e um palpite, e trata-lo como
    ///    visivel deixava os planetas ja vistos flutuando na tela como fantasmas.
    ///
    /// 2. Tolerancia: a carta so e dada como perdida depois de alguns decimos de
    ///    segundo fora de vista. O rastreamento oscila com o tremor da mao, e sem
    ///    isso o painel da pergunta piscaria enquanto a pessoa le.
    ///
    /// 3. Uma carta por vez: quando uma carta assume, a anterior se esconde e fica
    ///    suprimida ate sair de vista de verdade. As cartas compartilham o layout, e
    ///    a Vuforia as vezes continua rastreando a carta antiga sobre a nova; sem a
    ///    supressao, a antiga roubaria a vez de volta.
    /// </summary>
    [RequireComponent(typeof(ObserverBehaviour))]
    public class MarcadorPergunta : MonoBehaviour
    {
        [Tooltip("Deixe vazio para usar o nome do Image Target da Vuforia.")]
        [SerializeField] private string idPergunta;

        [Tooltip("Objeto 3D mostrado sobre a carta. Se vazio, usa todos os filhos.")]
        [SerializeField] private GameObject conteudoVirtual;

        [Tooltip("Tempo fora de vista antes de a carta ser dada como perdida.")]
        [SerializeField] private float segundosTolerancia = 0.6f;

        /// <summary>Uma carta acabou de assumir: as outras devem se esconder.</summary>
        private static event Action<MarcadorPergunta> AoAssumir;

        private ObserverBehaviour _observer;
        private bool _vendoAgora;          // a Vuforia diz TRACKED neste momento
        private bool _ativo;               // planeta na tela e pergunta aberta
        private bool _suprimido;           // outra carta assumiu enquanto esta era vista
        private float _foraDeVistaDesde = -1f;

        public string Id => string.IsNullOrWhiteSpace(idPergunta)
            ? (_observer != null ? _observer.TargetName : string.Empty)
            : idPergunta.Trim();

        // --- Ciclo de vida ----------------------------------------------------
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
            AoAssumir += AoOutroAssumir;
        }

        private void OnDisable()
        {
            if (_observer != null)
            {
                _observer.OnTargetStatusChanged -= AoMudarStatus;
            }
            AoAssumir -= AoOutroAssumir;

            // Se o objeto for desativado enquanto a carta estava na tela, a UI
            // ficaria presa. Fecha explicitamente.
            if (_ativo)
            {
                Desativar(avisarQuiz: true);
            }
        }

        private void Update()
        {
            if (_ativo && !_vendoAgora && _foraDeVistaDesde >= 0f
                && Time.time - _foraDeVistaDesde >= segundosTolerancia)
            {
                Debug.Log($"[Marcador] {Id} perdida de vista");
                Desativar(avisarQuiz: true);
            }
        }

        // --- Reacao ao rastreamento -------------------------------------------
        private void AoMudarStatus(ObserverBehaviour observer, TargetStatus status)
        {
            _vendoAgora = status.Status == Status.TRACKED;

            if (!_vendoAgora)
            {
                // Saiu de vista de verdade: acaba a supressao, e se estava na tela,
                // comeca a contar a tolerancia (o Update decide se some).
                _suprimido = false;
                if (_ativo && _foraDeVistaDesde < 0f)
                {
                    _foraDeVistaDesde = Time.time;
                }
                return;
            }

            _foraDeVistaDesde = -1f;          // voltou a tempo: nada acontece

            if (!_ativo && !_suprimido)
            {
                Assumir();
            }
        }

        private void Assumir()
        {
            _ativo = true;
            AoAssumir?.Invoke(this);          // as outras cartas se escondem
            MostrarConteudo(true);
            Debug.Log($"[Marcador] {Id} assumiu");

            if (QuizManager.Instance == null)
            {
                Debug.LogWarning("[MarcadorPergunta] Nenhum QuizManager na cena. " +
                                 "Crie um GameObject vazio chamado 'QuizManager' com o script.");
                return;
            }
            QuizManager.Instance.MarcadorDetectado(Id);
        }

        private void AoOutroAssumir(MarcadorPergunta outro)
        {
            if (outro == this)
            {
                return;
            }

            // Se a Vuforia ainda diz que esta carta esta visivel, ela fica suprimida
            // ate sair de vista de verdade -- e nao pode retomar a vez antes disso.
            _suprimido = _vendoAgora;

            if (_ativo)
            {
                Debug.Log($"[Marcador] {Id} escondida: {outro.Id} assumiu");
                // Nao avisa o QuizManager: ele ja trocou para a carta nova.
                Desativar(avisarQuiz: false);
            }
        }

        private void Desativar(bool avisarQuiz)
        {
            _ativo = false;
            _foraDeVistaDesde = -1f;
            MostrarConteudo(false);

            if (avisarQuiz)
            {
                QuizManager.Instance?.MarcadorPerdido(Id);
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

#endif // VUFORIA_PRESENT
