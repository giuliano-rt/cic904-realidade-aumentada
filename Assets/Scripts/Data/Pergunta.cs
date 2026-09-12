using System;

namespace ARQuiz.Data
{
    /// <summary>
    /// Uma pergunta do quiz, carregada de Resources/perguntas.json.
    /// Os nomes dos campos precisam bater exatamente com as chaves do JSON,
    /// porque a JsonUtility da Unity faz o mapeamento por nome.
    /// </summary>
    [Serializable]
    public class Pergunta
    {
        /// <summary>Identificador que tambem e o nome do Image Target na Vuforia.</summary>
        public string id;

        /// <summary>Nome exibido na carta e no topo do painel (ex.: "Terra").</summary>
        public string titulo;

        /// <summary>Cor tematica da carta, em hexadecimal (ex.: "#3A7BD5").</summary>
        public string corHex;

        public string enunciado;
        public string[] alternativas;

        /// <summary>Indice da alternativa correta dentro do array acima.</summary>
        public int correta;

        /// <summary>Texto mostrado no feedback, depois de responder.</summary>
        public string explicacao;

        public bool EhValida()
        {
            return !string.IsNullOrEmpty(id)
                   && alternativas != null
                   && alternativas.Length > 0
                   && correta >= 0
                   && correta < alternativas.Length;
        }
    }

    /// <summary>
    /// Raiz do arquivo JSON. A JsonUtility nao desserializa um array solto,
    /// entao o arquivo precisa ter um objeto na raiz envolvendo a lista.
    /// </summary>
    [Serializable]
    public class BancoPerguntas
    {
        public string tema;
        public Pergunta[] perguntas;
    }
}
