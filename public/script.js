/* ═══════════════════════════════════════════════════════════════
   Halter AI — script.js
   API_BASE vazio = mesma origin (funciona no Render onde FastAPI
   serve tudo na raiz sem prefixo /api)
═══════════════════════════════════════════════════════════════ */

const API_BASE = "";   // rotas: /auth/login, /perfis, etc.

/* ── Token ────────────────────────────────────────────────────── */
const getToken    = () => localStorage.getItem("halterai_token");
const setToken    = (t) => localStorage.setItem("halterai_token", t);
const clearToken  = () => localStorage.removeItem("halterai_token");
const authHeaders = () => {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
};

/* ── Toast ────────────────────────────────────────────────────── */
function showToast(msg, duration = 3000) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), duration);
}

/* ── Feedback inline ──────────────────────────────────────────── */
function setFeedback(id, msg, type = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = "feedback " + (type === "error" ? "error" : type === "success" ? "success" : "");
}

/* ── Loading overlay ──────────────────────────────────────────── */
function showLoading(msg = "Aguarde...") {
  const ov = document.getElementById("loading-overlay");
  const tx = document.getElementById("loading-text");
  if (!ov) return;
  if (tx) tx.textContent = msg;
  ov.classList.add("show");
}
function hideLoading() {
  const ov = document.getElementById("loading-overlay");
  if (ov) ov.classList.remove("show");
}

/* ── HTTP helper ──────────────────────────────────────────────── */
async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...(options.headers || {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch (_) { data = { detail: text }; }

  if (!res.ok) {
    if (res.status === 401) { clearToken(); navigate("index.html"); }
    throw new Error(data?.detail || data?.message || res.statusText || "Erro desconhecido");
  }
  return data;
}

/* ── Navigation ───────────────────────────────────────────────── */
function navigate(url) { window.location.href = url; }
function parseQuery() { return new URLSearchParams(window.location.search); }

/* ── Blob download ────────────────────────────────────────────── */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

/* ══════════════════════════════════════════════════════════════
   AUTH PAGE  (index.html)
══════════════════════════════════════════════════════════════ */
if (document.getElementById("login-button")) {

  // Already logged in → skip to dashboard
  if (getToken()) navigate("dashboard.html");

  // Tab switching
  document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".auth-form").forEach((f) => f.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.target).classList.add("active");
      setFeedback("auth-feedback", "");
    });
  });

  // LOGIN
  document.getElementById("login-button").addEventListener("click", async () => {
    const login = document.getElementById("login-username").value.trim();
    const senha = document.getElementById("login-password").value.trim();
    if (!login || !senha) return setFeedback("auth-feedback", "Preencha todos os campos.", "error");

    const btn = document.getElementById("login-button");
    btn.disabled = true;
    btn.textContent = "A entrar...";
    setFeedback("auth-feedback", "");

    try {
      const res = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ login, senha }),
      });
      setToken(res.token);
      navigate("dashboard.html");
    } catch (err) {
      setFeedback("auth-feedback", err.message, "error");
      btn.disabled = false;
      btn.textContent = "Acessar a Plataforma";
    }
  });

  // REGISTER
  document.getElementById("register-button").addEventListener("click", async () => {
    const username = document.getElementById("register-username").value.trim();
    const email    = document.getElementById("register-email").value.trim();
    const senha    = document.getElementById("register-password").value.trim();
    const confirm  = document.getElementById("register-password-confirm").value.trim();

    if (!username || !email || !senha || !confirm)
      return setFeedback("auth-feedback", "Preencha todos os campos.", "error");
    if (senha !== confirm)
      return setFeedback("auth-feedback", "As palavras-passe não coincidem.", "error");
    if (senha.length < 6)
      return setFeedback("auth-feedback", "A senha deve ter ao menos 6 caracteres.", "error");

    const btn = document.getElementById("register-button");
    btn.disabled = true;
    btn.textContent = "A criar conta...";
    setFeedback("auth-feedback", "");

    try {
      const res = await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, senha }),
      });
      setToken(res.token);
      navigate("dashboard.html");
    } catch (err) {
      setFeedback("auth-feedback", err.message, "error");
      btn.disabled = false;
      btn.textContent = "Criar Conta";
    }
  });

  // Submit on Enter
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const activeForm = document.querySelector(".auth-form.active");
    if (!activeForm) return;
    if (activeForm.id === "login-form")    document.getElementById("login-button").click();
    if (activeForm.id === "register-form") document.getElementById("register-button").click();
  });
}

/* ══════════════════════════════════════════════════════════════
   DASHBOARD PAGE  (dashboard.html)
══════════════════════════════════════════════════════════════ */
if (document.getElementById("create-profile-button")) {

  if (!getToken()) navigate("index.html");

  /* --- render profiles list --- */
  async function loadProfiles() {
    const list = document.getElementById("profiles-list");
    list.innerHTML = `<div style="color:var(--gray-500);font-size:.88rem;padding:12px 0">A carregar...</div>`;
    try {
      const data = await api("/perfis");
      const perfis = data.perfis || {};
      list.innerHTML = "";

      if (Object.keys(perfis).length === 0) {
        list.innerHTML = `
          <div class="empty-state" style="grid-column:1/-1">
            <p>Nenhum planejamento criado ainda.<br>Preencha o formulário abaixo para começar.</p>
          </div>`;
        return;
      }

      Object.entries(perfis).forEach(([nome, perfil]) => {
        const d = perfil.dados || {};
        const imc = (d.peso && d.altura)
          ? (d.peso / ((d.altura / 100) ** 2)).toFixed(1)
          : "—";
        const goal = (d.objetivo || "").split("(")[0].trim();

        const card = document.createElement("article");
        card.className = "surface profile-card";
        card.innerHTML = `
          <div class="profile-name">${nome}</div>
          <div class="profile-meta">
            <div class="profile-meta-row"><span class="label">Objetivo</span><span class="value">${goal || "—"}</span></div>
            <div class="profile-meta-row"><span class="label">Peso</span><span class="value">${d.peso || "—"} kg</span></div>
            <div class="profile-meta-row"><span class="label">Altura</span><span class="value">${d.altura || "—"} cm</span></div>
            <div class="profile-meta-row"><span class="label">IMC</span><span class="value">${imc}</span></div>
          </div>
          <div class="profile-card-actions">
            <button class="btn btn-primary btn-sm btn-open" data-name="${nome}">Abrir Painel</button>
            <button class="btn btn-danger btn-sm btn-delete" data-name="${nome}">Excluir</button>
          </div>`;
        list.appendChild(card);
      });

      list.querySelectorAll(".btn-open").forEach((btn) =>
        btn.addEventListener("click", () =>
          navigate(`perfil.html?profile=${encodeURIComponent(btn.dataset.name)}`)
        )
      );
      list.querySelectorAll(".btn-delete").forEach((btn) =>
        btn.addEventListener("click", async () => {
          if (!confirm(`Excluir o perfil "${btn.dataset.name}"?`)) return;
          try {
            await api(`/perfil/${encodeURIComponent(btn.dataset.name)}`, { method: "DELETE" });
            showToast("Perfil excluído.");
            loadProfiles();
          } catch (err) {
            setFeedback("dashboard-feedback", err.message, "error");
          }
        })
      );
    } catch (err) {
      list.innerHTML = "";
      setFeedback("dashboard-feedback", err.message, "error");
    }
  }

  loadProfiles();

  /* --- logout --- */
  document.getElementById("logout-button").addEventListener("click", () => {
    clearToken();
    navigate("index.html");
  });

  /* --- create profile --- */
  document.getElementById("create-profile-button").addEventListener("click", async () => {
    const nome = document.getElementById("profile-name").value.trim();
    if (!nome) return setFeedback("dashboard-feedback", "O nome do perfil é obrigatório.", "error");

    const payload = {
      nome,
      idade:    Number(document.getElementById("profile-age").value),
      sexo:     document.getElementById("profile-gender").value,
      peso:     Number(document.getElementById("profile-weight").value),
      altura:   Number(document.getElementById("profile-height").value),
      alergias: document.getElementById("profile-allergies").value.trim() || "Nenhuma",
      objetivo: document.getElementById("profile-goal").value,
      nivel:    document.getElementById("profile-activity").value,
    };

    setFeedback("dashboard-feedback", "");
    showLoading("A gerar o seu planejamento com IA... pode demorar até 30 segundos.");

    try {
      await api("/perfis", { method: "POST", body: JSON.stringify(payload) });
      hideLoading();
      navigate(`perfil.html?profile=${encodeURIComponent(nome)}`);
    } catch (err) {
      hideLoading();
      setFeedback("dashboard-feedback", err.message, "error");
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   PERFIL PAGE  (perfil.html)
══════════════════════════════════════════════════════════════ */
if (document.getElementById("send-chat-button")) {

  if (!getToken()) navigate("index.html");

  const profileName = parseQuery().get("profile");
  if (!profileName) navigate("dashboard.html");

  let macroChart = null;

  /* ── Helpers: parse ─────────────────────────────────────── */
  function extractJson(text) {
    const m = /```json\s*([\s\S]*?)\s*```/.exec(text);
    if (!m) return null;
    try { return JSON.parse(m[1]); } catch (_) { return null; }
  }

  function extractTables(text) {
    const lines = text.split("\n");
    const tables = [];
    let buf = [], title = "";

    lines.forEach((line) => {
      const s = line.trim();
      if (/^#+\s/.test(s)) title = s.replace(/^#+\s*/, "").replace(/\*\*/g, "").trim();
      if (s.startsWith("|") && s.split("|").length >= 3) {
        buf.push(s);
      } else if (buf.length) {
        const rows = buf
          .map((r) => r.trim().split("|").slice(1, -1).map((c) => c.trim()))
          .filter((r) => !r.every((c) => /^[-:]+$/.test(c)));   // drop separator rows
        if (rows.length > 1) tables.push({ title, rows });
        buf = [];
      }
    });
    if (buf.length) {
      const rows = buf
        .map((r) => r.trim().split("|").slice(1, -1).map((c) => c.trim()))
        .filter((r) => !r.every((c) => /^[-:]+$/.test(c)));
      if (rows.length > 1) tables.push({ title, rows });
    }
    return tables;
  }

  function findTable(tables, ...keywords) {
    return tables.find((t) =>
      keywords.some(
        (kw) =>
          t.title.toLowerCase().includes(kw) ||
          (t.rows[0] || []).some((c) => c.toLowerCase().includes(kw))
      )
    );
  }

  /* ── Render table ──────────────────────────────────────── */
  function renderTable(containerId, table) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!table || table.rows.length < 2) {
      el.innerHTML = `<p style="color:var(--gray-500);font-size:.85rem">Não disponível.</p>`;
      return;
    }
    const [head, ...body] = table.rows;
    const ths = head.map((h) => `<th>${h}</th>`).join("");
    const trs = body.map(
      (row) => `<tr>${row.map((c) => `<td>${c}</td>`).join("")}</tr>`
    ).join("");
    el.innerHTML = `<div style="overflow-x:auto"><table class="data-table"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table></div>`;
  }

  /* ── Render chart ──────────────────────────────────────── */
  function renderMacroChart(json) {
    const ctx = document.getElementById("macro-chart");
    if (!ctx) return;
    const vals = [
      Number(json.proteinas_g    || 0),
      Number(json.carboidratos_g || 0),
      Number(json.gorduras_g     || 0),
    ];
    if (macroChart) macroChart.destroy();
    macroChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Proteína", "Carboidratos", "Gorduras"],
        datasets: [{
          data: vals,
          backgroundColor: ["#e8e8e8", "#888888", "#444444"],
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        cutout: "62%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#aaa", padding: 14, font: { size: 12 } },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.parsed}g`,
            },
          },
        },
      },
    });
  }

  /* ── Render IMC ────────────────────────────────────────── */
  function renderIMC(dados) {
    if (!dados?.peso || !dados?.altura) return;
    const imc = dados.peso / ((dados.altura / 100) ** 2);
    const el = document.getElementById("imc-value");
    const lb = document.getElementById("imc-label");
    const mk = document.getElementById("imc-marker");
    if (el) el.textContent = imc.toFixed(1);

    let label, pct;
    if      (imc < 18.5) { label = "Baixo Peso"; pct = 8;  }
    else if (imc < 25)   { label = "Saudável";   pct = 32; }
    else if (imc < 30)   { label = "Sobrepeso";  pct = 62; }
    else                 { label = "Obesidade";  pct = 88; }

    if (lb) { lb.textContent = label; }
    if (mk) mk.style.left = pct + "%";
  }

  /* ── Render chat ───────────────────────────────────────── */
  function renderChat(msgs) {
    const hist = document.getElementById("chat-history");
    if (!hist) return;

    // Only show user ↔ assistant turns, skip raw plan (large assistant msg with tables)
    const display = msgs.filter((m) => {
      if (m.role === "user") return true;
      // assistant: only show if it's a short reply (no plan structure)
      return m.role === "assistant" && !m.content.includes("## 🧬");
    });

    if (display.length === 0) {
      hist.innerHTML = `<div class="chat-empty">Sem mensagens ainda. Peça uma alteração ou tire uma dúvida.</div>`;
      return;
    }

    hist.innerHTML = display.map((m) => `
      <div class="chat-row ${m.role}">
        <div class="chat-bubble">${escapeHtml(m.content)}</div>
      </div>`).join("");
    hist.scrollTop = hist.scrollHeight;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ── Load profile data ─────────────────────────────────── */
  async function loadPerfil() {
    try {
      const data = await api(`/perfil/${encodeURIComponent(profileName)}`);
      const dados = data.dados || {};
      const msgs  = data.mensagens || [];

      // Header
      document.getElementById("profile-title").textContent = profileName;
      document.getElementById("profile-subtitle").textContent =
        dados.objetivo ? dados.objetivo.split("(")[0].trim() : "";

      // Find plan content
      const plan = msgs.slice().reverse().find(
        (m) => m.role === "assistant" && m.content.includes("## 🧬")
      ) || msgs[0];
      const content = plan?.content || "";

      const json   = extractJson(content);
      const tables = extractTables(content);

      // Stats
      if (json) {
        document.getElementById("stat-calories").textContent = `${json.calorias || 0} kcal`;
        document.getElementById("stat-water").textContent   = `${json.agua_ml  || 0} ml`;
        document.getElementById("stat-steps").textContent   = `${json.passos   || 0}`;
        renderMacroChart(json);
      }

      const goal = (dados.objetivo || "").split("(")[0].trim();
      document.getElementById("stat-goal").textContent = goal || "—";

      // Tables
      renderTable("meal-plan",       findTable(tables, "plano alimentar", "alimento", "refeição"));
      renderTable("supplement-plan", findTable(tables, "suplementação", "suplemento"));
      renderTable("training-plan",   findTable(tables, "treinamento", "treino", "exercício", "séries"));

      // IMC
      renderIMC(dados);

      // Chat
      renderChat(msgs);

    } catch (err) {
      setFeedback("chat-feedback", err.message, "error");
    }
  }

  loadPerfil();

  /* ── Tabs ──────────────────────────────────────────────── */
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.target).classList.add("active");
    });
  });

  /* ── Back / Logout ─────────────────────────────────────── */
  document.getElementById("back-button").addEventListener("click", () => navigate("dashboard.html"));
  document.getElementById("logout-button-2").addEventListener("click", () => {
    clearToken(); navigate("index.html");
  });

  /* ── PDF download ──────────────────────────────────────── */
  document.getElementById("download-pdf-button").addEventListener("click", async () => {
    const btn = document.getElementById("download-pdf-button");
    btn.disabled = true;
    btn.textContent = "A gerar...";
    try {
      const res = await fetch(`${API_BASE}/download-pdf/${encodeURIComponent(profileName)}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const blob = await res.blob();
      downloadBlob(blob, `Halter_AI_${profileName.replace(/\s+/g, "_")}.pdf`);
      showToast("PDF descarregado com sucesso!");
    } catch (err) {
      setFeedback("chat-feedback", err.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Baixar PDF";
    }
  });

  /* ── Quick action chips ────────────────────────────────── */
  document.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const ta = document.getElementById("chat-message");
      if (ta) { ta.value = chip.dataset.msg; ta.focus(); }
    });
  });

  /* ── Send chat ─────────────────────────────────────────── */
  document.getElementById("send-chat-button").addEventListener("click", sendChat);
  document.getElementById("chat-message").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });

  async function sendChat() {
    const ta  = document.getElementById("chat-message");
    const msg = ta.value.trim();
    if (!msg) return setFeedback("chat-feedback", "Escreva uma mensagem.", "error");

    const btn = document.getElementById("send-chat-button");
    btn.disabled = true;
    ta.value = "";
    setFeedback("chat-feedback", "");
    showLoading("A IA está a processar o seu pedido...");

    try {
      const data = await api(`/chat/${encodeURIComponent(profileName)}`, {
        method: "POST",
        body: JSON.stringify({ mensagem: msg }),
      });
      hideLoading();
      renderChat(data.mensagens || []);

      // If the reply contains a new plan, refresh dashboard data too
      const lastMsg = (data.mensagens || []).slice().reverse().find(
        (m) => m.role === "assistant"
      );
      if (lastMsg?.content.includes("## 🧬")) {
        await loadPerfil();
        showToast("Plano atualizado! Veja o Dashboard.");
      }
    } catch (err) {
      hideLoading();
      setFeedback("chat-feedback", err.message, "error");
    } finally {
      btn.disabled = false;
    }
  }
}