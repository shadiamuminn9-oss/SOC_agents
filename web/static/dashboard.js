const AGENT_ORDER = ["Mon", "Searcher", "Scribe"];

const els = {
  runBtn: document.getElementById("runBtn"),
  sysDot: document.getElementById("sysDot"),
  sysText: document.getElementById("sysText"),
  clock: document.getElementById("clock"),
  feed: document.getElementById("feed"),
  feedCount: document.getElementById("feedCount"),
  report: document.getElementById("report"),
  alertCount: document.getElementById("alertCount"),
  connector1: document.getElementById("connector-1"),
  connector2: document.getElementById("connector-2"),
};

let feedEventCount = 0;
let alertCount = 0;
let feedStarted = false;

function tickClock() {
  const now = new Date();
  els.clock.textContent = now.toLocaleTimeString("en-US", { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

function setNodeStatus(agent, status) {
  const statusEl = document.getElementById(`status-${agent}`);
  const nodeEl = document.getElementById(`node-${agent}`);
  if (!statusEl || !nodeEl) return;

  statusEl.classList.remove("idle", "running", "done");
  nodeEl.classList.remove("active", "complete");
  statusEl.classList.add(status);
  statusEl.textContent = status.toUpperCase();

  if (status === "running") nodeEl.classList.add("active");
  if (status === "done") nodeEl.classList.add("complete");

  updateConnectors();
}

function updateConnectors() {
  const monDone = document.getElementById("status-Mon").classList.contains("done");
  const searcherRunning = document.getElementById("status-Searcher").classList.contains("running");
  const searcherDone = document.getElementById("status-Searcher").classList.contains("done");
  const scribeRunning = document.getElementById("status-Scribe").classList.contains("running");

  els.connector1.classList.toggle("live", searcherRunning || (monDone && !searcherDone));
  els.connector2.classList.toggle("live", scribeRunning);
}

function setSystemStatus(status) {
  els.sysDot.classList.remove("idle", "running", "done");
  els.sysDot.classList.add(status);
  const labels = { idle: "SYSTEM IDLE", running: "SCAN IN PROGRESS", done: "SCAN COMPLETE" };
  els.sysText.textContent = labels[status] || status.toUpperCase();
}

function appendFeedLine(evt) {
  if (!feedStarted) {
    els.feed.innerHTML = "";
    feedStarted = true;
  }
  const line = document.createElement("div");
  line.className = `feed-line ${evt.level || "info"}`;
  line.innerHTML = `
    <span class="feed-ts">${evt.ts || ""}</span>
    <span class="feed-tag">${evt.agent || "SYSTEM"}</span>
    <span class="feed-text"></span>
  `;
  line.querySelector(".feed-text").textContent = evt.text || "";
  els.feed.appendChild(line);
  els.feed.scrollTop = els.feed.scrollHeight;

  feedEventCount += 1;
  els.feedCount.textContent = `${feedEventCount} event${feedEventCount === 1 ? "" : "s"}`;
}

function colorizeSeverity(container) {
  container.querySelectorAll("td").forEach((td) => {
    const t = td.textContent.trim().toLowerCase();
    if (t === "critical") td.classList.add("sev-critical");
    else if (t === "high") td.classList.add("sev-high");
    else if (t === "medium") td.classList.add("sev-medium");
    else if (t === "low") td.classList.add("sev-low");
  });
}

function renderReport(markdown) {
  els.report.innerHTML = marked.parse(markdown);
  colorizeSeverity(els.report);
}

function handleEvent(evt) {
  switch (evt.type) {
    case "run_started":
      setSystemStatus("running");
      feedStarted = false;
      feedEventCount = 0;
      alertCount = 0;
      els.feedCount.textContent = "0 events";
      els.alertCount.textContent = "0 findings";
      els.report.innerHTML = '<div class="report-empty">Scan in progress, the Reporter agent will fill this in once the team finishes...</div>';
      AGENT_ORDER.forEach((a) => setNodeStatus(a, "idle"));
      break;

    case "agent_status":
      setNodeStatus(evt.agent, evt.status);
      break;

    case "log":
      appendFeedLine(evt);
      break;

    case "alert":
      alertCount += 1;
      els.alertCount.textContent = `${alertCount} finding${alertCount === 1 ? "" : "s"}`;
      break;

    case "run_completed":
      setSystemStatus("done");
      renderReport(evt.report);
      els.runBtn.disabled = false;
      els.runBtn.textContent = "RUN SCAN AGAIN";
      { const ul = document.getElementById("uploadLabel"); if (ul) ul.textContent = "UPLOAD LOG"; }
      break;

    case "run_failed":
      setSystemStatus("idle");
      AGENT_ORDER.forEach((a) => {
        const statusEl = document.getElementById(`status-${a}`);
        if (statusEl && statusEl.classList.contains("running")) setNodeStatus(a, "idle");
      });
      els.report.innerHTML = `<div class="report-empty">Run failed: ${evt.error}</div>`;
      els.runBtn.disabled = false;
      els.runBtn.textContent = "RUN SCAN";
      { const ul = document.getElementById("uploadLabel"); if (ul) ul.textContent = "UPLOAD LOG"; }
      break;

    default:
      break;
  }
}

function connectStream() {
  const source = new EventSource("/api/events");
  source.onmessage = (e) => {
    try {
      handleEvent(JSON.parse(e.data));
    } catch (err) {
      console.error("bad event", err, e.data);
    }
  };
  source.onerror = () => {
    // browser auto-retries EventSource connections, nothing to do here
  };
}

async function loadInitialStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    AGENT_ORDER.forEach((a) => setNodeStatus(a, data.agents[a] || "idle"));
    if (data.running) {
      setSystemStatus("running");
      els.runBtn.disabled = true;
      els.runBtn.textContent = "SCAN RUNNING...";
    } else if (data.report) {
      setSystemStatus("done");
      renderReport(data.report);
      els.runBtn.textContent = "RUN SCAN AGAIN";
    }
  } catch (err) {
    console.error("failed to load status", err);
  }
}

els.runBtn.addEventListener("click", async () => {
  els.runBtn.disabled = true;
  els.runBtn.textContent = "SCAN RUNNING...";
  try {
    const res = await fetch("/api/run", { method: "POST" });
    const data = await res.json();
    if (!data.ok) {
      els.runBtn.disabled = false;
      els.runBtn.textContent = "RUN SCAN";
      alert(data.error || "Could not start scan");
    }
  } catch (err) {
    els.runBtn.disabled = false;
    els.runBtn.textContent = "RUN SCAN";
    alert("Could not reach the server");
  }
});

// ---------- upload ----------

async function uploadLog(file) {
  if (state && state.running) { alert("A scan is already running"); return; }
  const label = document.getElementById("uploadLabel");
  if (label) label.textContent = "UPLOADING...";
  els.runBtn.disabled = true;
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || "Upload failed");
      els.runBtn.disabled = false;
      if (label) label.textContent = "UPLOAD LOG";
    } else {
      if (label) label.textContent = `ANALYZING: ${data.filename}`;
    }
  } catch (err) {
    alert("Upload failed");
    els.runBtn.disabled = false;
    if (label) label.textContent = "UPLOAD LOG";
  }
}

const uploadInput = document.getElementById("uploadInput");
if (uploadInput) {
  uploadInput.addEventListener("change", (e) => {
    if (e.target.files[0]) uploadLog(e.target.files[0]);
  });
}

const dropOverlay = document.getElementById("dropOverlay");

document.addEventListener("dragover", (e) => {
  e.preventDefault();
  if (dropOverlay) dropOverlay.classList.add("active");
});

document.addEventListener("dragleave", (e) => {
  if (e.relatedTarget === null && dropOverlay) dropOverlay.classList.remove("active");
});

document.addEventListener("drop", (e) => {
  e.preventDefault();
  if (dropOverlay) dropOverlay.classList.remove("active");
  const file = e.dataTransfer?.files[0];
  if (file) uploadLog(file);
});

connectStream();
loadInitialStatus();

// ---------- boot sequence ----------

const BOOT_TEXT = [
  "INITIALIZING SOC CENTRAL v1.0...",
  "LOADING AGENT PROFILES: MON / SEARCHER / SCRIBE...",
  "ESTABLISHING SECURE CHANNEL...",
  "THREAT FEED SYNCED...",
  "ACCESS GRANTED.",
];

function runBootSequence() {
  const overlay = document.getElementById("bootOverlay");
  const linesEl = document.getElementById("bootLines");
  if (!overlay || !linesEl) return;

  let lineIndex = 0;
  let charIndex = 0;
  let rendered = "";

  function typeNext() {
    if (lineIndex >= BOOT_TEXT.length) {
      setTimeout(() => overlay.classList.add("hidden"), 350);
      return;
    }
    const line = BOOT_TEXT[lineIndex];
    if (charIndex <= line.length) {
      linesEl.innerHTML = rendered + line.slice(0, charIndex) + '<span class="cursor"></span>';
      charIndex += 1;
      setTimeout(typeNext, 14);
    } else {
      rendered += line + "\n";
      lineIndex += 1;
      charIndex = 0;
      setTimeout(typeNext, 120);
    }
  }
  typeNext();
}

runBootSequence();

// ---------- matrix rain background ----------

function initMatrixRain() {
  const canvas = document.getElementById("matrixRain");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const chars = "アイウエオカキクケコ0123456789ABCDEF";
  let columns, drops;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    columns = Math.floor(canvas.width / 16);
    drops = new Array(columns).fill(1);
  }
  resize();
  window.addEventListener("resize", resize);

  function draw() {
    ctx.fillStyle = "rgba(4, 6, 10, 0.08)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#1affc9";
    ctx.font = "14px monospace";
    for (let i = 0; i < drops.length; i++) {
      const text = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillText(text, i * 16, drops[i] * 16);
      if (drops[i] * 16 > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }
      drops[i]++;
    }
  }
  setInterval(draw, 60);
}

initMatrixRain();
