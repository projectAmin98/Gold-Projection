const formatCurrency = (value, currency) =>
  new Intl.NumberFormat("en-MY", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

const formatNumber = (value) =>
  new Intl.NumberFormat("en-MY", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

function renderCalculatorResults({ entryPrice, grams, budget, marketPrice, currency }) {
  const totalCost = entryPrice * grams;
  const gramsFromBudget = entryPrice > 0 ? budget / entryPrice : 0;
  const marketValue = grams * marketPrice;
  const difference = marketValue - totalCost;
  const differenceClass = difference >= 0 ? "profit-positive" : "profit-negative";

  document.getElementById("calculatorResults").innerHTML = `
    <article class="card">
      <span>Total purchase value</span>
      <strong>${formatCurrency(totalCost, currency)}</strong>
    </article>
    <article class="card">
      <span>Grams from budget</span>
      <strong>${formatNumber(gramsFromBudget)} g</strong>
    </article>
    <article class="card">
      <span>Value at live market</span>
      <strong>${formatCurrency(marketValue, currency)}</strong>
    </article>
    <article class="card">
      <span>Entry vs live difference</span>
      <strong class="${differenceClass}">${formatCurrency(difference, currency)}</strong>
    </article>
  `;
}

export function setupCalculator(getState) {
  const inputIds = ["calcPricePerGram", "calcGrams", "calcBudget"];

  const update = () => {
    const state = getState();
    renderCalculatorResults({
      entryPrice: Number(document.getElementById("calcPricePerGram").value) || 0,
      grams: Number(document.getElementById("calcGrams").value) || 0,
      budget: Number(document.getElementById("calcBudget").value) || 0,
      marketPrice: Number(state.latestPricePerGram || 0),
      currency: state.currency || "MYR",
    });
  };

  inputIds.forEach((id) => {
    document.getElementById(id).addEventListener("input", update);
  });

  update();
  return update;
}

export function syncCalculatorMarket({ latestPricePerGram, currency }) {
  const priceInput = document.getElementById("calcPricePerGram");
  const label = document.getElementById("calculatorMarketLabel");

  if (!priceInput.dataset.touched && !priceInput.value) {
    priceInput.value = Number(latestPricePerGram || 0).toFixed(2);
  }

  label.textContent = `Live ${currency} ${Number(latestPricePerGram || 0).toFixed(2)}/g`;
}

export function markCalculatorPriceTouched() {
  document.getElementById("calcPricePerGram").dataset.touched = "true";
}
