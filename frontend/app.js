document
  .getElementById("predictionForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    // Coleta todos os valores do formulário
    const formData = {
      Age: parseInt(document.getElementById("age").value),
      Gender: document.getElementById("gender").value,
      Height: parseFloat(document.getElementById("height").value),
      Weight: parseFloat(document.getElementById("weight").value),
      FAF: parseInt(document.getElementById("faf").value),
      SMOKE: document.getElementById("smoke").value,
      FAVC: document.getElementById("favc").value,
      family_history_with_overweight:
        document.getElementById("family_history").value,
      CAEC: document.getElementById("caec").value,
      CALC: document.getElementById("calc").value,
      MTRANS: document.getElementById("mtrans").value,
    };

    // Validação avançada
    try {
      // Validação de campos numéricos
      if (formData.Age < 14 || formData.Age > 100)
        throw new Error("Idade deve ser entre 14 e 100 anos");
      if (formData.Height < 1.4 || formData.Height > 2.2)
        throw new Error("Altura inválida");
      if (formData.Weight < 40 || formData.Weight > 200)
        throw new Error("Peso inválido");
      if (formData.FAF < 0 || formData.FAF > 3)
        throw new Error("Frequência de atividade física deve ser 0-3");

      // Mostrar loading
      const submitBtn = e.target.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';

      const response = await fetch("http://localhost:5000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Erro na resposta do servidor");
      }

      const result = await response.json();
      console.log(result);

      // Exibir resultados detalhados
      displayPredictionResult(result, formData);
    } catch (error) {
      console.error("Erro:", error);
      showError(error.message);
    } finally {
      const submitBtn = e.target.querySelector('button[type="submit"]');
      submitBtn.disabled = false;
      submitBtn.textContent = "Prever";
    }
  });

// Função para carregar o total de predições
async function loadTotalPredictions() {
    try {
      // Requisição GET para obter o total de predições
      const response = await fetch("http://localhost:5000/total_predictions");
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      // Extrair o dado JSON da resposta
      const data = await response.json();
      console.log("Dados recebidos:", data.total_predictions); // Para debug
  
      // Verifica se a propriedade existe na resposta
      if (data.total_predictions !== undefined) {
        // Atualizar o valor no HTML
        document.getElementById("totalPredictions").textContent = 
          data.total_predictions.toLocaleString(); // Formatação numérica
      } else {
        throw new Error("Propriedade 'total_predictions' não encontrada na resposta");
      }
    } catch (error) {
      console.error("Erro ao carregar total de predições:", error);
      document.getElementById("totalPredictions").textContent =
        "Erro ao carregar dados";
      // Opcional: exibir mensagem de erro para o usuário
      alert("Não foi possível carregar o total de predições. Tente novamente mais tarde.");
    }
  }
  

loadTotalPredictions()

// Chame a função quando a página for carregada
window.onload = loadTotalPredictions;

function displayPredictionResult(result, formData) {
  const resultDiv = document.getElementById("result");
  const detailsList = document.getElementById("predictionList");

  // Mapeamento de tradução para os resultados
  const predictionLabels = {
    Insufficient_Weight: "Peso Insuficiente",
    Normal_Weight: "Peso Normal",
    Overweight_Level_I: "Sobrepeso Nível I",
    Overweight_Level_II: "Sobrepeso Nível II",
    Obesity_Type_I: "Obesidade Tipo I",
    Obesity_Type_II: "Obesidade Tipo II",
    Obesity_Type_III: "Obesidade Tipo III",
  };

  // Exibir resultado principal
  resultDiv.innerHTML = `
        <h4>Resultado: <strong>${
          predictionLabels[result.prediction] || result.prediction
        }</strong></h4>
        <p class="mb-0">ID da Predição: ${result.prediction_id}</p>
    `;
  resultDiv.className = "alert alert-success";
  resultDiv.style.display = "block";

  // Exibir detalhes
  detailsList.innerHTML = `
        <li class="list-group-item"><strong>Idade:</strong> ${
          formData.Age
        } anos</li>
        <li class="list-group-item"><strong>Gênero:</strong> ${
          formData.Gender === "Male" ? "Masculino" : "Feminino"
        }</li>
        <li class="list-group-item"><strong>IMC:</strong> ${(
          formData.Weight /
          (formData.Height * formData.Height)
        ).toFixed(1)}</li>
        <li class="list-group-item"><strong>Atividade Física:</strong> ${
          ["Nenhuma", "1-2 dias/semana", "3-4 dias/semana", "5+ dias/semana"][
            formData.FAF
          ]
        }</li>
        <li class="list-group-item"><strong>Fumante:</strong> ${
          formData.SMOKE === "yes" ? "Sim" : "Não"
        }</li>
    `;
  document.getElementById("predictionDetails").style.display = "block";
}

function showError(message) {
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = `<strong>Erro:</strong> ${message}`;
  resultDiv.className = "alert alert-danger";
  resultDiv.style.display = "block";
  document.getElementById("predictionDetails").style.display = "none";
}
