using System;
using System.Collections.Generic;
using ARQuiz.Data;
using UnityEngine;

namespace ARQuiz.Core
{
    /// <summary>
    /// Cerebro do jogo: carrega o banco de perguntas, decide o que mostrar
    /// quando um marcador e detectado, valida as respostas e mantem a pontuacao.
    ///
    /// Toda a comunicacao com a interface acontece por eventos estaticos, o mesmo
    /// padrao usado na Aula 04 (UIButtonHandler). Assim o QuizManager nao precisa
    /// conhecer nenhum objeto de UI, e a UI nao precisa procurar o QuizManager.
    /// </summary>
    public class QuizManager : MonoBehaviour
    {
        public static QuizManager Instance { get; private set; }

        [Header("Dados")]
        [Tooltip("Arquivo dentro de Assets/Resources, sem a extensao .json")]
        [SerializeField] private string arquivoPerguntas = "perguntas";

        [Header("Pontuacao")]
        [SerializeField] private int pontosPorAcerto = 10;
        [SerializeField] private int pontosPorErro = 0;

        // --- Eventos consumidos pela interface -------------------------------
        /// <summary>Marcador reconhecido e a pergunta ainda nao foi respondida.</summary>
        public static event Action<Pergunta> AoAbrirPergunta;

        /// <summary>Marcador reconhecido, mas a pergunta ja foi respondida antes.</summary>
        public static event Action<Pergunta, bool> AoRevisitarPergunta;

        /// <summary>O marcador saiu de vista: a interface deve se esconder.</summary>
        public static event Action AoFecharPergunta;

        /// <summary>Resposta processada: (acertou, pergunta, indiceEscolhido).</summary>
        public static event Action<bool, Pergunta, int> AoResponder;

        /// <summary>Placar mudou: (pontos, acertos, respondidas, total).</summary>
        public static event Action<int, int, int, int> AoAtualizarPlacar;

        /// <summary>Todas as perguntas foram respondidas.</summary>
        public static event Action<int, int, int> AoConcluirJogo;

        // --- Estado interno ---------------------------------------------------
        private readonly Dictionary<string, Pergunta> _perguntas =
            new Dictionary<string, Pergunta>();

        /// <summary>id da pergunta -> acertou na primeira tentativa.</summary>
        private readonly Dictionary<string, bool> _respondidas =
            new Dictionary<string, bool>();

        private string _marcadorAtivo;

        public int Pontos { get; private set; }
        public int Acertos { get; private set; }
        public int Erros { get; private set; }
        public int Total => _perguntas.Count;
        public int Respondidas => _respondidas.Count;
        public string Tema { get; private set; }

        /// <summary>
        /// A partida so pode recomecar depois que todas as cartas forem respondidas.
        /// Sem essa regra, o jogador poderia errar uma pergunta, reiniciar e responder
        /// de novo valendo os pontos cheios.
        /// </summary>
        public bool PodeReiniciar => Total > 0 && Respondidas >= Total;

        // --- Ciclo de vida ----------------------------------------------------
        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            CarregarPerguntas();
        }

        private void Start()
        {
            NotificarPlacar();
        }

        private void OnDestroy()
        {
            if (Instance == this)
            {
                Instance = null;
            }
        }

        private void CarregarPerguntas()
        {
            TextAsset arquivo = Resources.Load<TextAsset>(arquivoPerguntas);
            if (arquivo == null)
            {
                Debug.LogError($"[QuizManager] Nao encontrei Assets/Resources/{arquivoPerguntas}.json");
                return;
            }

            BancoPerguntas banco = JsonUtility.FromJson<BancoPerguntas>(arquivo.text);
            if (banco == null || banco.perguntas == null)
            {
                Debug.LogError("[QuizManager] O JSON foi lido mas nao pode ser interpretado. " +
                               "Confira se a raiz do arquivo e um objeto com o campo 'perguntas'.");
                return;
            }

            Tema = banco.tema;
            foreach (Pergunta p in banco.perguntas)
            {
                if (!p.EhValida())
                {
                    Debug.LogWarning($"[QuizManager] Pergunta invalida ignorada: '{p?.id}'. " +
                                     "Verifique o indice do campo 'correta'.");
                    continue;
                }
                if (_perguntas.ContainsKey(p.id))
                {
                    Debug.LogWarning($"[QuizManager] Id duplicado no JSON: '{p.id}'. Mantive o primeiro.");
                    continue;
                }
                _perguntas.Add(p.id, p);
            }

            Debug.Log($"[QuizManager] Tema '{Tema}' com {_perguntas.Count} perguntas carregadas.");
        }

        // --- Chamado pelos marcadores de AR -----------------------------------
        /// <summary>A Vuforia comecou a rastrear o marcador com este id.</summary>
        public void MarcadorDetectado(string id)
        {
            if (!_perguntas.TryGetValue(id, out Pergunta pergunta))
            {
                Debug.LogWarning($"[QuizManager] Marcador '{id}' nao tem pergunta no JSON. " +
                                 "O nome do Image Target precisa ser igual ao campo 'id'.");
                return;
            }

            _marcadorAtivo = id;

            if (_respondidas.TryGetValue(id, out bool acertouAntes))
            {
                AoRevisitarPergunta?.Invoke(pergunta, acertouAntes);
            }
            else
            {
                AoAbrirPergunta?.Invoke(pergunta);
            }
        }

        /// <summary>A Vuforia perdeu o rastreamento do marcador com este id.</summary>
        public void MarcadorPerdido(string id)
        {
            // So fecha se quem saiu de vista for o marcador que esta na tela.
            // Sem essa checagem, virar a camera de uma carta para outra fecharia
            // a pergunta que acabou de abrir.
            if (_marcadorAtivo != id)
            {
                return;
            }

            _marcadorAtivo = null;
            AoFecharPergunta?.Invoke();
        }

        // --- Resposta do jogador ----------------------------------------------
        /// <summary>Processa a alternativa escolhida. Devolve true se acertou.</summary>
        public bool Responder(string id, int indiceEscolhido)
        {
            if (!_perguntas.TryGetValue(id, out Pergunta pergunta))
            {
                return false;
            }
            if (_respondidas.ContainsKey(id))
            {
                // Protege contra toque duplo e contra pontuar a mesma carta duas vezes.
                return _respondidas[id];
            }

            bool acertou = indiceEscolhido == pergunta.correta;
            _respondidas[id] = acertou;

            if (acertou)
            {
                Acertos++;
                Pontos += pontosPorAcerto;
            }
            else
            {
                Erros++;
                Pontos += pontosPorErro;
            }

            AoResponder?.Invoke(acertou, pergunta, indiceEscolhido);
            NotificarPlacar();

            if (Respondidas >= Total && Total > 0)
            {
                AoConcluirJogo?.Invoke(Pontos, Acertos, Total);
            }

            return acertou;
        }

        /// <summary>Comeca uma partida nova. So funciona ao fim da partida atual.</summary>
        public void Reiniciar()
        {
            // A regra fica aqui, e nao so na interface: mesmo que algum botao chame
            // este metodo no meio da partida, o placar nao e apagado.
            if (!PodeReiniciar)
            {
                Debug.Log($"[QuizManager] Reiniciar recusado: {Respondidas}/{Total} cartas respondidas.");
                return;
            }

            _respondidas.Clear();
            _marcadorAtivo = null;
            Pontos = 0;
            Acertos = 0;
            Erros = 0;
            AoFecharPergunta?.Invoke();
            NotificarPlacar();
        }

        private void NotificarPlacar()
        {
            AoAtualizarPlacar?.Invoke(Pontos, Acertos, Respondidas, Total);
        }
    }
}
