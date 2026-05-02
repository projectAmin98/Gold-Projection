let chartInstance;

function buildProjectionDataset(projectionTable) {
  if (!projectionTable?.length) {
    return [];
  }

  return projectionTable.map((row) => ({
    x: String(row.year),
    y: row.price_per_gram,
  }));
}

export function renderGoldChart({ historicalSeries, projectionTable, currency }) {
  const canvas = document.getElementById("goldChart");
  const context = canvas.getContext("2d");

  const historicalPoints = historicalSeries.map((point) => ({
    x: point.date,
    y: point.price_per_gram,
  }));

  const projectionPoints = buildProjectionDataset(projectionTable);

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new Chart(context, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Historical Trend",
          data: historicalPoints,
          borderColor: "#a86e0f",
          backgroundColor: "rgba(168, 110, 15, 0.14)",
          borderWidth: 3,
          pointRadius: 0,
          tension: 0.24,
          fill: true,
        },
        {
          label: "Future Projection",
          data: projectionPoints,
          borderColor: "#1f7a50",
          backgroundColor: "rgba(31, 122, 80, 0.12)",
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 5,
          tension: 0.18,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "nearest",
        intersect: false,
      },
      plugins: {
        legend: {
          labels: {
            usePointStyle: true,
            boxWidth: 10,
          },
        },
      },
      scales: {
        x: {
          type: "category",
          grid: {
            color: "rgba(89, 69, 37, 0.08)",
          },
        },
        y: {
          title: {
            display: true,
            text: `Price / gram (${currency})`,
          },
          grid: {
            color: "rgba(89, 69, 37, 0.08)",
          },
        },
      },
    },
  });
}
