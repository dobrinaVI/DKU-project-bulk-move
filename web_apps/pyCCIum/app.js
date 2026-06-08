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

  // Defaults requested: Snowflake + OpenAI
  addMappingRow("SNOWFLAKE_SRC", "SNOWFLAKE_TGT");
  addMappingRow("OPENAI_SRC", "OPENAI_TGT");

  document.getElementById("start").onclick = async () => {
    try {
      setStatus("Starting…");
      const payload = {
        source: { host: (srcHost.value || "").trim(), apiKey: srcKey.value || "" },
        target: { host: (tgtHost.value || "").trim(), apiKey: tgtKey.value || "" },
        projects: lines(projects.value),
        connectionRemap: readMappings(),
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

