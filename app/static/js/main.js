const form = document.querySelector("#search-form");
const input = document.querySelector("#search-input");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");

function renderRecipe(recipe) {
  const card = document.createElement("article");
  card.className = "recipe";

  if (recipe.image) {
    const img = document.createElement("img");
    img.src = recipe.image;
    img.alt = "";
    img.loading = "lazy";
    card.appendChild(img);
  }

  const body = document.createElement("div");
  body.className = "recipe-body";

  const title = document.createElement("h2");
  title.textContent = recipe.title;

  const origin = document.createElement("p");
  origin.className = "meta";
  origin.textContent = [recipe.area, recipe.category].filter(Boolean).join(", ");

  const count = document.createElement("p");
  count.className = "meta";
  count.textContent = `${recipe.ingredients.length} ingredients`;

  body.append(title, origin, count);
  card.appendChild(body);
  return card;
}

async function search(query) {
  statusEl.textContent = "Searching...";
  resultsEl.replaceChildren();

  try {
    const response = await fetch(`/api/recipes/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();

    if (!response.ok) {
      statusEl.textContent = data.error || "Something went wrong. Try again.";
      return;
    }
    if (data.results.length === 0) {
      statusEl.textContent = `No recipes found for "${query}". Try a broader term like "chicken".`;
      return;
    }

    statusEl.textContent = `${data.results.length} recipes for "${query}"`;
    data.results.forEach((recipe) => resultsEl.appendChild(renderRecipe(recipe)));
  } catch (error) {
    statusEl.textContent = "Could not reach the server. Check your connection and try again.";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (query) search(query);
});