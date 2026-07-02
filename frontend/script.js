/* ===========================
   NeuroRank AI — JavaScript
   =========================== */

const API_BASE = "";

// ─── DOM Refs ───────────────────────────────────────
const jobText       = document.getElementById("jobText");
const jobFile       = document.getElementById("jobFile");
const resumeFiles   = document.getElementById("resumeFiles");
const uploadJobBtn  = document.getElementById("uploadJobBtn");
const uploadResumesBtn = document.getElementById("uploadResumesBtn");
const rankBtn       = document.getElementById("rankBtn");
const rankBtnText   = document.getElementById("rankBtnText");
const downloadCsvBtn = document.getElementById("downloadCsvBtn");
const resetBtn      = document.getElementById("resetBtn");
const jobStatus     = document.getElementById("jobStatus");
const resumeStatus  = document.getElementById("resumeStatus");
const rankStatus    = document.getElementById("rankStatus");
const resumeQueue   = document.getElementById("resumeQueue");
const resultsBody   = document.getElementById("resultsBody");
const rankProgress  = document.getElementById("rankProgress");
const progressBar   = document.getElementById("progressBar");
const progressMsg   = document.getElementById("progressMsg");
const emptyState    = document.getElementById("emptyState");
const cardsView     = document.getElementById("cardsView");
const tableView     = document.getElementById("tableView");
const podiumSection = document.getElementById("podiumSection");
const podium        = document.getElementById("podium");
const candidatesGrid = document.getElementById("candidatesGrid");
const resultsSubtitle = document.getElementById("resultsSubtitle");
const modalBackdrop = document.getElementById("modalBackdrop");
const candidateModal = document.getElementById("candidateModal");
const modalContent  = document.getElementById("modalContent");
const toastContainer = document.getElementById("toastContainer");

let currentResults  = [];
let progressTimer   = null;

// ─── Toast Notifications ─────────────────────────────
function showToast(message, type = "info", duration = 4000) {
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<div class="toast-icon">${icons[type] || "ℹ"}</div><div class="toast-msg">${escapeHtml(message)}</div>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "toastOut 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards";
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// ─── Utilities ────────────────────────────────────────
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function setStatus(el, msg, type = "") {
  if (!el) return;
  el.textContent = msg;
  el.className = `status-banner ${type}`.trim();
}

function scoreClass(val) {
  if (val >= 75) return "score-high";
  if (val >= 50) return "score-mid";
  return "score-low";
}

function rankBadgeClass(rank) {
  if (rank === 1) return "rb-1";
  if (rank === 2) return "rb-2";
  if (rank === 3) return "rb-3";
  return "rb-n";
}

function getInitials(name) {
  const parts = String(name).trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function renderSkillTags(items, cls, maxShow = 3) {
  if (!items || !items.length) return '<span style="color:var(--t4);font-size:0.75rem">—</span>';
  const visible = items.slice(0, maxShow);
  const extra = items.length - maxShow;
  let html = visible.map(s => `<span class="skill-tag ${cls}">${escapeHtml(s)}</span>`).join("");
  if (extra > 0) html += `<span class="skill-tag sk-more">+${extra}</span>`;
  return `<div class="skill-tags-row">${html}</div>`;
}

// ─── Step State & Navigation ──────────────────────────
function markStepDone(stepNum) {
  // Track Numbers
  const trackNum = document.getElementById(`trackNum${stepNum}`);
  if (trackNum) {
    trackNum.classList.add("done");
    trackNum.classList.remove("active");
    trackNum.innerHTML = `<svg viewBox="0 0 20 20" fill="none" style="width:20px;height:20px"><path d="M4 10l4 4 8-8" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }
  
  // Track Line
  const trackLine = document.getElementById(`trackLine${stepNum}`);
  if (trackLine) trackLine.style.background = "var(--emerald)";
  
  // Activate next step
  if (stepNum < 3) {
    const nextTrack = document.getElementById(`trackNum${stepNum + 1}`);
    if (nextTrack) nextTrack.classList.add("active");
  }

  // Panel Badge
  const badge = document.getElementById(stepNum === 1 ? "jobBadge" : "resumeBadge");
  if (badge) {
    badge.classList.add("done");
    badge.innerHTML = `<span class="badge-dot"></span>Completed`;
  }
  
  // Nav Pills
  const pills = ["pillarJob", "pillarResumes", "pillarRank"];
  const currentPill = document.getElementById(pills[stepNum-1]);
  if (currentPill) {
    currentPill.classList.remove("active");
    currentPill.classList.add("done");
  }
  if (stepNum < 3) {
    const nextPill = document.getElementById(pills[stepNum]);
    if (nextPill) nextPill.classList.add("active");
  }
}

// ─── Char Counter ─────────────────────────────────────
if (jobText) {
  jobText.addEventListener("input", () => {
    const len = jobText.value.length;
    const cc = document.getElementById("charCount");
    if (cc) cc.textContent = `${len.toLocaleString()} character${len !== 1 ? "s" : ""}`;
  });
}

// ─── Drop Zones ───────────────────────────────────────
function setupDropzone(dropzoneId, inputId, onFiles) {
  const zone = document.getElementById(dropzoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
  });
  input.addEventListener("change", () => { if (input.files.length) onFiles(input.files); });
}

setupDropzone("jobDropzone", "jobFile", (files) => {
  const file = files[0];
  const info = document.getElementById("jobFileBadge");
  if (info) info.innerHTML = `✓ ${escapeHtml(file.name)} <span style="opacity:0.6;font-weight:400">(${(file.size / 1024).toFixed(1)} KB)</span>`;
});

setupDropzone("resumeDropzone", "resumeFiles", (files) => {
  const arr = Array.from(files);
  resumeQueue.innerHTML = arr.map(f =>
    `<div class="resume-chip">
      <svg viewBox="0 0 24 24" fill="none"><path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" stroke="currentColor" stroke-width="1.5"/></svg>
      ${escapeHtml(f.name)}
    </div>`
  ).join("");
});

// ─── Upload Job ────────────────────────────────────────
async function uploadJob() {
  const text = jobText.value.trim();
  const file = jobFile.files[0];
  if (!text && !file) {
    showToast("Please provide a job description text or PDF.", "error");
    setStatus(jobStatus, "Please provide text or a PDF file.", "error");
    return;
  }

  const formData = new FormData();
  if (text) formData.append("job_text", text);
  if (file) formData.append("job_file", file);

  uploadJobBtn.disabled = true;
  uploadJobBtn.innerHTML = `<span class="btn-icon"><svg class="spin" viewBox="0 0 24 24" fill="none"><path d="M12 4V2M12 22v-2M4 12H2M22 12h-2M17.657 6.343l1.414-1.414M4.93 19.07l1.414-1.414M17.657 17.657l1.414 1.414M4.93 4.93l1.414 1.414" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span><span class="btn-label">Uploading...</span>`;
  setStatus(jobStatus, "Uploading job description...", "info");

  try {
    const res = await fetch(`${API_BASE}/upload-job`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed.");
    setStatus(jobStatus, `✓ ${data.message}`, "success");
    markStepDone(1);
    showToast("Job description uploaded successfully!", "success");
  } catch (err) {
    setStatus(jobStatus, err.message, "error");
    showToast(err.message, "error");
  } finally {
    uploadJobBtn.disabled = false;
    uploadJobBtn.innerHTML = `<span class="btn-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M10 2v11M5 7l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 15v1a2 2 0 002 2h10a2 2 0 002-2v-1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span><span class="btn-label">Upload Job Description</span><span class="btn-shine"></span>`;
  }
}

// ─── Upload Resumes ────────────────────────────────────
async function uploadResumes() {
  const files = Array.from(resumeFiles.files || []);
  if (!files.length) {
    showToast("Please select at least one resume PDF or JSON file.", "error");
    setStatus(resumeStatus, "Select at least one PDF or JSON file.", "error");
    return;
  }

  const invalidFiles = files.filter(f => !/\.(pdf|json)$/i.test(f.name));
  if (invalidFiles.length) {
    const names = invalidFiles.map(f => f.name).join(", ");
    showToast("Only PDF and JSON resume files are supported.", "error");
    setStatus(resumeStatus, `Unsupported file type: ${names}`, "error");
    return;
  }

  const formData = new FormData();
  files.forEach(f => formData.append("resume_files", f));

  uploadResumesBtn.disabled = true;
  uploadResumesBtn.innerHTML = `<span class="btn-icon"><svg class="spin" viewBox="0 0 24 24" fill="none"><path d="M12 4V2M12 22v-2M4 12H2M22 12h-2M17.657 6.343l1.414-1.414M4.93 19.07l1.414-1.414M17.657 17.657l1.414 1.414M4.93 4.93l1.414 1.414" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span><span class="btn-label">Parsing Resumes with AI...</span>`;
  setStatus(resumeStatus, `Parsing ${files.length} resume file(s)...`, "info");

  try {
    const res = await fetch(`${API_BASE}/upload-resumes`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed.");
    setStatus(resumeStatus, `✓ ${data.message}`, "success");
    markStepDone(2);

    if (data.candidates && data.candidates.length) {
      resumeQueue.innerHTML = data.candidates.map(c =>
        `<div class="resume-chip parsed">
          <svg viewBox="0 0 20 20" fill="none"><path d="M16 5L7.5 14 4 10.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          ${escapeHtml(c.name)} <span style="opacity:0.6;font-size:0.65rem">· ${escapeHtml(c.filename)}</span>
        </div>`
      ).join("");
    }
    showToast(`${data.count} resume(s) parsed successfully!`, "success");
  } catch (err) {
    setStatus(resumeStatus, err.message, "error");
    showToast(err.message, "error");
  } finally {
    uploadResumesBtn.disabled = false;
    uploadResumesBtn.innerHTML = `<span class="btn-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M3 7l7-5 7 5v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7z" stroke="currentColor" stroke-width="1.5"/><path d="M8 18V12h4v6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></span><span class="btn-label">Parse All Resumes with AI</span><span class="btn-shine"></span>`;
  }
}

// ─── Progress Simulation ───────────────────────────────
const progressSteps = [
  { pct: 15, msg: "Initializing neural embedding engine (all-MiniLM-L6-v2)...", pipeIdx: 1 },
  { pct: 40, msg: "Executing FAISS vector search across candidate embeddings...", pipeIdx: 2 },
  { pct: 65, msg: "Evaluating profiles via Groq Llama 3.3 70B...", pipeIdx: 3 },
  { pct: 85, msg: "Synthesizing match scores and reasoning...", pipeIdx: 4 },
  { pct: 95, msg: "Finalizing ranking metrics...", pipeIdx: 4 },
];

function startProgress() {
  rankProgress.classList.remove("hidden");
  progressBar.style.width = "5%";
  
  // reset pipes
  document.querySelectorAll(".pipe-step").forEach(el => { el.classList.remove("active", "done"); });
  document.querySelectorAll(".pipe-connector").forEach(el => { el.classList.remove("active", "done"); });
  document.getElementById("pipe1").classList.add("active");

  let i = 0;
  progressTimer = setInterval(() => {
    if (i >= progressSteps.length) { clearInterval(progressTimer); return; }
    const step = progressSteps[i];
    progressBar.style.width = step.pct + "%";
    progressMsg.textContent = step.msg;
    
    // Update pipe visuals
    for (let j = 1; j <= 4; j++) {
      const p = document.getElementById(`pipe${j}`);
      const conn = document.getElementById(`pconn${j}`);
      if (j < step.pipeIdx) {
        if (p) p.className = "pipe-step done";
        if (conn) conn.className = "pipe-connector done";
      } else if (j === step.pipeIdx) {
        if (p) p.className = "pipe-step active";
        if (conn && j > 1) {
          const prevConn = document.getElementById(`pconn${j-1}`);
          if (prevConn) prevConn.className = "pipe-connector active";
        }
      } else {
        if (p) p.className = "pipe-step";
        if (conn) conn.className = "pipe-connector";
      }
    }
    
    i++;
  }, 1800);
}

function stopProgress(success = true) {
  clearInterval(progressTimer);
  progressBar.style.width = success ? "100%" : progressBar.style.width;
  if (!success) progressBar.style.background = "var(--rose)";
  
  if (success) {
    document.querySelectorAll(".pipe-step").forEach(el => el.className = "pipe-step done");
    document.querySelectorAll(".pipe-connector").forEach(el => el.className = "pipe-connector done");
  }
  
  setTimeout(() => rankProgress.classList.add("hidden"), 1200);
}

// ─── Rank Candidates ──────────────────────────────────
async function rankCandidates() {
  rankBtn.disabled = true;
  rankBtnText.textContent = "Analyzing with AI...";
  downloadCsvBtn.disabled = true;
  setStatus(rankStatus, "Running semantic search and Groq evaluation...", "info");
  startProgress();

  try {
    const res = await fetch(`${API_BASE}/rank`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Ranking failed.");
    stopProgress(true);
    currentResults = data.results || [];
    renderResults(currentResults);
    setStatus(rankStatus, `✓ ${data.total_candidates} candidate(s) ranked successfully!`, "success");
    downloadCsvBtn.disabled = false;
    showToast(`Ranking complete! ${data.total_candidates} candidates evaluated.`, "success");
    markStepDone(3);
    document.getElementById("resultsSection").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    stopProgress(false);
    setStatus(rankStatus, err.message, "error");
    showToast(err.message, "error");
  } finally {
    rankBtn.disabled = false;
    rankBtnText.textContent = "Analyze & Rank Candidates";
  }
}

// ─── View Toggles ─────────────────────────────────────
function setView(view) {
  document.getElementById("toggleCards").classList.toggle("active", view === "cards");
  document.getElementById("toggleTable").classList.toggle("active", view === "table");
  
  if (view === "cards") {
    cardsView.classList.remove("hidden");
    tableView.classList.add("hidden");
  } else {
    cardsView.classList.add("hidden");
    tableView.classList.remove("hidden");
  }
}

// Default view
setView("cards");

// ─── Render Results ───────────────────────────────────
function renderResults(results) {
  if (!results || !results.length) {
    emptyState.classList.remove("hidden");
    cardsView.classList.add("hidden");
    tableView.classList.add("hidden");
    resultsSubtitle.textContent = "No results available.";
    downloadCsvBtn.disabled = true;
    return;
  }

  emptyState.classList.add("hidden");
  const isCards = document.getElementById("toggleCards").classList.contains("active");
  if (isCards) cardsView.classList.remove("hidden");
  else tableView.classList.remove("hidden");
  
  resultsSubtitle.textContent = `${results.length} candidate${results.length > 1 ? "s" : ""} evaluated with neural precision`;

  // Render Podium (top 3)
  renderPodium(results.slice(0, 3));
  
  // Render Candidates Grid (all)
  renderCandidatesGrid(results);

  // Render Table
  resultsBody.innerHTML = results.map((item, idx) => {
    const finalScore = `<span class="score-pill ${scoreClass(item.final_score)}">${item.final_score}</span>`;
    const simScore   = `<span class="score-pill ${scoreClass(item.similarity_score)}">${item.similarity_score}%</span>`;
    const aiScore    = `<span class="score-pill ${scoreClass(item.ai_match_score)}">${item.ai_match_score}</span>`;
    const badge = `<span class="rank-badge ${rankBadgeClass(item.rank)}">${item.rank}</span>`;
    
    return `
      <tr onclick="openModal(${idx})">
        <td>${badge}</td>
        <td class="td-name">
          <strong>${escapeHtml(item.candidate_name)}</strong>
          <small>${escapeHtml(item.filename || "")}</small>
        </td>
        <td>${simScore}</td>
        <td>${aiScore}</td>
        <td>${finalScore}</td>
        <td>${renderSkillTags(item.key_matching_skills, "sk-match", 2)}</td>
        <td>${renderSkillTags(item.missing_skills, "sk-miss", 2)}</td>
        <td><div class="rec-cell">${escapeHtml((item.recommendation || "").slice(0, 80))}...</div></td>
      </tr>
    `;
  }).join("");
}

// ─── Podium ───────────────────────────────────────────
const medals = ["🏆", "🥈", "🥉"];

function renderPodium(top) {
  if (!top || !top.length) { podiumSection.classList.add("hidden"); return; }
  podiumSection.classList.remove("hidden");

  // Reorder for visual center: 2nd, 1st, 3rd
  const order = top.length === 1 ? [top[0]] : top.length === 2 ? [top[1], top[0]] : [top[1], top[0], top[2]];

  podium.innerHTML = order.map(item => {
    const cls = `rank-${item.rank}`;
    const skills = (item.key_matching_skills || []).slice(0, 4)
      .map(s => `<span class="mini-tag">${escapeHtml(s)}</span>`).join("");

    return `
      <div class="podium-card ${cls}" onclick="openModal(${item.rank - 1})">
        <div class="podium-rank-badge">#${item.rank}</div>
        <span class="podium-medal">${medals[item.rank - 1] || "🏅"}</span>
        
        <div class="podium-score-ring">
          <svg viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" stroke-width="2" opacity="0.1"/>
            <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" stroke-width="2.5" 
              stroke-dasharray="100" stroke-dashoffset="${100 - item.final_score}" stroke-linecap="round" transform="rotate(-90 18 18)" class="ring-fg"/>
          </svg>
          <div class="podium-score-val">${item.final_score}</div>
        </div>
        
        <div class="podium-name">${escapeHtml(item.candidate_name)}</div>
        <div class="podium-file">${escapeHtml(item.filename || "")}</div>
        <div class="podium-skills">${skills || '<span class="mini-tag">—</span>'}</div>
      </div>
    `;
  }).join("");
}

// ─── Candidates Grid ──────────────────────────────────
function renderCandidatesGrid(results) {
  candidatesGrid.innerHTML = results.map((item, idx) => {
    const initials = getInitials(item.candidate_name);
    return `
      <div class="candidate-card" onclick="openModal(${idx})">
        <div class="card-avatar">${initials}</div>
        <div class="card-info">
          <div class="card-name">${escapeHtml(item.candidate_name)}</div>
          <div class="card-file">${escapeHtml(item.filename || "")}</div>
          <div class="card-scores">
            <span class="score-pill ${scoreClass(item.final_score)}">Score: ${item.final_score}</span>
            <span class="score-pill ${scoreClass(item.ai_match_score)}">AI: ${item.ai_match_score}</span>
          </div>
        </div>
        <div class="card-rank">
          <div class="card-rank-num rn-${item.rank <= 3 ? item.rank : 'n'}">#${item.rank}</div>
        </div>
      </div>
    `;
  }).join("");
}

// ─── Modal ────────────────────────────────────────────
function openModal(resultIndex) {
  const item = currentResults[resultIndex];
  if (!item) return;

  const parsed = item.parsed || {};
  const skills = Array.isArray(parsed.skills) ? parsed.skills : [];
  const initials = getInitials(item.candidate_name);

  modalContent.innerHTML = `
    <div class="modal-header">
      <div class="modal-avatar-lg">${initials}</div>
      <div>
        <div class="modal-name">#${item.rank} ${escapeHtml(item.candidate_name)}</div>
        <div class="modal-file">📄 ${escapeHtml(item.filename || "")}</div>
        <div class="modal-score-row">
          <div class="modal-score-card msc-final">
            <div class="msc-val">${item.final_score}</div>
            <div class="msc-label">Final Match</div>
          </div>
          <div class="modal-score-card msc-semantic">
            <div class="msc-val">${item.similarity_score}%</div>
            <div class="msc-label">Semantic</div>
          </div>
          <div class="modal-score-card msc-ai">
            <div class="msc-val">${item.ai_match_score}</div>
            <div class="msc-label">Groq AI</div>
          </div>
        </div>
      </div>
    </div>

    <div class="modal-sections">
      ${item.recommendation ? `
        <div class="modal-section">
          <h4 class="modal-section-title"><span class="section-icon">🤖</span> AI Analysis & Recommendation</h4>
          <div class="modal-text-block modal-rec">${escapeHtml(item.recommendation)}</div>
        </div>` : ""}

      ${item.key_matching_skills && item.key_matching_skills.length ? `
        <div class="modal-section">
          <h4 class="modal-section-title"><span class="section-icon">🎯</span> Matched Skills</h4>
          <div class="modal-tags">${item.key_matching_skills.map(s => `<span class="modal-skill-tag mst-match">${escapeHtml(s)}</span>`).join("")}</div>
        </div>` : ""}

      ${item.missing_skills && item.missing_skills.length ? `
        <div class="modal-section">
          <h4 class="modal-section-title"><span class="section-icon">⚠️</span> Missing Skills / Gaps</h4>
          <div class="modal-tags">${item.missing_skills.map(s => `<span class="modal-skill-tag mst-miss">${escapeHtml(s)}</span>`).join("")}</div>
        </div>` : ""}

      ${item.strengths && item.strengths.length ? `
        <div class="modal-section">
          <h4 class="modal-section-title"><span class="section-icon">💪</span> Core Strengths</h4>
          <div class="modal-tags">${item.strengths.map(s => `<span class="modal-skill-tag mst-neutral">${escapeHtml(s)}</span>`).join("")}</div>
        </div>` : ""}

      ${item.weaknesses && item.weaknesses.length ? `
        <div class="modal-section">
          <h4 class="modal-section-title"><span class="section-icon">📉</span> Areas for Improvement</h4>
          <div class="modal-tags">${item.weaknesses.map(s => `<span class="modal-skill-tag mst-miss">${escapeHtml(s)}</span>`).join("")}</div>
        </div>` : ""}
    </div>
  `;

  modalBackdrop.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  modalBackdrop.classList.add("hidden");
  document.body.style.overflow = "";
}

document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

// ─── Data Export & Reset ──────────────────────────────
function downloadCsv() {
  window.location.href = `${API_BASE}/download-csv`;
  showToast("Downloading AI Ranking CSV report...", "info");
}

async function resetSession() {
  if (!confirm("Are you sure you want to reset the session? All uploaded data will be cleared.")) return;
  
  try {
    const res = await fetch(`${API_BASE}/reset`, { method: "POST" });
    if (res.ok) {
      window.location.reload();
    }
  } catch (err) {
    showToast("Reset failed: " + err.message, "error");
  }
}

// ─── Initialization ───────────────────────────────────
(async function initLoad() {
  try {
    const res = await fetch(`${API_BASE}/results`);
    const data = await res.json();
    if (data.results && data.results.length) {
      currentResults = data.results;
      renderResults(currentResults);
      downloadCsvBtn.disabled = false;
      
      if (data.job_description_loaded) markStepDone(1);
      if (data.resume_count > 0) markStepDone(2);
      if (data.results.length > 0) markStepDone(3);
      
      showToast(`Restored ${data.total} candidates from previous session.`, "info");
    }
  } catch (_) { /* Ignore */ }
})();

// ─── Visual Effects (Canvas) ──────────────────────────
const canvas = document.getElementById('particleCanvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height, particles = [];
  
  function initCanvas() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    particles = [];
    for (let i = 0; i < 40; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 2,
        alpha: Math.random() * 0.5 + 0.1
      });
    }
  }
  
  function drawParticles() {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#fbbf24'; // gold particles
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = width; if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height; if (p.y > height) p.y = 0;
      
      ctx.globalAlpha = p.alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });
    requestAnimationFrame(drawParticles);
  }
  
  initCanvas();
  drawParticles();
  window.addEventListener('resize', initCanvas);
}

// Nav scroll effect
window.addEventListener('scroll', () => {
  const nav = document.getElementById('topnav');
  if (nav) {
    if (window.scrollY > 10) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  }
});

// Scroll reveal effects
(function setupScrollReveal() {
  const revealSelectors = [
    ".step-wrap",
    ".results-header",
    ".empty-state",
    ".podium-section",
    ".candidates-label",
    ".candidate-card",
    ".podium-card",
    ".table-view"
  ];

  const selector = revealSelectors.join(",");
  const observed = new WeakSet();

  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll(selector).forEach(el => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.14, rootMargin: "0px 0px -8% 0px" });

  function observeRevealItems(root = document) {
    root.querySelectorAll(selector).forEach((el, index) => {
      if (observed.has(el)) return;
      observed.add(el);
      el.classList.add("reveal-on-scroll");
      el.style.setProperty("--reveal-delay", `${Math.min(index * 55, 220)}ms`);
      observer.observe(el);
    });
  }

  observeRevealItems();

  const mutationObserver = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        if (node.matches && node.matches(selector)) {
          observeRevealItems(node.parentElement || document);
        } else if (node.querySelectorAll) {
          observeRevealItems(node);
        }
      });
    });
  });

  mutationObserver.observe(document.body, { childList: true, subtree: true });
})();
