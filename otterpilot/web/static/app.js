"use strict";

(() => {
  const root = document.getElementById("root");
  const REFRESH_MS = 30000;

  // ------------------------------------------------------------ DOM

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);

    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;

      if (key === "class") el.className = value;
      else if (key === "style" && typeof value === "object") Object.assign(el.style, value);
      else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
      else if (key === "value") el.value = value;
      else if (key === "checked" || key === "disabled" || key === "selected") el[key] = Boolean(value);
      else el.setAttribute(key, value === true ? "" : String(value));
    }

    append(el, children);
    return el;
  }

  function append(el, children) {
    for (const child of children.flat(Infinity)) {
      if (child === null || child === undefined || child === false) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  }

  function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
    return el;
  }

  function toast(message, kind) {
    const el = h("div", { class: `toast ${kind || ""}` }, message);
    document.getElementById("toasts").append(el);
    setTimeout(() => el.remove(), kind === "error" ? 7000 : 4000);
  }

  // ------------------------------------------------------------ API

  class ApiError extends Error {
    constructor(status, detail) {
      super(detail);
      this.status = status;
    }
  }

  async function request(method, path, body) {
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    let data = null;
    try { data = await response.json(); } catch (_) { /* sem corpo */ }

    if (response.status === 401 && path !== "/api/auth/login" && path !== "/api/auth/password") {
      showLogin();
      throw new ApiError(401, "Sessão expirada");
    }

    if (!response.ok) {
      let detail = data && data.detail;
      if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
      throw new ApiError(response.status, detail || `Erro ${response.status}`);
    }

    return data;
  }

  const api = {
    get: (path) => request("GET", path),
    put: (path, body) => request("PUT", path, body),
    post: (path, body) => request("POST", path, body || {}),
    del: (path) => request("DELETE", path),
  };

  // ------------------------------------------------------------ formatação

  const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
  const nfInt = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

  function num(value, digits) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value !== "number") return String(value);
    return digits === 0 ? nfInt.format(value) : nf.format(value);
  }

  function yesNo(value) {
    if (value === true) return "Sim";
    if (value === false) return "Não";
    return "—";
  }

  function duration(seconds) {
    if (seconds === null || seconds === undefined) return "—";
    seconds = Math.max(0, Math.round(seconds));
    if (seconds < 60) return `${seconds} s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
    return `${Math.floor(seconds / 86400)} d ${Math.floor((seconds % 86400) / 3600)} h`;
  }

  function ago(iso) {
    if (!iso) return "—";
    const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
    if (!isFinite(seconds)) return "—";
    if (seconds < 5) return "agora";
    return `há ${duration(seconds)}`;
  }

  function absolute(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    return isNaN(date) ? iso : date.toLocaleString("pt-BR");
  }

  function timeCell(iso) {
    return h("span", { title: absolute(iso), class: "nowrap" }, ago(iso));
  }

  // ------------------------------------------------------------ status

  const STATUS_LABEL = {
    healthy: "Saudável", ok: "OK", online: "Online",
    warning: "Alerta", degraded: "Degradado", unknown: "Desconhecido",
    critical: "Crítico", offline: "Offline", error: "Erro", failed: "Falha",
    stopped: "Parado", running: "Rodando",
    unexpected_stopped: "Parado (inesperado)", unexpected_running: "Rodando (inesperado)",
    unexpected_state: "Estado inesperado",
    connected: "Conectado", disconnected: "Desconectado", not_configured: "Não configurado",
    disabled: "Desativado", pending: "Aguardando",
  };

  function statusClass(status, stale) {
    if (stale) return "stale";
    switch (String(status || "").toLowerCase()) {
      case "healthy": case "ok": case "online": case "connected": case "running": case "info":
        return "ok";
      case "critical": case "offline": case "error": case "failed":
        return "crit";
      case "stopped": case "disabled": case "pending":
        return "";
      default:
        return "warn";
    }
  }

  function badge(status, stale, label) {
    const text = label || (stale ? `${STATUS_LABEL[status] || status} · desatualizado` : STATUS_LABEL[status] || status || "—");
    return h("span", { class: `badge ${statusClass(status, stale)}` }, text);
  }

  function impactBadge(impact) {
    return h("span", { class: `badge ${impact === "critical" ? "crit" : "warn"}` }, impact === "critical" ? "Crítico" : "Alerta");
  }

  function meter(value, options) {
    if (value === null || value === undefined) return h("span", { class: "muted" }, "—");
    const opts = Object.assign({ warn: 85, crit: 95, invert: false, max: 100, unit: "%" }, options);
    const pct = Math.max(0, Math.min(100, (value / opts.max) * 100));
    let level = "";
    if (opts.invert) {
      if (value <= opts.crit) level = "crit";
      else if (value <= opts.warn) level = "warn";
    } else if (value >= opts.crit) level = "crit";
    else if (value >= opts.warn) level = "warn";

    return h("span", { class: "meter" },
      h("span", { class: "meter-bar" }, h("span", { class: `meter-fill ${level}`, style: { width: `${pct}%` } })),
      h("span", { class: "meter-value" }, `${nf.format(value)}${opts.unit}`));
  }

  // ------------------------------------------------------------ capabilities

  const p = (r) => r.payload || {};

  const CAPABILITIES = {
    host_health: {
      label: "Hosts", order: 1,
      columns: [
        { label: "Nó", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "CPU", render: (r) => meter(p(r).cpu_percent), sort: (r) => p(r).cpu_percent },
        { label: "RAM", render: (r) => meter(p(r).memory_percent), sort: (r) => p(r).memory_percent },
        { label: "Disco", render: (r) => meter(p(r).disk_percent), sort: (r) => p(r).disk_percent },
        { label: "Threads", value: (r) => p(r).cpu_threads, num: true },
        { label: "Uptime", value: (r) => duration(p(r).uptime_seconds), sort: (r) => p(r).uptime_seconds },
      ],
    },
    virtualization: {
      label: "Virtualização", order: 2,
      columns: [
        { label: "ID", value: (r) => r.resource_id, sort: (r) => Number(String(r.resource_id).split("/")[1]) },
        { label: "Nome", value: (r) => p(r).name },
        { label: "Nó", value: (r) => p(r).node },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Proxmox", value: (r) => STATUS_LABEL[p(r).proxmox_status] || p(r).proxmox_status },
        { label: "Esperado", value: (r) => STATUS_LABEL[p(r).expected_state] || "—" },
        { label: "Importância", value: (r) => ({ critical: "Crítica", warning: "Normal" })[p(r).importance] || "—" },
        { label: "CPU", render: (r) => meter(p(r).cpu_percent), sort: (r) => p(r).cpu_percent },
        { label: "RAM", render: (r) => meter(p(r).memory_percent), sort: (r) => p(r).memory_percent },
        { label: "Disco", render: (r) => (p(r).guest_type === "lxc" ? meter(p(r).disk_percent) : h("span", { class: "muted" }, "—")), sort: (r) => p(r).disk_percent },
      ],
    },
    dns: {
      label: "DNS", order: 3,
      columns: [
        { label: "Instância", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Rodando", value: (r) => yesNo(p(r).running) },
        { label: "Proteção", value: (r) => yesNo(p(r).protection_enabled) },
        { label: "Consultas", value: (r) => num(p(r).num_dns_queries, 0), num: true, sort: (r) => p(r).num_dns_queries },
        { label: "Bloqueado", value: (r) => (p(r).blocked_percent == null ? "—" : `${num(p(r).blocked_percent)}%`), num: true, sort: (r) => p(r).blocked_percent },
        { label: "Erros (log)", value: (r) => p(r).querylog_error_count, num: true },
        { label: "Score", value: (r) => p(r).health_score, num: true },
        { label: "Versão", value: (r) => p(r).version || p(r).error },
      ],
    },
    ups: {
      label: "UPS", order: 4,
      columns: [
        { label: "Recurso", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Estado do UPS", value: (r) => p(r).ups_status },
        { label: "Bateria", render: (r) => meter(p(r).battery_percent, { warn: 40, crit: 20, invert: true }), sort: (r) => p(r).battery_percent },
      ],
    },
    environment_health: {
      label: "Ambiente", order: 5,
      columns: [
        { label: "Recurso", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Temperatura", render: (r) => meter(p(r).temperature_c, { warn: 45, crit: 50, max: 60, unit: " °C" }), sort: (r) => p(r).temperature_c },
        { label: "Entidade", value: (r) => p(r).entity_id },
      ],
    },
    zigbee_health: {
      label: "Zigbee", order: 6,
      columns: [
        { label: "Instância", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Online", value: (r) => yesNo(p(r).online) },
        { label: "Versão", value: (r) => p(r).version },
        { label: "Dispositivos", value: (r) => p(r).device_count, num: true },
        { label: "Canal", value: (r) => p(r).channel, num: true },
        { label: "Coordenador", value: (r) => p(r).coordinator_type },
        { label: "MQTT", value: (r) => yesNo(p(r).mqtt_connected) },
        { label: "Reinício pendente", value: (r) => yesNo(p(r).restart_required) },
      ],
    },
    camera_health: {
      label: "Câmeras", order: 7,
      columns: [
        { label: "Câmera", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "FPS câmera", value: (r) => num(p(r).camera_fps), num: true, sort: (r) => p(r).camera_fps },
        { label: "FPS processado", value: (r) => num(p(r).process_fps), num: true, sort: (r) => p(r).process_fps },
        { label: "FPS descartado", value: (r) => num(p(r).skipped_fps), num: true, sort: (r) => p(r).skipped_fps },
        { label: "FPS detecção", value: (r) => num(p(r).detection_fps), num: true, sort: (r) => p(r).detection_fps },
      ],
    },
    llm_runtime: {
      label: "LLM", order: 8,
      columns: [
        { label: "Recurso", value: (r) => r.resource_id },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Modelo", value: (r) => p(r).model },
        { label: "Carregado", value: (r) => yesNo(p(r).loaded) },
        { label: "Latência", value: (r) => (p(r).latency_ms == null ? "—" : `${num(p(r).latency_ms, 0)} ms`), num: true, sort: (r) => p(r).latency_ms },
        { label: "VRAM", value: (r) => (p(r).size_vram_gb == null ? "—" : `${num(p(r).size_vram_gb)} GB`), num: true },
        { label: "Resumo", value: (r) => p(r).summary },
      ],
    },
    vehicle: {
      label: "Veículo", order: 9,
      columns: [
        { label: "Veículo", value: (r) => [p(r).manufacturer, p(r).model].filter(Boolean).join(" ") || r.resource_id },
        { label: "Local", value: (r) => p(r).zone },
        { label: "Autonomia", value: (r) => (p(r).range_km == null ? "—" : `${num(p(r).range_km, 0)} km`), num: true },
        { label: "Combustível", render: (r) => meter(p(r).fuel_percent, { warn: 25, crit: 10, invert: true }) },
        { label: "Motor", value: (r) => (p(r).engine_running ? "Ligado" : p(r).engine_running === false ? "Desligado" : "—") },
        { label: "Travado", value: (r) => yesNo(p(r).locked) },
        { label: "Porta aberta", value: (r) => yesNo(p(r).any_door_open) },
        { label: "Pneu (mín.)", value: (r) => (p(r).tire_min_psi == null ? "—" : `${num(p(r).tire_min_psi)} psi`), num: true },
        { label: "Revisão", value: (r) => (p(r).days_to_service == null ? "—" : `${p(r).days_to_service} dias`), num: true },
      ],
    },
  };

  const HIDDEN_CAPABILITIES = new Set(["system_health", "object_detection"]);
  const EXTRA_LABELS = { object_detection: "Detecções", system_health: "Saúde do sistema" };

  function capabilityLabel(id) {
    return (CAPABILITIES[id] && CAPABILITIES[id].label) || EXTRA_LABELS[id] || id;
  }

  function defaultColumns() {
    return [
      { label: "Recurso", value: (r) => r.name ? `${r.resource_id} · ${r.name}` : r.resource_id },
      { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
      { label: "Mensagem", value: (r) => r.message },
    ];
  }

  // ------------------------------------------------------------ tabela

  function dataTable(rows, columns, options) {
    const opts = Object.assign({ onRowClick: null, empty: "Nada para mostrar." }, options);
    let sortIndex = null;
    let sortDir = 1;
    const wrap = h("div", { class: "table-wrap" });

    function cellValue(column, row) {
      return column.value ? column.value(row) : null;
    }

    function sortKey(column, row) {
      const value = column.sort ? column.sort(row) : cellValue(column, row);
      return value === null || value === undefined ? "" : value;
    }

    function draw() {
      let sorted = rows.slice();
      if (sortIndex !== null) {
        const column = columns[sortIndex];
        sorted.sort((a, b) => {
          const x = sortKey(column, a);
          const y = sortKey(column, b);
          if (typeof x === "number" && typeof y === "number") return (x - y) * sortDir;
          return String(x).localeCompare(String(y), "pt-BR", { numeric: true }) * sortDir;
        });
      }

      const head = h("tr", null, columns.map((column, index) =>
        h("th", {
          class: `sortable ${column.num ? "right" : ""}`,
          onclick: () => {
            sortDir = sortIndex === index ? -sortDir : 1;
            sortIndex = index;
            draw();
          },
        }, column.label, sortIndex === index ? (sortDir > 0 ? " ↑" : " ↓") : "")));

      const body = sorted.length
        ? sorted.map((row) => h("tr", {
            class: opts.onRowClick ? "clickable" : "",
            onclick: opts.onRowClick ? () => opts.onRowClick(row) : null,
          }, columns.map((column) => h("td", { class: column.num ? "num" : "" },
            column.render ? column.render(row) : (cellValue(column, row) ?? "—")))))
        : [h("tr", null, h("td", { colspan: columns.length, class: "empty" }, opts.empty))];

      clear(wrap).append(h("table", null, h("thead", null, head), h("tbody", null, body)));
    }

    draw();
    return wrap;
  }

  // ------------------------------------------------------------ overlays

  function closeOverlay() {
    document.querySelectorAll(".overlay").forEach((el) => el.remove());
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeOverlay();
  });

  function overlay(content, centered) {
    closeOverlay();
    const el = h("div", {
      class: `overlay ${centered ? "center" : ""}`,
      onclick: (event) => { if (event.target === el) closeOverlay(); },
    }, content);
    document.body.append(el);
    return el;
  }

  function confirmButton(label, confirmLabel, action, cls) {
    let armed = false;
    let timer = null;
    const button = h("button", {
      class: `btn ${cls || "danger"}`,
      onclick: async () => {
        if (!armed) {
          armed = true;
          button.textContent = confirmLabel;
          timer = setTimeout(() => { armed = false; button.textContent = label; }, 4000);
          return;
        }
        clearTimeout(timer);
        button.disabled = true;
        try { await action(); } finally { button.disabled = false; }
      },
    }, label);
    return button;
  }

  function flatten(payload) {
    const scalars = [];
    const nested = {};
    for (const [key, value] of Object.entries(payload || {})) {
      if (value !== null && typeof value === "object") nested[key] = value;
      else scalars.push([key, value]);
    }
    return { scalars, nested };
  }

  async function openResource(row) {
    const path = `/api/resources/${encodeURIComponent(row.connector)}/${encodeURIComponent(row.capability)}/${row.resource_id.split("/").map(encodeURIComponent).join("/")}`;
    let detail;
    try { detail = await api.get(path); } catch (error) { toast(error.message, "error"); return; }

    const { scalars, nested } = flatten(detail.payload);

    const forget = confirmButton("Esquecer recurso", "Clique de novo para confirmar", async () => {
      try {
        await api.del(path);
        toast("Recurso removido do estado atual.");
        closeOverlay();
        render();
      } catch (error) { toast(error.message, "error"); }
    });

    overlay(h("aside", { class: "drawer", role: "dialog", "aria-label": "Detalhes do recurso" },
      h("div", { class: "drawer-head" },
        h("div", { class: "spacer" },
          h("div", { class: "small muted" }, `${detail.connector} · ${capabilityLabel(detail.capability)}`),
          h("h1", null, detail.name ? `${detail.name}` : detail.resource_id),
          detail.name ? h("div", { class: "mono muted" }, detail.resource_id) : null),
        h("button", { class: "btn ghost", onclick: closeOverlay, "aria-label": "Fechar" }, "✕")),
      h("div", { class: "drawer-body" },
        h("div", { class: "row" }, badge(detail.status, detail.stale), h("span", { class: "badge plain" }, `severidade: ${detail.severity}`)),
        detail.message ? h("div", null, detail.message) : null,
        h("div", { class: "kv" },
          h("div", null, "atualizado"), h("div", { title: absolute(detail.timestamp) }, `${ago(detail.timestamp)} (${absolute(detail.timestamp)})`),
          h("div", null, "evento"), h("div", null, detail.event_type),
          scalars.map(([key, value]) => [h("div", null, key), h("div", null, value === null ? "—" : typeof value === "boolean" ? yesNo(value) : String(value))])),
        Object.keys(nested).length ? h("details", null, h("summary", null, "Dados aninhados"),
          h("pre", { class: "json" }, JSON.stringify(nested, null, 2))) : null,
        detail.stale ? h("div", { class: "notice warn" },
          "Este recurso não é atualizado há algum tempo. Se ele deixou de existir, você pode removê-lo do estado atual; ele volta automaticamente se reaparecer.") : null,
        h("div", { class: "row" }, h("span", { class: "spacer" }), forget))));
  }

  // ------------------------------------------------------------ shell

  const state = { system: null, capabilities: [], timer: null, lastLoad: null };

  const NAV = [
    { title: "Visão geral", items: [
      { hash: "#/", label: "Saúde do sistema" },
      { hash: "#/problems", label: "Problemas", count: () => state.system && state.system.problem_count, countClass: () => (state.system && state.system.critical_count ? "crit" : "warn") },
      { hash: "#/resources", label: "Recursos", count: () => state.system && state.system.resource_count },
      { hash: "#/activity", label: "Atividade" },
    ] },
    { title: "Infraestrutura", items: () => state.capabilities
        .filter((c) => !HIDDEN_CAPABILITIES.has(c.id) && c.stats.total > 0)
        .sort((a, b) => ((CAPABILITIES[a.id] || {}).order || 99) - ((CAPABILITIES[b.id] || {}).order || 99))
        .map((c) => ({
          hash: `#/capability/${c.id}`,
          label: capabilityLabel(c.id),
          count: () => c.stats.problem || null,
          countClass: () => "warn",
        })) },
    { title: "Operação", items: [
      { hash: "#/integrations", label: "Integrações" },
      { hash: "#/copilot", label: "Copilot" },
    ] },
    { title: "Configurações", items: [
      { hash: "#/settings/polling", label: "Coleta" },
      { hash: "#/settings/policies", label: "Políticas" },
      { hash: "#/settings/files", label: "Arquivos" },
      { hash: "#/settings/system", label: "Sistema" },
    ] },
  ];

  const OTTER = '<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="16" fill="#0f7c86"/><circle cx="17" cy="20" r="6" fill="#e9d3b4"/><circle cx="47" cy="20" r="6" fill="#e9d3b4"/><ellipse cx="32" cy="35" rx="20" ry="18" fill="#e9d3b4"/><ellipse cx="32" cy="42" rx="11" ry="8" fill="#fbf3e7"/><circle cx="24" cy="31" r="2.6" fill="#17202a"/><circle cx="40" cy="31" r="2.6" fill="#17202a"/><ellipse cx="32" cy="38" rx="3.6" ry="2.6" fill="#17202a"/><path d="M28 44c2 1.6 6 1.6 8 0" stroke="#17202a" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>';

  function brand(sub) {
    const mark = h("span");
    mark.innerHTML = OTTER; // SVG estático, sem dados externos.
    return h("div", { class: "brand" }, mark.firstChild,
      h("div", null, h("div", { class: "brand-name" }, "OtterPilot"), sub ? h("div", { class: "brand-sub" }, sub) : null));
  }

  let shell = null;

  function buildShell() {
    const sidebar = h("nav", { class: "sidebar", "aria-label": "Navegação" });
    const title = h("div", { class: "title" });
    const statusSlot = h("div");
    const content = h("main", { class: "content" });
    const app = h("div", { class: "app" },
      sidebar,
      h("div", { class: "main" },
        h("header", { class: "topbar" },
          h("button", { class: "btn ghost menu-toggle", "aria-label": "Menu", onclick: () => app.classList.toggle("menu-open") }, "☰"),
          title,
          statusSlot,
          h("button", { class: "btn small", onclick: () => render(), title: "Atualizar" }, "Atualizar")),
        content));

    clear(root).append(app);
    shell = { app, sidebar, title, statusSlot, content };
  }

  function drawSidebar() {
    const current = location.hash || "#/";
    clear(shell.sidebar).append(brand(state.system ? `v${state.system.version}` : ""));

    for (const section of NAV) {
      const items = typeof section.items === "function" ? section.items() : section.items;
      if (!items.length) continue;
      shell.sidebar.append(h("div", { class: "nav-section" },
        h("h3", null, section.title),
        items.map((item) => {
          const count = item.count ? item.count() : null;
          const active = current === item.hash || (item.hash !== "#/" && current.startsWith(item.hash + "/"));
          return h("a", { class: `nav-link ${active ? "active" : ""}`, href: item.hash, onclick: () => shell.app.classList.remove("menu-open") },
            h("span", null, item.label),
            count ? h("span", { class: `nav-count ${item.countClass ? item.countClass() : ""}` }, count) : null);
        })));
    }
  }

  function setTitle(text, subtitle) {
    append(clear(shell.title), [h("h1", null, text), subtitle ? h("div", { class: "subtitle" }, subtitle) : null]);
    clear(shell.statusSlot);
    if (state.system) {
      const labels = { healthy: "Operacional", degraded: "Degradado", critical: "Crítico" };
      shell.statusSlot.append(badge(state.system.overall_status, false, labels[state.system.overall_status]));
    }
  }

  async function loadShellData() {
    const [system, capabilities] = await Promise.all([api.get("/api/system"), api.get("/api/capabilities")]);
    state.system = system;
    state.capabilities = capabilities;
    state.lastLoad = new Date();
  }

  // ------------------------------------------------------------ páginas

  function card(title, body, actions) {
    return h("section", { class: "card" },
      title ? h("div", { class: "card-head" }, h("h2", null, title), actions || null) : null,
      body);
  }

  function problemsTable(problems) {
    return dataTable(problems, [
      { label: "Impacto", render: (r) => impactBadge(r.impact), sort: (r) => (r.impact === "critical" ? 0 : 1) },
      { label: "Recurso", value: (r) => r.resource_id },
      { label: "Capability", value: (r) => capabilityLabel(r.capability) },
      { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
      { label: "Motivo", value: (r) => r.reason },
    ], { onRowClick: openResource, empty: "Nenhum problema. 🦦" });
  }

  async function pageOverview() {
    const s = state.system;
    const marks = { healthy: "✓", degraded: "!", critical: "✕" };
    const labels = { healthy: "Tudo operacional", degraded: "Ambiente degradado", critical: "Problema crítico" };

    const kpis = h("div", { class: "grid kpis" },
      [
        ["Recursos", s.resource_count, ""],
        ["Saudáveis", s.healthy_count, "ok"],
        ["Alertas", s.warning_count, s.warning_count ? "warn" : ""],
        ["Críticos", s.critical_count, s.critical_count ? "crit" : ""],
        ["Sem atualização", s.stale_count, s.stale_count ? "stale" : ""],
      ].map(([label, value, cls]) => h("div", { class: `card kpi ${cls}` }, h("div", { class: "label" }, label), h("div", { class: "value" }, num(value, 0)))));

    const capabilityCards = state.capabilities
      .filter((c) => !HIDDEN_CAPABILITIES.has(c.id) && c.stats.total > 0)
      .sort((a, b) => ((CAPABILITIES[a.id] || {}).order || 99) - ((CAPABILITIES[b.id] || {}).order || 99))
      .map((c) => {
        const { total, problem, stale } = c.stats;
        const warn = Math.max(0, problem - stale);
        const ok = Math.max(0, total - problem);
        return h("a", { class: "card card-body stack", href: `#/capability/${c.id}`, style: { textDecoration: "none", color: "inherit" } },
          h("div", { class: "row" },
            h("h2", null, capabilityLabel(c.id)), h("span", { class: "spacer" }),
            problem ? h("span", { class: "badge warn" }, `${problem} com atenção`) : h("span", { class: "badge ok" }, "OK")),
          h("div", { class: "stackbar" },
            h("span", { class: "ok", style: { width: `${(ok / total) * 100}%` } }),
            h("span", { class: "warn", style: { width: `${(warn / total) * 100}%` } }),
            h("span", { class: "stale", style: { width: `${(stale / total) * 100}%` } })),
          h("div", { class: "small muted" }, `${total} recurso(s) · ${c.connectors.join(", ")}`));
      });

    let jobsCard = null;
    try {
      const jobs = await api.get("/api/jobs");
      const failing = jobs.filter((job) => job.outcome === "error");
      if (failing.length) {
        jobsCard = card("Coletas com falha", h("div", { class: "card-body flush" }, dataTable(failing, [
          { label: "Job", value: (r) => r.job_id },
          { label: "Falhas seguidas", value: (r) => r.consecutive_failures, num: true },
          { label: "Último sucesso", render: (r) => timeCell(r.last_success_at) },
          { label: "Erro", value: (r) => r.last_error },
        ])), h("a", { href: "#/integrations", class: "small" }, "Ver integrações"));
      }
    } catch (_) { /* opcional */ }

    return [
      h("section", { class: `card hero ${s.overall_status}` },
        h("div", { class: "hero-mark" }, marks[s.overall_status] || "?"),
        h("div", null, h("div", { class: "hero-status" }, labels[s.overall_status] || s.overall_status), h("div", { class: "hero-summary" }, s.summary))),
      kpis,
      jobsCard,
      card("Problemas", h("div", { class: "card-body flush" }, problemsTable(s.problems.slice(0, 12))),
        s.problems.length > 12 ? h("a", { href: "#/problems", class: "small" }, `Ver todos (${s.problems.length})`) : null),
      h("div", { class: "grid cards" }, capabilityCards),
    ];
  }

  async function pageProblems() {
    return card(`${state.system.problems.length} problema(s)`, h("div", { class: "card-body flush" }, problemsTable(state.system.problems)));
  }

  async function pageResources() {
    const rows = await api.get("/api/resources");
    const params = new URLSearchParams((location.hash.split("?")[1]) || "");
    const filters = { q: params.get("q") || "", capability: params.get("capability") || "", status: params.get("status") || "" };
    const tableSlot = h("div", { class: "card-body flush" });

    function apply() {
      const needle = filters.q.toLowerCase();
      const filtered = rows.filter((r) =>
        (!filters.capability || r.capability === filters.capability) &&
        (!filters.status || (filters.status === "stale" ? r.stale : statusClass(r.status, r.stale) === filters.status)) &&
        (!needle || r.resource_id.toLowerCase().includes(needle) || String(r.name || "").toLowerCase().includes(needle)));

      clear(tableSlot).append(dataTable(filtered, [
        { label: "Recurso", value: (r) => r.resource_id },
        { label: "Nome", value: (r) => r.name },
        { label: "Capability", value: (r) => capabilityLabel(r.capability) },
        { label: "Connector", value: (r) => r.connector },
        { label: "Status", render: (r) => badge(r.status, r.stale), sort: (r) => r.status },
        { label: "Atualizado", render: (r) => timeCell(r.timestamp), sort: (r) => -(r.age_seconds || 0) },
      ], { onRowClick: openResource, empty: "Nenhum recurso com esses filtros." }));
    }

    const capabilities = [...new Set(rows.map((r) => r.capability))].sort();

    const toolbar = h("div", { class: "toolbar card-body" },
      h("input", { type: "search", placeholder: "Buscar por ID ou nome", value: filters.q, oninput: (e) => { filters.q = e.target.value; apply(); }, "aria-label": "Buscar" }),
      h("select", { onchange: (e) => { filters.capability = e.target.value; apply(); }, "aria-label": "Capability" },
        h("option", { value: "" }, "Todas as capabilities"),
        capabilities.map((c) => h("option", { value: c, selected: c === filters.capability }, capabilityLabel(c)))),
      h("select", { onchange: (e) => { filters.status = e.target.value; apply(); }, "aria-label": "Status" },
        [["", "Todos os status"], ["ok", "Saudáveis"], ["warn", "Alertas"], ["crit", "Críticos"], ["stale", "Desatualizados"]]
          .map(([value, label]) => h("option", { value, selected: value === filters.status }, label))),
      h("span", { class: "spacer" }),
      h("span", { class: "small muted" }, `${rows.length} recursos`));

    apply();
    return h("section", { class: "card" }, toolbar, tableSlot);
  }

  async function pageCapability(id) {
    const rows = await api.get(`/api/resources?capability=${encodeURIComponent(id)}`);
    const meta = CAPABILITIES[id];
    const columns = (meta ? meta.columns : defaultColumns()).concat([
      { label: "Atualizado", render: (r) => timeCell(r.timestamp), sort: (r) => -(r.age_seconds || 0) },
    ]);
    const capability = state.capabilities.find((c) => c.id === id);

    return [
      capability ? h("div", { class: "muted" }, capability.description) : null,
      h("section", { class: "card" }, h("div", { class: "card-body flush" }, dataTable(rows, columns, { onRowClick: openResource, empty: "Nenhum recurso." }))),
    ];
  }

  async function pageActivity() {
    const params = new URLSearchParams((location.hash.split("?")[1]) || "");
    const hours = Number(params.get("hours") || 24);
    const data = await api.get(`/api/activity?hours=${hours}`);

    const selector = h("select", {
      onchange: (e) => { location.hash = `#/activity?hours=${e.target.value}`; },
      "aria-label": "Período",
    }, [[6, "Últimas 6 horas"], [24, "Últimas 24 horas"], [72, "Últimos 3 dias"], [168, "Últimos 7 dias"]]
      .map(([value, label]) => h("option", { value, selected: value === hours }, label)));

    if (!data.available) {
      return h("div", { class: "notice warn" }, `Histórico indisponível: ${data.reason}. Configure o OpenObserve em Integrações.`);
    }

    return [
      h("div", { class: "toolbar" }, selector, h("span", { class: "muted small" }, "Eventos com severidade de alerta ou maior, vindos do OpenObserve.")),
      data.errors && data.errors.length ? h("div", { class: "notice warn" }, `Algumas consultas falharam: ${data.errors.join(" · ")}`) : null,
      card(`${data.events.length} evento(s)`, h("div", { class: "card-body flush" }, dataTable(data.events, [
        { label: "Quando", render: (r) => timeCell(r.timestamp), sort: (r) => r.timestamp },
        { label: "Severidade", render: (r) => badge(r.severity, false, r.severity), sort: (r) => r.severity },
        { label: "Capability", value: (r) => capabilityLabel(r.capability) },
        { label: "Recurso", value: (r) => r.resource_id },
        { label: "Evento", value: (r) => r.event_type },
        { label: "Mensagem", value: (r) => r.message },
      ], { empty: "Nenhum alerta no período. 🦦" }))),
    ];
  }

  // ---- integrações

  function connectorState(connector) {
    if (!connector.enabled) return { label: "Desativado", cls: "" };
    if (!connector.configured) return { label: "Não configurado", cls: "warn" };
    const jobErrors = connector.jobs.some((job) => job.outcome === "error");
    const componentErrors = connector.components.some((c) => ["error", "disconnected"].includes(c.status));
    if (jobErrors || componentErrors) return { label: "Com falhas", cls: "crit" };
    const waiting = connector.components.some((c) => c.status === "not_configured");
    if (waiting) return { label: "Aguardando MQTT", cls: "warn" };
    return { label: "Ativo", cls: "ok" };
  }

  function settingsForm(group, onSaved) {
    const inputs = [];
    const groups = new Map();

    for (const setting of group.settings) {
      const key = setting.group || "Conexão";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(setting);
    }

    function field(setting) {
      const id = `f-${setting.key}`;
      let input;
      let remove = null;
      const initial = setting.value ?? "";

      if (setting.kind === "bool") {
        input = h("select", { id },
          h("option", { value: "" }, `Padrão${setting.default ? ` (${setting.default === "true" ? "sim" : "não"})` : ""}`),
          h("option", { value: "true", selected: initial === "true" }, "Sim"),
          h("option", { value: "false", selected: initial === "false" }, "Não"));
      } else if (setting.kind === "secret") {
        const fromCredential = setting.source === "credential";
        input = h("input", {
          id, type: "password", autocomplete: "new-password", disabled: fromCredential,
          placeholder: fromCredential ? "Definido por credencial systemd" : setting.is_set ? "•••••• definido (vazio mantém)" : "",
        });
        if (setting.is_set && !fromCredential) {
          remove = h("input", { type: "checkbox" });
        }
      } else {
        input = h("input", {
          id, type: setting.kind === "int" ? "number" : "text", value: initial,
          placeholder: setting.default ? `Padrão: ${setting.default}` : setting.kind === "url" ? "https://…" : "",
        });
      }

      inputs.push({ setting, input, remove, initial });

      return h("div", { class: "field" },
        h("label", { for: id }, setting.label, setting.required ? h("span", { class: "req", title: "Obrigatório" }, "*") : null),
        input,
        remove ? h("label", { class: "small muted row" }, remove, "Remover valor salvo") : null,
        setting.help ? h("div", { class: "help" }, setting.help) : null,
        setting.source === "credential" && setting.kind !== "secret" ? h("div", { class: "help" }, "Definido por credencial systemd (tem precedência).") : null);
    }

    const enabledInput = group.kind === "connector" ? h("input", { type: "checkbox", checked: group.enabled }) : null;

    const body = h("div", { class: "modal-body" },
      h("div", { class: "muted" }, group.description),
      enabledInput ? h("label", { class: "switch" }, enabledInput, "Integração habilitada") : null,
      group.missing.length ? h("div", { class: "notice warn" }, `Campos obrigatórios pendentes: ${group.missing.join(", ")}`) : null,
      [...groups.entries()].map(([name, settings]) => h("fieldset", null, h("legend", null, name), h("div", { class: "fields" }, settings.map(field)))),
      h("div", { class: "small muted" }, "Ao salvar, os serviços do OtterPilot reiniciam sozinhos em alguns segundos para aplicar a configuração."));

    const save = h("button", { class: "btn primary", type: "submit" }, "Salvar");

    const form = h("form", {
      class: "modal",
      onsubmit: async (event) => {
        event.preventDefault();
        const values = {};

        for (const { setting, input, remove, initial } of inputs) {
          if (setting.kind === "secret") {
            if (remove && remove.checked) values[setting.key] = null;
            else if (input.value) values[setting.key] = input.value;
          } else if (input.value.trim() !== String(initial)) {
            values[setting.key] = input.value.trim();
          }
        }

        const enabledChanged = enabledInput && enabledInput.checked !== group.enabled;

        if (!Object.keys(values).length && !enabledChanged) {
          toast("Nenhuma alteração.");
          return;
        }

        save.disabled = true;
        try {
          await api.put(`/api/settings/${group.id}`, { values, enabled: enabledChanged ? enabledInput.checked : null });
          toast("Configuração salva. Os serviços reiniciam em alguns segundos.");
          closeOverlay();
          if (onSaved) onSaved();
        } catch (error) {
          toast(error.message, "error");
        } finally {
          save.disabled = false;
        }
      },
    },
      h("div", { class: "modal-head" }, h("h1", { class: "spacer" }, group.name), h("button", { class: "btn ghost", type: "button", onclick: closeOverlay, "aria-label": "Fechar" }, "✕")),
      body,
      h("div", { class: "modal-foot" }, h("button", { class: "btn", type: "button", onclick: closeOverlay }, "Cancelar"), save));

    return form;
  }

  function testButton(groupId, resultsSlot) {
    const button = h("button", {
      class: "btn",
      onclick: async () => {
        button.disabled = true;
        button.textContent = "Testando…";
        clear(resultsSlot);
        try {
          const { results } = await api.post(`/api/settings/${groupId}/test`);
          append(resultsSlot, results.map((r) => h("div", {
            class: `notice small ${r.ok ? "ok" : r.not_configured ? "warn" : "crit"}`,
          }, `${r.ok ? "✓" : "✕"} ${r.label}: ${r.detail} (${num(r.duration_ms, 0)} ms)`)));
        } catch (error) {
          resultsSlot.append(h("div", { class: "notice crit small" }, error.message));
        } finally {
          button.disabled = false;
          button.textContent = "Testar conexão";
        }
      },
    }, "Testar conexão");
    return button;
  }

  async function pageIntegrations() {
    const [connectors, settings] = await Promise.all([api.get("/api/connectors"), api.get("/api/settings")]);
    const byId = Object.fromEntries(settings.map((group) => [group.id, group]));
    const openForm = (id) => overlay(settingsForm(byId[id], () => render()), true);
    const allComponents = connectors.flatMap((c) => c.components);

    const platform = settings.filter((group) => group.kind === "platform").map((group) => {
      let status;
      if (group.id === "mqtt") {
        const connected = allComponents.filter((c) => c.status === "connected").length;
        status = !group.configured ? { label: "Não configurado", cls: "warn" }
          : connected ? { label: `${connected} componente(s) conectado(s)`, cls: "ok" }
          : { label: "Sem conexão", cls: "crit" };
      } else {
        status = group.configured ? { label: "Configurado", cls: "ok" } : { label: "Opcional · não configurado", cls: "" };
      }

      const results = h("div", { class: "test-results" });

      return h("section", { class: "card" },
        h("div", { class: "card-head" }, h("h2", null, group.name), h("span", { class: `badge ${status.cls}` }, status.label)),
        h("div", { class: "card-body stack" },
          h("div", { class: "muted small" }, group.description),
          group.id === "mqtt" && allComponents.length ? h("div", { class: "chips" }, allComponents.map((c) =>
            h("span", { class: `badge ${statusClass(c.status)}`, title: c.detail || "" }, `${c.component}: ${STATUS_LABEL[c.status] || c.status}`))) : null,
          results),
        h("div", { class: "card-foot" },
          group.configured ? testButton(group.id, results) : null,
          h("button", { class: "btn", onclick: () => openForm(group.id) }, "Configurar")));
    });

    const connectorCards = connectors.filter((c) => !c.internal).map((connector) => {
      const st = connectorState(connector);

      const jobs = connector.jobs.length ? dataTable(connector.jobs, [
        { label: "Coleta", value: (r) => capabilityLabel(r.capability_id) },
        { label: "Resultado", render: (r) => badge(r.outcome) },
        { label: "Última", render: (r) => h("span", { class: "nowrap", title: `A cada ${duration(r.interval_seconds)}` }, ago(r.last_run_at)) },
      ]) : null;

      const errors = connector.jobs.filter((job) => job.last_error && job.outcome !== "ok");
      const results = h("div", { class: "test-results" });

      return h("section", { class: "card" },
        h("div", { class: "card-head" }, h("h2", null, connector.name), h("span", { class: `badge ${st.cls}` }, st.label)),
        h("div", { class: "card-body stack" },
          h("div", { class: "chips" }, connector.capabilities.map((c) => h("span", { class: "chip" }, capabilityLabel(c))),
            h("span", { class: "chip" }, `${connector.resource_count} recurso(s)`)),
          connector.missing.length && connector.enabled ? h("div", { class: "notice warn small" }, `Falta configurar: ${connector.missing.join(", ")}`) : null,
          errors.map((job) => h("div", { class: `notice ${job.outcome === "error" ? "crit" : "warn"} small` }, `${capabilityLabel(job.capability_id)}: ${job.last_error}`)),
          connector.components.map((c) => h("div", { class: "row small" },
            badge(c.status), h("span", null, c.component), h("span", { class: "muted" }, c.last_message_at ? `última mensagem ${ago(c.last_message_at)}` : c.detail || ""))),
          jobs,
          results),
        h("div", { class: "card-foot" },
          connector.configured && connector.enabled ? testButton(connector.id, results) : null,
          h("button", { class: "btn", onclick: () => openForm(connector.id) }, "Configurar")));
    });

    return [
      h("h3", null, "Plataforma"),
      h("div", { class: "grid cards" }, platform),
      h("h3", null, "Integrações"),
      h("div", { class: "grid cards" }, connectorCards),
    ];
  }

  // ---- copilot

  const CHAT_KEY = "otterpilot.chat";

  function loadChat() {
    try { return JSON.parse(sessionStorage.getItem(CHAT_KEY)) || []; } catch (_) { return []; }
  }

  function saveChat(messages) {
    try { sessionStorage.setItem(CHAT_KEY, JSON.stringify(messages.slice(-40))); } catch (_) { /* cheio */ }
  }

  function inline(text) {
    return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map((part) => {
      if (part.startsWith("**") && part.endsWith("**")) return h("strong", null, part.slice(2, -2));
      if (part.startsWith("`") && part.endsWith("`")) return h("code", null, part.slice(1, -1));
      return part;
    });
  }

  function markdown(text) {
    const nodes = [];
    for (const block of String(text).split(/\n{2,}/)) {
      const lines = block.split("\n").filter((line) => line.trim() !== "");
      if (!lines.length) continue;
      if (lines.every((line) => /^\s*([-*]|\d+\.)\s+/.test(line))) {
        nodes.push(h("ul", null, lines.map((line) => h("li", null, inline(line.replace(/^\s*([-*]|\d+\.)\s+/, ""))))));
      } else {
        nodes.push(h("p", null, lines.map((line, index) => [index ? h("br") : null, inline(line.replace(/^#+\s*/, ""))])));
      }
    }
    return nodes;
  }

  function chatMessage(message) {
    if (message.role === "user") return h("div", { class: "msg user" }, message.text);
    return h("div", { class: `msg bot ${message.ok === false ? "error" : ""}` },
      markdown(message.text),
      message.meta ? h("div", { class: "meta" }, message.meta) : null);
  }

  async function pageCopilot() {
    const messages = loadChat();
    const log = h("div", { class: "chat-log", "aria-live": "polite" });
    const input = h("textarea", { rows: 1, placeholder: "Pergunte sobre o seu ambiente…", "aria-label": "Pergunta" });
    const send = h("button", { class: "btn primary", type: "submit" }, "Enviar");

    const suggestions = [
      "O que está com problema agora?",
      "Como estão os hosts do Proxmox?",
      "Algum container com disco ou memória alta?",
      "O DNS está saudável?",
    ];

    function draw() {
      clear(log);
      if (!messages.length) {
        log.append(h("div", { class: "empty stack" },
          h("div", null, "Pergunte qualquer coisa sobre o estado atual e o histórico do homelab."),
          h("div", { class: "suggestions", style: { justifyContent: "center" } },
            suggestions.map((text) => h("button", { class: "btn small", type: "button", onclick: () => ask(text) }, text)))));
      }
      messages.forEach((message) => log.append(chatMessage(message)));
      log.scrollTop = log.scrollHeight;
    }

    async function ask(question) {
      question = question.trim();
      if (!question) return;
      messages.push({ role: "user", text: question });
      saveChat(messages);
      input.value = "";
      draw();
      const typing = h("div", { class: "msg bot" }, h("span", { class: "typing" }, h("span"), h("span"), h("span")));
      log.append(typing);
      log.scrollTop = log.scrollHeight;
      send.disabled = true;

      try {
        const result = await api.post("/api/copilot/query", { question });
        messages.push({
          role: "bot", text: result.answer, ok: result.ok,
          meta: [result.model, result.duration_ms ? `${(result.duration_ms / 1000).toFixed(1)} s` : null].filter(Boolean).join(" · "),
        });
      } catch (error) {
        messages.push({ role: "bot", text: `Falha ao consultar o Copilot: ${error.message}`, ok: false });
      } finally {
        send.disabled = false;
        saveChat(messages);
        draw();
        input.focus();
      }
    }

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        ask(input.value);
      }
    });

    draw();

    return h("section", { class: "card chat" },
      h("div", { class: "card-head" },
        h("div", null, h("h2", null, "Copilot"), h("div", { class: "small muted" }, "Responde com base no State Store (agora) e no OpenObserve (histórico).")),
        h("button", { class: "btn small", type: "button", onclick: () => { messages.length = 0; saveChat(messages); draw(); } }, "Limpar conversa")),
      log,
      h("form", { class: "chat-input", onsubmit: (event) => { event.preventDefault(); ask(input.value); } }, input, send));
  }

  // ---- configurações

  async function pagePolling() {
    const jobs = await api.get("/api/jobs");

    function row(job) {
      const input = h("input", { type: "number", min: 10, max: 86400, value: job.interval_seconds, style: { width: "100px" }, "aria-label": `Intervalo de ${job.job_id}` });

      async function save(value) {
        try {
          await api.put(`/api/jobs/${job.job_id}`, { interval_seconds: value });
          toast("Intervalo salvo. O scheduler reinicia em alguns segundos.");
          render();
        } catch (error) { toast(error.message, "error"); }
      }

      return h("tr", null,
        h("td", null, h("div", null, capabilityLabel(job.capability_id)), h("div", { class: "small muted mono" }, job.job_id)),
        h("td", null, job.connector_id),
        h("td", null, badge(job.enabled ? job.outcome : "disabled")),
        h("td", null, timeCell(job.last_run_at)),
        h("td", { class: "num" }, job.duration_ms == null ? "—" : `${num(job.duration_ms, 0)} ms`),
        h("td", null, h("div", { class: "row" }, input, h("span", { class: "small muted" }, "s"))),
        h("td", { class: "small muted" }, `padrão ${job.default_interval_seconds}s`),
        h("td", null, h("div", { class: "row" },
          h("button", { class: "btn small primary", onclick: () => save(Number(input.value)) }, "Salvar"),
          job.interval_overridden ? h("button", { class: "btn small", onclick: () => save(null) }, "Padrão") : null)));
    }

    return [
      h("div", { class: "muted" }, "Frequência de cada coleta periódica. Zigbee2MQTT e detecções do Frigate chegam por MQTT e não usam polling."),
      card("Coletas periódicas", h("div", { class: "card-body flush table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, ["Coleta", "Connector", "Resultado", "Última execução", "Duração", "Intervalo", "", ""].map((label) => h("th", null, label)))),
        h("tbody", null, jobs.map(row))))),
    ];
  }

  async function pagePolicies() {
    const data = await api.get("/api/policies/virtualization");
    const guests = Object.fromEntries(data.guests.map((g) => [g.resource_id, g]));
    const ids = [...new Set([...Object.keys(data.workloads), ...Object.keys(guests)])]
      .sort((a, b) => Number(a.split("/")[1]) - Number(b.split("/")[1]));
    const removed = new Set();
    const rows = [];

    const tbody = h("tbody", null, ids.map((id) => {
      const guest = guests[id];
      const policy = data.workloads[id] || {};
      const expected = h("select", { "aria-label": `Estado esperado de ${id}` },
        [["", "—"], ["running", "Rodando"], ["stopped", "Parado"]].map(([value, label]) => h("option", { value, selected: (policy.expected_state || "") === value }, label)));
      const importance = h("select", { "aria-label": `Importância de ${id}` },
        [["", "—"], ["critical", "Crítica"], ["warning", "Normal"]].map(([value, label]) => h("option", { value, selected: (policy.importance || "") === value }, label)));

      const tr = h("tr", null,
        h("td", { class: "mono" }, id),
        h("td", null, (guest && guest.name) || policy.name || "—"),
        h("td", null, (guest && guest.node) || "—"),
        h("td", null, guest ? badge(guest.proxmox_status) : h("span", { class: "badge stale" }, "Fora do inventário")),
        h("td", null, expected),
        h("td", null, importance),
        h("td", null, guest ? null : h("button", {
          class: "btn small danger",
          onclick: () => { removed.add(id); tr.remove(); },
          title: "Remover política de um guest que não existe mais",
        }, "Remover")));

      rows.push({ id, guest, policy, expected, importance });
      return tr;
    }));

    const save = h("button", {
      class: "btn primary",
      onclick: async () => {
        const workloads = {};
        for (const row of rows) {
          if (removed.has(row.id)) continue;
          if (!row.expected.value && !row.importance.value) continue;
          workloads[row.id] = {
            name: (row.guest && row.guest.name) || row.policy.name || null,
            expected_state: row.expected.value || null,
            importance: row.importance.value || null,
          };
        }
        save.disabled = true;
        try {
          await api.put("/api/policies/virtualization", { workloads });
          toast("Políticas salvas. O scheduler reinicia em alguns segundos.");
          render();
        } catch (error) { toast(error.message, "error"); }
        finally { save.disabled = false; }
      },
    }, "Salvar políticas");

    return [
      h("div", { class: "muted" },
        "Estado esperado de cada VM/container do Proxmox. Um guest parado que deveria estar rodando vira alerta — ou problema crítico, se a importância for crítica. Guests sem política não geram alertas por estarem parados."),
      card("Virtualização", h("div", { class: "card-body flush table-wrap" }, h("table", null,
        h("thead", null, h("tr", null, ["ID", "Nome", "Nó", "Estado atual", "Esperado", "Importância", ""].map((label) => h("th", null, label)))),
        tbody)), save),
    ];
  }

  async function pageFiles() {
    const files = await api.get("/api/config-files");
    const help = {
      "proxmox.yaml": "Política de workloads do Proxmox (também editável em Políticas).",
      "vehicle.yaml": "Mapeamento das entidades do Home Assistant para a capability de veículo. Sem este arquivo a coleta de veículo fica desativada.",
    };

    return files.map((file) => {
      const editor = h("textarea", { class: "code", spellcheck: "false", "aria-label": file.name }, file.content);
      const error = h("div");
      const save = h("button", {
        class: "btn primary",
        onclick: async () => {
          clear(error);
          save.disabled = true;
          try {
            await api.put(`/api/config-files/${file.name}`, { content: editor.value });
            toast(`${file.name} salvo.`);
          } catch (err) {
            error.append(h("div", { class: "notice crit" }, err.message));
          } finally { save.disabled = false; }
        },
      }, "Salvar");

      return card(file.name, h("div", { class: "card-body stack" },
        h("div", { class: "muted small" }, help[file.name] || ""),
        file.exists ? null : h("div", { class: "notice" }, "Arquivo ainda não existe; ele será criado ao salvar."),
        editor, error), save);
    });
  }

  async function pageSystem() {
    const about = await api.get("/api/about");
    const current = h("input", { type: "password", autocomplete: "current-password", id: "pw-current" });
    const next = h("input", { type: "password", autocomplete: "new-password", id: "pw-new", minlength: 8 });
    const confirm = h("input", { type: "password", autocomplete: "new-password", id: "pw-confirm" });

    const passwordForm = h("form", {
      class: "card-body stack",
      onsubmit: async (event) => {
        event.preventDefault();
        if (next.value !== confirm.value) { toast("As senhas novas não conferem.", "error"); return; }
        try {
          await api.post("/api/auth/password", { current: current.value, new: next.value });
          toast("Senha alterada.");
          event.target.reset();
        } catch (error) { toast(error.message, "error"); }
      },
    },
      h("div", { class: "fields" },
        h("div", { class: "field" }, h("label", { for: "pw-current" }, "Senha atual"), current),
        h("div", { class: "field" }, h("label", { for: "pw-new" }, "Nova senha"), next, h("div", { class: "help" }, "Mínimo de 8 caracteres.")),
        h("div", { class: "field" }, h("label", { for: "pw-confirm" }, "Confirmar nova senha"), confirm)),
      h("div", null, h("button", { class: "btn primary", type: "submit" }, "Alterar senha")));

    return [
      card("Serviços", h("div", { class: "card-body flush" }, dataTable(about.services, [
        { label: "Serviço", value: (r) => r.unit },
        { label: "Estado", render: (r) => badge(r.active_state === "active" ? "running" : r.active_state === "inactive" ? "stopped" : r.active_state, false, `${r.active_state}${r.sub_state ? ` (${r.sub_state})` : ""}`) },
        { label: "Desde", value: (r) => r.since || "—" },
        { label: "Reinícios", value: (r) => r.restarts ?? "—", num: true },
        { label: "Inicialização", value: (r) => r.unit_file_state || "—" },
      ]))),
      card("Sobre", h("div", { class: "card-body" }, h("div", { class: "kv" },
        h("div", null, "versão"), h("div", null, about.version),
        h("div", null, "host"), h("div", null, about.hostname),
        h("div", null, "configuração"), h("div", { class: "mono" }, about.config_root),
        h("div", null, "estado"), h("div", { class: "mono" }, about.state_db)))),
      card("Senha de administrador", passwordForm),
      card("Sessão", h("div", { class: "card-body" }, h("button", {
        class: "btn",
        onclick: async () => { await api.post("/api/auth/logout"); showLogin(); },
      }, "Sair"))),
    ];
  }

  // ------------------------------------------------------------ roteador

  const ROUTES = [
    { pattern: /^#\/?$/, title: "Saúde do sistema", page: pageOverview, refresh: true },
    { pattern: /^#\/problems$/, title: "Problemas", page: pageProblems, refresh: true },
    { pattern: /^#\/resources(\?.*)?$/, title: "Recursos", page: pageResources, refresh: true },
    { pattern: /^#\/capability\/([a-z0-9_]+)$/, title: (m) => capabilityLabel(m[1]), page: (m) => pageCapability(m[1]), refresh: true },
    { pattern: /^#\/activity(\?.*)?$/, title: "Atividade", page: pageActivity },
    { pattern: /^#\/integrations$/, title: "Integrações", page: pageIntegrations, refresh: true },
    { pattern: /^#\/copilot$/, title: "Copilot", page: pageCopilot },
    { pattern: /^#\/settings\/polling$/, title: "Coleta", page: pagePolling },
    { pattern: /^#\/settings\/policies$/, title: "Políticas", page: pagePolicies },
    { pattern: /^#\/settings\/files$/, title: "Arquivos de configuração", page: pageFiles },
    { pattern: /^#\/settings\/system$/, title: "Sistema", page: pageSystem },
  ];

  let renderToken = 0;

  async function render(options) {
    const soft = options && options.soft;
    if (!shell) buildShell();
    const token = ++renderToken;
    const hash = location.hash || "#/";
    const route = ROUTES.find((r) => r.pattern.test(hash)) || ROUTES[0];
    const match = hash.match(route.pattern) || [];

    if (!soft) clear(shell.content).append(h("div", { class: "loading" }, h("div", { class: "spinner" })));

    try {
      await loadShellData();
      if (token !== renderToken) return;
      drawSidebar();
      const title = typeof route.title === "function" ? route.title(match) : route.title;
      setTitle(title, `Atualizado ${state.lastLoad.toLocaleTimeString("pt-BR")}`);
      document.title = `${title} · OtterPilot`;
      const content = await route.page(match);
      if (token !== renderToken) return;
      clear(shell.content);
      append(shell.content, [content]);
    } catch (error) {
      if (error.status === 401) return;
      if (token !== renderToken) return;
      clear(shell.content).append(h("div", { class: "notice crit" }, `Não foi possível carregar: ${error.message}`));
    }

    clearInterval(state.timer);
    if (route.refresh) {
      state.timer = setInterval(() => {
        const busy = document.querySelector(".overlay") ||
          (document.activeElement && ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName));
        if (!busy && !document.hidden) render({ soft: true });
      }, REFRESH_MS);
    }
  }

  // ------------------------------------------------------------ login

  function showLogin(message) {
    clearInterval(state.timer);
    closeOverlay();
    shell = null;

    const password = h("input", { type: "password", id: "login-password", autocomplete: "current-password", required: true });
    const error = h("div");
    const submit = h("button", { class: "btn primary", type: "submit" }, "Entrar");

    clear(root).append(h("div", { class: "login" }, h("form", {
      class: "card",
      onsubmit: async (event) => {
        event.preventDefault();
        clear(error);
        submit.disabled = true;
        try {
          await api.post("/api/auth/login", { password: password.value });
          start();
        } catch (err) {
          error.append(h("div", { class: "notice crit" }, err.message));
          password.select();
        } finally { submit.disabled = false; }
      },
    },
      brand("Observabilidade e copiloto para o seu homelab"),
      message ? h("div", { class: "notice warn" }, message) : null,
      h("div", { class: "field" }, h("label", { for: "login-password" }, "Senha de administrador"), password),
      error,
      submit)));

    password.focus();
  }

  async function start() {
    try {
      const session = await api.get("/api/auth/session");
      if (!session.authenticated) {
        showLogin(session.password_configured ? null : "Nenhuma senha definida. No servidor, execute: sudo otterpilot set-password");
        return;
      }
    } catch (error) {
      clear(root).append(h("div", { class: "login" }, h("div", { class: "notice crit" }, `OtterPilot indisponível: ${error.message}`)));
      return;
    }
    render();
  }

  window.addEventListener("hashchange", () => { if (shell) render(); });
  start();
})();
