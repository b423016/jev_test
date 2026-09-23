const STEPS = [
  ["hash", "Hash"],
  ["split", "Split"],
  ["jev", "Jev"],
  ["playbook", "Playbook"],
  ["explain", "Explain"],
  ["draft", "Draft"],
];

const form = document.querySelector("#scan");
const fileInput = document.querySelector("#file");
const fileLabel = document.querySelector("#file-label");
const drop = document.querySelector("#drop");
const textInput = document.querySelector("#text");
const statusLine = document.querySelector("#status");
const result = document.querySelector("#result");
const doc = document.querySelector("#doc");
const rail = document.querySelector("#rail");
const draft = document.querySelector("#draft");
const reminderBox = document.querySelector("#reminder");
const reminderBody = document.querySelector("#reminder-body");
const tape = document.querySelector("#tape");
const go = document.querySelector("#go");

document.querySelector("#host").textContent = window.location.host;

drawTape();

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0] ? fileInput.files[0].name : "Drop a PDF or text file, or choose one";
});

["dragover", "dragenter"].forEach((name) => {
  drop.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.add("over");
  });
});
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  if (event.dataTransfer.files[0]) {
    fileInput.files = event.dataTransfer.files;
    fileLabel.textContent = event.dataTransfer.files[0].name;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusLine.className = "status";
  result.hidden = true;
  drawTape();

  const door = form.querySelector("input[name=door]:checked").value;
  const file = fileInput.files[0];
  const pasted = textInput.value;
  if (Boolean(file) === Boolean(pasted.trim())) {
    fail("Paste the text or upload one file.");
    return;
  }

  go.disabled = true;
  mark("hash", "run", "Hashing in the browser.");
  let bytes;
  if (file) bytes = new Uint8Array(await file.arrayBuffer());
  else bytes = new TextEncoder().encode(pasted);
  const sha256 = await sha256Hex(bytes);
  mark("hash", "run", sha256.slice(0, 16));

  const body = new FormData();
  body.set("document_type", door);
  body.set("sha256", sha256);
  if (file) body.set("file", file);
  else body.set("text", pasted);

  let response;
  try {
    response = await fetch("/scans/stream", { method: "POST", body });
  } catch {
    mark("hash", "fail", "No server.");
    fail("The server did not answer.");
    go.disabled = false;
    return;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || "The scan failed.";
    if (response.status === 400 && String(detail).toLowerCase().includes("hash")) {
      mark("hash", "fail", "Rejected.");
    } else {
      mark("hash", "done", "Accepted.");
    }
    fail(detail);
    go.disabled = false;
    return;
  }

  await readStream(response);
  go.disabled = false;
});

document.querySelector("#copy-draft").addEventListener("click", () => copy(draft.textContent));
document.querySelector("#copy-reminder").addEventListener("click", () => copy(reminderBody.textContent));

function drawTape() {
  tape.replaceChildren();
  for (const [id, name] of STEPS) {
    const item = document.createElement("li");
    item.id = `step-${id}`;
    item.className = "wait";
    const dot = document.createElement("span");
    dot.className = "dot";
    const text = document.createElement("span");
    const title = document.createElement("span");
    title.className = "step-name";
    title.textContent = name;
    const detail = document.createElement("span");
    detail.className = "step-detail";
    detail.textContent = "Waiting";
    text.append(title, detail);
    item.append(dot, text);
    tape.appendChild(item);
  }
}

function mark(id, state, detail) {
  const item = document.querySelector(`#step-${id}`);
  if (!item) return;
  item.className = state;
  item.querySelector(".step-detail").textContent = detail || state;
}

async function readStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop();
    for (const chunk of chunks) applyEvent(chunk);
  }
  if (buffer.trim()) applyEvent(buffer);
}

function applyEvent(chunk) {
  let event = "message";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;
  const payload = JSON.parse(data);
  if (event === "step") mark(payload.id, payload.state, payload.detail);
  if (event === "result") {
    render(payload);
    statusLine.textContent = payload.status === "partial"
      ? "Scores are in. Explanations did not come back."
      : "The tape finished on the bytes you sent.";
  }
  if (event === "error") {
    fail(payload.message || "The scan failed.");
  }
}

function render(payload) {
  doc.replaceChildren();
  rail.replaceChildren();
  for (const finding of payload.findings) {
    const paragraph = document.createElement("p");
    paragraph.className = finding.lit ? "para lit" : "para dim";
    paragraph.textContent = finding.text;
    doc.appendChild(paragraph);
    if (!finding.lit) continue;
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = label(finding.clause_type);
    item.appendChild(title);
    if (finding.score !== null) {
      const score = document.createElement("div");
      score.className = "score";
      score.textContent = `${Math.round(finding.score * 100)}%`;
      item.appendChild(score);
    }
    if (finding.explanation) item.appendChild(line(finding.explanation));
    if (finding.figure) item.appendChild(line(finding.figure));
    if (finding.question) item.appendChild(line(finding.question));
    rail.appendChild(item);
  }
  draft.textContent = payload.draft || "No questions on the lit sentences.";
  if (payload.reminder) {
    reminderBox.hidden = false;
    reminderBody.textContent = `${payload.reminder.title}\n${payload.reminder.date}\n${payload.reminder.details}`;
  } else {
    reminderBox.hidden = true;
  }
  if (payload.mismatch) {
    statusLine.textContent = `This reads more like a ${payload.detected_type}. The scores below use the door you picked.`;
  }
  result.hidden = false;
}

function line(value) {
  const node = document.createElement("div");
  node.textContent = value;
  return node;
}

function label(clause) {
  return clause.replaceAll("_", " ");
}

function fail(message) {
  statusLine.className = "status error";
  statusLine.textContent = message;
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function copy(value) {
  try {
    await navigator.clipboard.writeText(value);
  } catch {
    fail("Could not copy from this page.");
  }
}
