const API_BASE = "/api";

function getToken() {
  return localStorage.getItem("halterai_token") || null;
}

function setToken(token) {
  localStorage.setItem("halterai_token", token);
}

function clearToken() {
  localStorage.removeItem("halterai_token");
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function showFeedback(message, type = "info", containerId = "auth-feedback") {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.textContent = message;
  container.style.color = type === "error" ? "#fda4af" : "#a5f3fc";
}

function navigateTo(url) {
  window.location.href = url;
}

async function requestJson(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await response.text();
  let payload = null;
  try { payload = JSON.parse(text); } catch (error) { payload = null; }
  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      navigateTo("index.html");
    }
    throw new Error(payload?.detail || payload?.message || response.statusText || text);
  }
  return payload;
}

// Auth page
if (document.body.contains(document.querySelector("#login-button"))) {
  if (getToken()) {
    navigateTo("dashboard.html");
  }
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((tab) => tab.classList.remove("active"));
      document.querySelectorAll(".auth-panel").forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.target).classList.add("active");
      showFeedback("");
    });
  });

  document.getElementById("login-button").addEventListener("click", async () => {
    const login = document.getElementById("login-username").value.trim();
    const senha = document.getElementById("login-password").value.trim();
    if (!login || !senha) {
      return showFeedback("Preencha todos os campos.", "error");
    }
    try {
      const response = await requestJson("/auth/login", { method: "POST", body: JSON.stringify({ login, senha }) });
      setToken(response.token);
      navigateTo("dashboard.html");
    } catch (error) {
      showFeedback(error.message, "error");
    }
  });

  document.getElementById("register-button").addEventListener("click", async () => {
    const username = document.getElementById("register-username").value.trim();
    const email = document.getElementById("register-email").value.trim();
    const senha = document.getElementById("register-password").value.trim();
    const confirm = document.getElementById("register-password-confirm").value.trim();
    if (!username || !email || !senha || !confirm) {
      return showFeedback("Preencha todos os campos.", "error");
    }
    if (senha !== confirm) {
      return showFeedback("As palavras-passe não coincidem.", "error");
    }
    try {
      const response = await requestJson("/auth/register", { method: "POST", body: JSON.stringify({ username, email, senha }) });
      setToken(response.token);
      navigateTo("dashboard.html");
    } catch (error) {
      showFeedback(error.message, "error");
    }
  });
}

// Dashboard page
if (document.body.contains(document.querySelector("#create-profile-button"))) {
  async function loadProfiles() {
    try {
      const data = await requestJson("/perfis", { method: "GET" });
      const profiles = data.perfis || {};
      const list = document.getElementById("profiles-list");
      list.innerHTML = "";
      if (Object.keys(profiles).length === 0) {
        list.innerHTML = `<div class="card"><p>Nenhum perfil registado ainda. Crie o seu primeiro planeamento.</p></div>`;
        return;
      }
      Object.entries(profiles).forEach(([nome, perfil]) => {
        const dados = perfil.dados || {};
        const card = document.createElement("article");
        card.className = "profile-card";
        card.innerHTML = `
          <div>
            <small>Perfil</small>
            <strong>${nome}</strong>
          </div>
          <div><small>Objetivo</small><br>${dados.objetivo || "-"}</div>
          <div><small>Peso</small><br>${dados.peso || "-"} kg</div>
          <div><small>IMC</small><br>${dados.peso && dados.altura ? (dados.peso / ((dados.altura / 100) ** 2)).toFixed(1) : "-"}</div>
          <div class="card-actions">
            <button class="secondary-button" data-action="open" data-profile="${nome}">Abrir Painel</button>
            <button class="secondary-button" data-action="delete" data-profile="${nome}">Excluir</button>
          </div>
        `;
        list.appendChild(card);
      });
      list.querySelectorAll("button[data-action='open']").forEach((button) => {
        button.addEventListener("click", () => {
          const profile = button.dataset.profile;
          navigateTo(`perfil.html?profile=${encodeURIComponent(profile)}`);
        });
      });
      list.querySelectorAll("button[data-action='delete']").forEach((button) => {
        button.addEventListener("click", async () => {
          const profile = button.dataset.profile;
          try {
            await requestJson(`/perfil/${encodeURIComponent(profile)}`, { method: "DELETE" });
            showFeedback("Perfil excluído com sucesso.", "info", "dashboard-feedback");
            loadProfiles();
          } catch (error) {
            showFeedback(error.message, "error", "dashboard-feedback");
          }
        });
      });
    } catch (error) {
      showFeedback(error.message, "error", "dashboard-feedback");
    }
  }

  if (!getToken()) {
    return navigateTo("index.html");
  }

  document.getElementById("logout-button").addEventListener("click", () => {
    clearToken();
    navigateTo("index.html");
  });

  document.getElementById("create-profile-button").addEventListener("click", async () => {
    const payload = {
      nome: document.getElementById("profile-name").value.trim(),
      idade: Number(document.getElementById("profile-age").value),
      sexo: document.getElementById("profile-gender").value,
      peso: Number(document.getElementById("profile-weight").value),
      altura: Number(document.getElementById("profile-height").value),
      alergias: document.getElementById("profile-allergies").value.trim() || "Nenhuma",
      objetivo: document.getElementById("profile-goal").value,
      nivel: document.getElementById("profile-activity").value,
    };
    if (!payload.nome) {
      return showFeedback("Nome do perfil é obrigatório.", "error", "dashboard-feedback");
    }
    try {
      await requestJson("/perfis", { method: "POST", body: JSON.stringify(payload) });
      showFeedback("Perfil criado com sucesso! Redirecionando...", "info", "dashboard-feedback");
      setTimeout(() => navigateTo(`perfil.html?profile=${encodeURIComponent(payload.nome)}`), 900);
    } catch (error) {
      showFeedback(error.message, "error", "dashboard-feedback");
    }
  });

  loadProfiles();
}

// Perfil page
if (document.body.contains(document.querySelector("#send-chat-button"))) {
  let macroChart = null;

  function parseQuery() {
    return new URLSearchParams(window.location.search);
  }

  function renderTable(containerId, title, tabela) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!tabela || tabela.length === 0) {
      container.innerHTML = `<p>Dados indisponíveis.</p>`;
      return;
    }
    const headers = tabela[0];
    const rows = tabela.slice(1);
    let html = `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>`;
    rows.forEach((row) => {
      html += `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  }

  function renderChat(messages) {
    const history = document.getElementById("chat-history");
    history.innerHTML = "";
    messages.forEach((message) => {
      const row = document.createElement("div");
      row.className = `chat-message-row ${message.role}`;
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble";
      bubble.innerText = message.content;
      row.appendChild(bubble);
      history.appendChild(row);
    });
    history.scrollTop = history.scrollHeight;
  }

  function formatTableData(df) {
    if (!df || !Array.isArray(df) || df.length === 0) return null;
    return df;
  }

  async function loadPerfil() {
    const query = parseQuery();
    const profileName = query.get("profile");
    if (!profileName) return showFeedback("Perfil não especificado.", "error", "chat-feedback");
    try {
      const data = await requestJson(`/perfil/${encodeURIComponent(profileName)}`, { method: "GET" });
      const dados = data.dados || {};
      const mensagens = data.mensagens || [];
      document.getElementById("profile-title").textContent = `Perfil: ${profileName}`;
      document.getElementById("profile-subtitle").textContent = `Objetivo: ${dados.objetivo || "-"}`;
      document.getElementById("stat-goal").textContent = dados.objetivo || "-";
      const plano = mensagens.slice().reverse().find((msg) => msg.role === "assistant" && msg.content.includes("## 🧬"));
      const content = plano ? plano.content : mensagens[0]?.content || "";
      const jsonData = extractJsonBlock(content);
      const tables = extractMarkdownTables(content);
      if (jsonData) {
        document.getElementById("stat-calories").textContent = `${jsonData.calorias || 0} kcal`;
        document.getElementById("stat-water").textContent = `${jsonData.agua_ml || 0} ml`;
        document.getElementById("stat-steps").textContent = `${jsonData.passos || 0} /dia`;
        renderMacroChart(jsonData);
      }
      const mealTable = tables.find((table) => table[0].toLowerCase().includes("plano alimentar") || table[1][0].some((cell) => /refeição|alimento/i.test(cell)));
      const supplementTable = tables.find((table) => table[0].toLowerCase().includes("suplementação") || table[1][0].some((cell) => /suplemento/i.test(cell)));
      const trainingTable = tables.find((table) => table[0].toLowerCase().includes("planilha") || table[1][0].some((cell) => /exercício|séries/i.test(cell)));
      renderTable("meal-plan", "Plano Alimentar", mealTable?.[1] || []);
      renderTable("supplement-plan", "Suplementação", supplementTable?.[1] || []);
      renderTable("training-plan", "Treino", trainingTable?.[1] || []);
      renderChat(mensagens.filter((msg) => msg.role && msg.content));
    } catch (error) {
      showFeedback(error.message, "error", "chat-feedback");
    }
  }

  function renderMacroChart(data) {
    const ctx = document.getElementById("macro-chart").getContext("2d");
    const values = [Number(data.proteinas_g || 0), Number(data.carboidratos_g || 0), Number(data.gorduras_g || 0)];
    if (macroChart) macroChart.destroy();
    macroChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Proteína", "Carboidratos", "Gorduras"],
        datasets: [{ data: values, backgroundColor: ["#60a5fa", "#38bdf8", "#a78bfa"], borderWidth: 0 }],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1" } } } },
    });
  }

  function extractJsonBlock(text) {
    const match = /```json\s*([\s\S]*?)\s*```/.exec(text);
    if (!match) return null;
    try { return JSON.parse(match[1]); } catch (error) { return null; }
  }

  function extractMarkdownTables(text) {
    const lines = text.split("\n");
    const tables = [];
    let buffer = [];
    let title = "";
    lines.forEach((line) => {
      const stripped = line.trim();
      if (/^#+\s*/.test(stripped)) { title = stripped.replace(/^#+\s*/, ""); }
      if (stripped.startsWith("|") && stripped.split("|").length >= 3) {
        buffer.push(stripped);
      } else if (buffer.length) {
        tables.push([title, buffer.map((row) => row.trim().split("|").slice(1, -1).map((cell) => cell.trim()))]);
        buffer = [];
      }
    });
    if (buffer.length) {
      tables.push([title, buffer.map((row) => row.trim().split("|").slice(1, -1).map((cell) => cell.trim()))]);
    }
    return tables;
  }

  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((tab) => tab.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.target).classList.add("active");
    });
  });

  document.getElementById("back-button").addEventListener("click", () => navigateTo("dashboard.html"));
  document.getElementById("logout-button-2").addEventListener("click", () => { clearToken(); navigateTo("index.html"); });

  document.getElementById("download-pdf-button").addEventListener("click", async () => {
    const profile = parseQuery().get("profile");
    if (!profile) return showFeedback("Perfil não especificado.", "error", "chat-feedback");
    try {
      const response = await fetch(`${API_BASE}/download-pdf/${encodeURIComponent(profile)}`, {
        method: "GET",
        headers: authHeaders(),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
      }
      const blob = await response.blob();
      downloadBlob(blob, `Relatorio_${profile.replace(/\s+/g, "_")}.pdf`);
    } catch (error) {
      showFeedback(error.message, "error", "chat-feedback");
    }
  });

  document.getElementById("send-chat-button").addEventListener("click", async () => {
    const profile = parseQuery().get("profile");
    const message = document.getElementById("chat-message").value.trim();
    if (!message) return showFeedback("Escreva uma mensagem.", "error", "chat-feedback");
    try {
      document.getElementById("chat-message").value = "";
      const data = await requestJson(`/chat/${encodeURIComponent(profile)}`, { method: "POST", body: JSON.stringify({ mensagem: message }) });
      renderChat(data.mensagens);
      loadPerfil();
    } catch (error) {
      showFeedback(error.message, "error", "chat-feedback");
    }
  });

  loadPerfil();
}
