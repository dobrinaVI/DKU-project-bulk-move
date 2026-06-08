/* global dataiku */

function backendUrl(path) {
  return dataiku.getWebAppBackendUrl(path);
}

function lines(v) {
  return (v || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function elt(tag, attrs, children) {
  const e = document.createElement(tag);
  if (attrs) Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
  (children || []).forEach((c) =>
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c)
  );
  return e;
}

function addMappingRow(src = "", tgt = "") {
  const row = elt("div", { class: "mappingRow" }, []);
  const srcInput = elt(
    "input",
    { class: "input", placeholder: "SRC_CONN", value: src },
    []
  );
  const tgtInput = elt(
    "input",
    { class: "input", placeholder: "TGT_CONN", value: tgt },
    []
  );
  const delBtn = elt(
    "button",
    { class: "iconBtn", type: "button", title: "Remove mapping" },
    ["×"]
  );
  delBtn.onclick = () => row.remove();
  row.appendChild(srcInput);
  row.appendChild(tgtInput);
  row.appendChild(delBtn);
  document.getElementById("mappings").appendChild(row);
}

function readMappings() {
  const rows = Array.from(document.querySelectorAll("#mappings .mappingRow"));
  const remap = {};
  rows.forEach((r) => {
    const inputs = r.querySelectorAll("input");
    const src = (inputs[0].value || "").trim();
    const tgt = (inputs[1].value || "").trim();
    if (src && tgt) remap[src] = tgt;
  });
  return remap;
}

function addCodeEnvMappingRow(src = "", tgt = "") {
  const row = elt("div", { class: "mappingRow" }, []);
  const srcInput = elt(
    "input",
    { class: "input", placeholder: "SRC_CODE_ENV", value: src },
    []
  );
  const tgtInput = elt(
    "input",
    { class: "input", placeholder: "TGT_CODE_ENV", value: tgt },
    []
  );
  const delBtn = elt(
    "button",
    { class: "iconBtn", type: "button", title: "Remove mapping" },
    ["×"]
  );
  delBtn.onclick = () => row.remove();
  row.appendChild(srcInput);
  row.appendChild(tgtInput);
  row.appendChild(delBtn);
  document.getElementById("codeenvMappings").appendChild(row);
}

function readCodeEnvMappings() {
  const rows = Array.from(
    document.querySelectorAll("#codeenvMappings .mappingRow")
  );
  const remap = {};
  rows.forEach((r) => {
    const inputs = r.querySelectorAll("input");
    const src = (inputs[0].value || "").trim();
    const tgt = (inputs[1].value || "").trim();
    if (src && tgt) remap[src] = tgt;
  });
  return remap;
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function setStatus(line, obj) {
  document.getElementById("statusLine").textContent = line;
  document.getElementById("statusJson").textContent = obj
    ? JSON.stringify(obj, null, 2)
    : "";
  renderResults(obj);
}

function pickProjectError(p) {
  if (!p) return "";
  if (p.error) return String(p.error);
  const ir = p.importResult;
  if (!ir || !Array.isArray(ir.messages)) return "";
  const msgs = ir.messages
    .filter((m) => m && (m.isFatal || m.severity === "ERROR"))
    .map((m) => m.message || m.title || "")
    .filter(Boolean);
  if (msgs.length) return msgs.slice(0, 3).join(" | ");
  return "";
}

function renderResults(st) {
  const summary = document.getElementById("resultSummary");
  const wrap = document.getElementById("resultsTableWrap");

  summary.textContent = "";
  wrap.style.display = "none";
  wrap.innerHTML = "";

  if (!st || !st.result || !st.result.projects) return;

  const projects = st.result.projects || [];
  const ok = projects.filter((p) => p && p.success).length;
  const ko = projects.length - ok;
  summary.textContent = `Projects: ${projects.length} • Success: ${ok} • Failed: ${ko}`;

  const table = elt("table", { class: "table" }, []);
  const thead = elt("thead", null, []);
  const headRow = elt("tr", null, [
    elt("th", null, ["Source"]),
    elt("th", null, ["Target"]),
    elt("th", null, ["Status"]),
    elt("th", null, ["Details"]),
  ]);
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = elt("tbody", null, []);
  projects.forEach((p) => {
    const status = p && p.success ? "OK" : "ERROR";
    const pill = elt(
      "span",
      { class: `pill ${status === "OK" ? "pillOk" : "pillErr"}` },
      [status]
    );
    const details = pickProjectError(p);
    const row = elt("tr", null, [
      elt("td", null, [String((p && p.sourceProjectKey) || "")]),
      elt("td", null, [String((p && p.targetProjectKey) || "")]),
      elt("td", null, [pill]),
      elt("td", null, [details || "—"]),
    ]);
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  wrap.appendChild(table);
  wrap.style.display = "block";
}

async function poll(jobId) {
  const st = await getJson(
    backendUrl("/status?jobId=" + encodeURIComponent(jobId))
  );
  setStatus(`${st.status} (${jobId})`, st);
  if (st.status === "queued" || st.status === "running") {
    setTimeout(() => poll(jobId), 1500);
  }
}

function wire() {
  document.getElementById("addMapping").onclick = () => addMappingRow("", "");
  document.getElementById("addCodeEnvMapping").onclick = () =>
    addCodeEnvMappingRow("", "");

  // Defaults requested: Snowflake + OpenAI
  addMappingRow("SNOWFLAKE_SRC", "SNOWFLAKE_TGT");
  addMappingRow("OPENAI_SRC", "OPENAI_TGT");
  addCodeEnvMappingRow("", "");

  document.getElementById("start").onclick = async () => {
    try {
      setStatus("Starting…");
      const payload = {
        source: { host: (srcHost.value || "").trim(), apiKey: srcKey.value || "" },
        target: { host: (tgtHost.value || "").trim(), apiKey: tgtKey.value || "" },
        projects: lines(projects.value),
        connectionRemap: readMappings(),
        codeEnvRemap: readCodeEnvMappings(),
        options: {
          exportUploads: false,
          exportManagedFS: false,
          exportSavedModels: true,
          exportAnalysisModels: true,
        },
        targetKeyPrefix: "",
      };
      const resp = await postJson(backendUrl("/start"), payload);
      setStatus(`queued (${resp.jobId})`, resp);
      poll(resp.jobId);
    } catch (e) {
      setStatus("error", { error: String(e) });
    }
  };
}

wire();
