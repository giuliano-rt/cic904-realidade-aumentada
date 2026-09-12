using UnityEngine;

namespace ARQuiz.AR
{
    /// <summary>
    /// Gira o objeto 3D sobre a carta e faz um leve movimento de flutuacao.
    /// Serve para dar vida ao planeta que aparece em cima do marcador.
    /// </summary>
    public class GiroObjeto : MonoBehaviour
    {
        [Header("Rotacao")]
        [SerializeField] private Vector3 eixo = Vector3.up;
        [SerializeField] private float grausPorSegundo = 25f;

        [Header("Flutuacao")]
        [SerializeField] private bool flutuar = true;
        [SerializeField] private float amplitude = 0.04f;
        [SerializeField] private float velocidade = 1.2f;

        private Vector3 _posicaoInicial;
        private float _defasagem;

        private void Awake()
        {
            _posicaoInicial = transform.localPosition;

            // Defasagem baseada na posicao no mundo: dois planetas visiveis ao
            // mesmo tempo nao flutuam em sincronia, o que fica mais natural.
            _defasagem = Mathf.Abs(transform.position.x + transform.position.z) * 2f;
        }

        private void OnEnable()
        {
            transform.localPosition = _posicaoInicial;
        }

        private void Update()
        {
            transform.Rotate(eixo.normalized, grausPorSegundo * Time.deltaTime, Space.Self);

            if (!flutuar)
            {
                return;
            }

            float deslocamento = Mathf.Sin((Time.time + _defasagem) * velocidade) * amplitude;
            transform.localPosition = _posicaoInicial + Vector3.up * deslocamento;
        }
    }
}
