const form = document.querySelector("#search-form");
const input = document.querySelector("#search-input");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const savedStatusEl = document.querySelector("#saved-status");
const savedEl = document.querySelector("#saved-results");

function renderRecipe(recipe, actionLabel, onAction) {
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

  const button = document.createElement("button");
  button.type = "button";
  button.className = "recipe-action";
  button.textContent = actionLabel;
  button.addEventListener("click", () => onAction(button, recipe));

  body.append(title, origin, count, button);
  card.appendChild(body);
  return card;
}

async function saveRecipe(button, recipe) {
  button.disabled = true;
  try {
    const response = await fetch("/api/saved", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: recipe.id }),
    });
    if (!response.ok) throw new Error("save failed");
    button.textContent = "Saved";
    loadSaved();
  } catch (error) {
    button.disabled = false;
    statusEl.textContent = "Could not save that recipe. Try again.";
  }
}

async function removeRecipe(button, recipe) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/saved/${recipe.saved_id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("remove failed");
    loadSaved();
  } catch (error) {
    button.disabled = false;
    savedStatusEl.textContent = "Could not remove that recipe. Try again.";
  }
}

async function loadSaved() {
  try {
    const response = await fetch("/api/saved");
    const data = await response.json();
    savedEl.replaceChildren();

    if (data.results.length === 0) {
      savedStatusEl.textContent = "No saved recipes yet. Search for one and click Save.";
      return;
    }

    savedStatusEl.textContent = `${data.results.length} saved`;
    data.results.forEach((recipe) =>
      savedEl.appendChild(renderRecipe(recipe, "Remove", removeRecipe))
    );
  } catch (error) {
    savedStatusEl.textContent = "Could not load saved recipes.";
  }
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
    data.results.forEach((recipe) =>
      resultsEl.appendChild(renderRecipe(recipe, "Save", saveRecipe))
    );
  } catch (error) {
    statusEl.textContent = "Could not reach the server. Check your connection and try again.";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (query) search(query);
});

loadSaved();