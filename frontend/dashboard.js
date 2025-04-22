// dashboard.js - Estatísticas de predição
let charts = {};

document.addEventListener("DOMContentLoaded", async () => {
  await loadStatistics();
  setInterval(loadStatistics, 30000); // Atualiza a cada 30 segundos
});

async function loadStatistics() {
  try {
    // Atualiza a hora da última atualização
    document.getElementById("lastUpdate").textContent =
      new Date().toLocaleTimeString();

    // Carrega todos os dados em paralelo
    const [total, distribution, genderStats, ageStats, activityStats] =
      await Promise.all([
        fetchData("/total_predictions"),
        fetchData("/predictions/distribution"),
        fetchData("/predictions/gender-stats"),
        fetchData("/predictions/age-stats"),
        fetchData("/predictions/activity-stats"),
      ]);

    // Atualiza os gráficos
    renderChart(
      "predictionChart",
      "bar",
      {
        labels: Object.keys(distribution),
        datasets: [
          {
            label: "Distribuição Geral",
            data: Object.values(distribution),
            backgroundColor: getChartColors(Object.keys(distribution).length),
          },
        ],
      },
      {
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Quantidade" },
          },
          x: { title: { display: true, text: "Classificação" } },
        },
      }
    );

    renderChart(
      "genderChart",
      "bar",
      {
        labels: Object.keys(distribution),
        datasets: [
          {
            label: "Masculino",
            data: Object.keys(distribution).map(
              (k) => genderStats.Male?.[k] || 0
            ),
            backgroundColor: "rgba(54, 162, 235, 0.7)",
          },
          {
            label: "Feminino",
            data: Object.keys(distribution).map(
              (k) => genderStats.Female?.[k] || 0
            ),
            backgroundColor: "rgba(255, 99, 132, 0.7)",
          },
        ],
      },
      {
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Quantidade" },
          },
          x: { title: { display: true, text: "Classificação" } },
        },
      }
    );

    renderChart("ageChart", "line", {
      labels: ageStats.map((item) => item.age_range),
      datasets: [
        {
          label: "Distribuição por Idade",
          data: ageStats.map((item) => item.count),
          backgroundColor: "rgba(75, 192, 192, 0.1)",
          borderColor: "rgba(75, 192, 192, 1)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "Peso Médio (kg)",
          data: ageStats.map((item) => item.avg_weight),
          backgroundColor: "rgba(255, 99, 132, 0.6)",
          type: "line",
          yAxisID: "y1",
        },
      ],
    });

    renderChart(
      "activityChart",
      "radar",
      {
        labels: activityStats.map((item) => item.activity_level),
        datasets: [
          {
            label: "Média de Peso (kg)",
            data: activityStats.map((item) => item.avg_weight),
            backgroundColor: "rgba(255, 206, 86, 0.2)",
            borderColor: "rgba(255, 206, 86, 1)",
            pointBackgroundColor: "rgba(255, 206, 86, 1)",
          },
        ],
      },
      {
        scales: {
          r: { beginAtZero: true, suggestedMin: 40, suggestedMax: 100 },
        },
      }
    );

    // Atualiza o total de predições
    document.getElementById("totalPredictions").textContent =
      total.total_predictions;
  } catch (error) {
    console.error("Erro ao carregar estatísticas:", error);
  }
}

async function fetchData(endpoint) {
  const response = await fetch(`http://localhost:5000${endpoint}`);
  if (!response.ok) throw new Error(`Erro ao buscar ${endpoint}`);
  return await response.json();
}

function renderChart(canvasId, type, data, options) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  // Destroi o gráfico anterior se existir
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }

  charts[canvasId] = new Chart(ctx, {
    type: type,
    data: data,
    options: options,
  });
}

function getChartColors(count) {
  const palette = [
    "rgba(54, 162, 235, 0.7)",
    "rgba(255, 99, 132, 0.7)",
    "rgba(75, 192, 192, 0.7)",
    "rgba(255, 206, 86, 0.7)",
    "rgba(153, 102, 255, 0.7)",
    "rgba(255, 159, 64, 0.7)",
    "rgba(199, 199, 199, 0.7)",
  ];
  return palette.slice(0, count);
}
