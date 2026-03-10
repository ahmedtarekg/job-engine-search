/* Job Engine Search — Dashboard JS */

// ── Status update (no page reload) ────────────────────────────────────────
function updateStatus(selectEl) {
    const jobId = selectEl.dataset.jobId;
    const status = selectEl.value;

    fetch("/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, status: status }),
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) {
            console.error("Status update failed:", data.error);
            return;
        }
        // Visual feedback: dim/undim row
        const row = selectEl.closest("tr");
        if (row) {
            row.classList.toggle("dismissed", status === "dismissed");
        }
    })
    .catch(err => console.error("Status update error:", err));
}

// ── Run pipeline ───────────────────────────────────────────────────────────
function runPipeline() {
    const btn = document.getElementById("run-btn");
    const indicator = document.getElementById("pipeline-indicator");
    const msg = document.getElementById("pipeline-msg");

    btn.disabled = true;
    btn.textContent = "Running…";
    indicator.className = "pipeline-running";
    if (msg) { msg.style.display = "block"; msg.textContent = "Pipeline started…"; }

    fetch("/run", { method: "POST" })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) {
            showMsg("Pipeline error: " + data.message, "error");
            resetBtn();
            return;
        }
        pollPipelineStatus();
    })
    .catch(err => {
        showMsg("Request failed: " + err, "error");
        resetBtn();
    });
}

function pollPipelineStatus() {
    const interval = setInterval(() => {
        fetch("/pipeline_status")
        .then(r => r.json())
        .then(data => {
            if (!data.running) {
                clearInterval(interval);
                const summary = data.last_summary || {};
                if (summary.error) {
                    showMsg("Pipeline error: " + summary.error, "error");
                } else {
                    showMsg(
                        `Done! ${summary.inserted || 0} new jobs inserted, ` +
                        `${summary.scored || 0} scored. Refreshing…`,
                        "success"
                    );
                    setTimeout(() => location.reload(), 2000);
                }
                resetBtn();
            }
        })
        .catch(() => clearInterval(interval));
    }, 3000);
}

function showMsg(text, type) {
    const msg = document.getElementById("pipeline-msg");
    if (!msg) return;
    msg.style.display = "block";
    msg.textContent = text;
    msg.style.color = type === "error" ? "#f87171" : "#34d399";
}

function resetBtn() {
    const btn = document.getElementById("run-btn");
    const indicator = document.getElementById("pipeline-indicator");
    if (btn) { btn.disabled = false; btn.textContent = "Run Now"; }
    if (indicator) { indicator.className = "pipeline-idle"; }
}

// ── Score badge tooltip ────────────────────────────────────────────────────
// Tooltips are handled via HTML `title` attribute on badge elements (native browser)
// No extra JS needed.

// ── Filter range display ───────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    // Already handled inline with oninput in template
});
