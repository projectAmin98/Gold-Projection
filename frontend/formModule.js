import { fetchForecast, fetchGoldMarketData, fetchMalaysiaLivePrice } from "./apiService.js";
import {
  markCalculatorPriceTouched,
  setupCalculator,
  syncCalculatorMarket,
} from "./calculatorModule.js";
import { renderGoldChart } from "./chartModule.js";

const state = {
  mode: "ai",
  latestMarket: null,
  benchmarkMarket: null,
  calculatorUpdate: null,
  chartRange: "1mo",
  chartInterval: "1d",
  latestProjectionTable: [],
  malaysiaMarket: null,
};

const formatCurrency = (value, currency) =>
  new Intl.NumberFormat("en-MY", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".toggle").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });

  const manualGroup = document.getElementById("manualPriceGroup");
  const yearsGroup = document.getElementById("projectionYearsGroup");
  const forecastModeLabel = document.getElementById("forecastModeLabel");
  manualGroup.classList.toggle("hidden", mode !== "manual");
  yearsGroup.classList.toggle("hidden", mode !== "ai");
  forecastModeLabel.textContent = mode === "manual" ? "Manual Future Price" : "AI Projection";
}

function parseProjectionYears(value) {
  const years = value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0);

  return [...new Set(years)].sort((left, right) => left - right);
}

function renderSummaryCards(summary, currency, latestPrice) {
  const realisticSellPrice = state.malaysiaMarket?.realistic_sell_price_per_gram || latestPrice;
  const cards = [
    { label: "Initial Investment", value: formatCurrency(summary.initial_investment, currency) },
    { label: "Realistic Sell Value", value: formatCurrency(summary.current_value, currency) },
    { label: "Profit / Loss", value: formatCurrency(summary.profit_loss, currency), profit: true },
    { label: "Spot Price / Gram", value: formatCurrency(latestPrice, currency) },
    { label: "Dealer Buy / Gram", value: formatCurrency(realisticSellPrice, currency) },
  ];

  document.getElementById("summaryCards").innerHTML = cards
    .map((card) => {
      const profitClass = card.profit
        ? Number(summary.profit_loss) >= 0
          ? "profit-positive"
          : "profit-negative"
        : "";
      return `
        <article class="card">
          <span>${card.label}</span>
          <strong class="${profitClass}">${card.value}</strong>
        </article>
      `;
    })
    .join("");
}

function renderProjectionTable(response) {
  const currency = response.market.currency;
  const wrapper = document.getElementById("projectionTableWrapper");

  if (response.manual_future_value) {
    const manual = response.manual_future_value;
    wrapper.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Mode</th>
            <th>Future Price / Gram</th>
            <th>Total Value</th>
            <th>Profit</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Manual</td>
            <td>${formatCurrency(manual.future_price_per_gram, currency)}</td>
            <td>${formatCurrency(manual.total_value, currency)}</td>
            <td>${formatCurrency(manual.profit, currency)}</td>
          </tr>
        </tbody>
      </table>
    `;
    return;
  }

  const rows = response.projection_table
    .map(
      (row) => `
        <tr>
          <td>${row.year}</td>
          <td>${formatCurrency(row.price_per_gram, currency)}</td>
          <td>${formatCurrency(row.total_value, currency)}</td>
          <td>${formatCurrency(row.profit, currency)}</td>
        </tr>
      `,
    )
    .join("");

  wrapper.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Year</th>
          <th>Price / Gram</th>
          <th>Total Value</th>
          <th>Profit</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderForecastMeta(meta) {
  const entries = [
    ["Model", meta.model || "-"],
    ["MA (30)", meta.moving_average_30 || "-"],
    ["MA (90)", meta.moving_average_90 || "-"],
    ["CAGR", meta.cagr ? `${meta.cagr}%` : "-"],
    ["Annualized Volatility", meta.annualized_volatility ? `${meta.annualized_volatility}%` : "-"],
  ];

  document.getElementById("forecastMeta").innerHTML = entries
    .map(
      ([label, value]) => `
        <div class="meta-item">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

function renderScenarioSummary(scenarios, currency) {
  const container = document.getElementById("scenarioSummary");
  const blocks = Object.entries(scenarios || {}).map(([name, rows]) => {
    const horizonRows = rows
      .map(
        (row) => `
          <div class="meta-item">
            <span>${row.year}</span>
            <strong>${formatCurrency(row.low_price_per_gram, currency)} - ${formatCurrency(row.high_price_per_gram, currency)}</strong>
          </div>
        `,
      )
      .join("");

    return `
      <section class="scenario-block">
        <span>${name.toUpperCase()}</span>
        <strong>Projected price range / gram</strong>
        <div class="meta-list">${horizonRows}</div>
      </section>
    `;
  });

  container.innerHTML = blocks.length ? blocks.join("") : "<p>No scenario data in manual mode.</p>";
}

function renderMarketTimestamp(updatedAt) {
  document.getElementById("marketTimestamp").textContent = updatedAt || "Unavailable";
}

function findHighestPoint(series, days) {
  if (!series?.length) {
    return null;
  }

  const latestDate = new Date(series[series.length - 1].date);
  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - days);

  const windowSeries = series.filter((point) => new Date(point.date) >= cutoff);
  const source = windowSeries.length ? windowSeries : series;

  return source.reduce((highest, point) => (
    !highest || point.price_per_gram > highest.price_per_gram ? point : highest
  ), null);
}

function renderMarketHighlights(market) {
  if (!market?.historical_series?.length) {
    return;
  }

  const currency = market.currency;
  const currentPoint = state.malaysiaMarket && currency === "MYR"
    ? {
        price_per_gram: state.malaysiaMarket.analytics_price_per_gram,
        date: state.malaysiaMarket.analytics_source.updated_at || market.historical_series[market.historical_series.length - 1].date,
      }
    : market.historical_series[market.historical_series.length - 1];
  const monthHigh = findHighestPoint(market.historical_series, 30);
  const yearHigh = findHighestPoint(market.historical_series, 365);

  const cards = [
    {
      label: "Current Price",
      value: `${formatCurrency(currentPoint.price_per_gram, currency)}/g`,
      meta: currentPoint.date,
    },
    {
      label: "1-Month High",
      value: `${formatCurrency(monthHigh?.price_per_gram, currency)}/g`,
      meta: monthHigh?.date || "-",
    },
    {
      label: "1-Year High",
      value: `${formatCurrency(yearHigh?.price_per_gram, currency)}/g`,
      meta: yearHigh?.date || "-",
    },
  ];

  document.getElementById("marketHighlightsCards").innerHTML = cards
    .map(
      (card) => `
        <article class="market-card">
          <span>${card.label}</span>
          <strong>${card.value}</strong>
          <p>${card.meta}</p>
        </article>
      `,
    )
    .join("");
}

function renderMalaysiaMarket(data) {
  state.malaysiaMarket = data;
  document.getElementById("malaysiaMarketUpdated").textContent = data.updated_at || "Live";
  document.getElementById("malaysiaMarketSource").href = data.analytics_source.url;
  document.getElementById("malaysiaMarketSource").textContent = data.analytics_source.name;
  document.getElementById("malaysiaDealerSource").href = data.realistic_sell_source.url;
  document.getElementById("malaysiaDealerSource").textContent = data.realistic_sell_source.name;

  const cards = [
    {
      label: "Analytics Spot (999)",
      spot: data.analytics_price_per_gram,
      note: "Used for model and forecast logic",
    },
    {
      label: "Dealer Buyback (999)",
      spot: data.realistic_sell_price_per_gram,
      note: "Used for realistic selling value",
    },
  ];

  document.getElementById("malaysiaMarketCards").innerHTML = cards
    .map(
      (card) => `
        <article class="market-card">
          <span>${card.label}</span>
          <strong>${card.spot ? `${formatCurrency(card.spot, "MYR")}/g` : "See SMS Deen app"}</strong>
          <p>${card.note}</p>
        </article>
      `,
    )
    .join("");
}

function refreshCalculator() {
  if (!state.latestMarket) {
    return;
  }

  syncCalculatorMarket({
    latestPricePerGram: state.latestMarket.latest_price_per_gram,
    currency: state.latestMarket.currency,
  });

  if (state.calculatorUpdate) {
    state.calculatorUpdate();
  }
}

async function preloadMarketData() {
  const currency = document.getElementById("displayCurrency").value;
  const [market, benchmarkMarket] = await Promise.all([
    fetchGoldMarketData(currency, state.chartRange, state.chartInterval),
    fetchGoldMarketData(currency, "1y", "1d"),
  ]);
  state.latestMarket = market;
  state.benchmarkMarket = benchmarkMarket;
  renderMarketTimestamp(market.updated_at);
  renderMarketHighlights(benchmarkMarket);
  refreshCalculator();
  renderGoldChart({
    historicalSeries: market.historical_series,
    projectionTable: state.latestProjectionTable,
    currency: market.currency,
  });
}

async function preloadMalaysiaMarket() {
  const data = await fetchMalaysiaLivePrice();
  renderMalaysiaMarket(data);
}

async function handleSubmit(event) {
  event.preventDefault();

  const currency = document.getElementById("displayCurrency").value;
  const projectionYears = parseProjectionYears(document.getElementById("projectionYears").value);
  const payload = {
    price_per_gram: Number(document.getElementById("pricePerGram").value),
    grams: Number(document.getElementById("grams").value),
    purchase_date: document.getElementById("purchaseDate").value || null,
    future_price_per_gram: state.mode === "manual"
      ? Number(document.getElementById("futurePricePerGram").value)
      : null,
    projection_years: projectionYears,
    display_currency: currency,
    use_ai_projection: state.mode === "ai",
  };

  if (state.mode === "manual" && !payload.future_price_per_gram) {
    window.alert("Please enter a manual future price per gram.");
    return;
  }

  if (state.mode === "ai" && !projectionYears.length) {
    window.alert("Please enter at least one projection year, like 1,3,5.");
    return;
  }

  const response = await fetchForecast(payload);
  renderMarketTimestamp(response.market.updated_at);
  if (response.market.pricing_reference) {
    renderMalaysiaMarket(response.market.pricing_reference);
  }
  renderSummaryCards(
    response.summary,
    response.market.currency,
    response.market.analytics_price_per_gram,
  );
  renderProjectionTable(response);
  renderForecastMeta(response.forecast_meta);
  renderScenarioSummary(response.scenario_summary, response.market.currency);
  renderGoldChart({
    historicalSeries: state.latestMarket?.historical_series || response.historical_series,
    projectionTable: response.projection_table,
    currency: response.market.currency,
  });
  state.latestMarket = {
    latest_price_per_gram: response.market.latest_price_per_gram,
    currency: response.market.currency,
    historical_series: state.latestMarket?.historical_series || response.historical_series,
  };
  if (state.benchmarkMarket) {
    renderMarketHighlights(state.benchmarkMarket);
  }
  state.latestProjectionTable = response.projection_table;
  refreshCalculator();
}

function bindEvents() {
  document.querySelectorAll(".toggle").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  document.getElementById("displayCurrency").addEventListener("change", async () => {
    await preloadMarketData();
  });

  document.querySelectorAll(".chart-range-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelectorAll(".chart-range-btn").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
      state.chartRange = button.dataset.range;
      state.chartInterval = button.dataset.interval;
      try {
        await preloadMarketData();
      } catch (error) {
        window.alert(error.message || "Unable to switch chart range.");
      }
    });
  });

  document.getElementById("calcPricePerGram").addEventListener("input", () => {
    markCalculatorPriceTouched();
  });

  document.getElementById("projectionForm").addEventListener("submit", async (event) => {
    try {
      await handleSubmit(event);
    } catch (error) {
      window.alert(error.message || "Unable to generate projection.");
    }
  });
}

async function init() {
  setMode("ai");
  state.calculatorUpdate = setupCalculator(() => ({
    latestPricePerGram: state.latestMarket?.latest_price_per_gram,
    currency: state.latestMarket?.currency || document.getElementById("displayCurrency").value,
  }));
  bindEvents();
  try {
    await Promise.all([preloadMarketData(), preloadMalaysiaMarket()]);
  } catch (error) {
    renderMarketTimestamp("Market feed unavailable");
    window.alert(error.message || "Unable to load live gold market data.");
  }
}

init();
