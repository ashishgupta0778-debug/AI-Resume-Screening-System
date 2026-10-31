// ================= CONFIGURATION =================

const API_BASE_URL = window.getApiBaseUrl ? window.getApiBaseUrl() : (() => {
    const stored = localStorage.getItem("resumeAI_backend_url");
    if (stored) return stored.replace(/\/+$/, "");
    if (window.location.port === "5500" || window.location.protocol === "file:") {
        return "http://127.0.0.1:8000";
    }
    return window.location.origin;
})();


// ================= LOGIN PROTECTION =================

const isLoggedIn = sessionStorage.getItem("resumeAI_loggedIn");

if (isLoggedIn !== "true") {
    window.location.href = "login.html";
}

const adminEmail = sessionStorage.getItem("resumeAI_admin");
if (adminEmail) {
    const badge = document.getElementById("userEmailBadge");
    if (badge) badge.innerText = adminEmail;
}


// ================= LOGOUT =================

async function logout() {
    const token = sessionStorage.getItem("resumeAI_token");
    if (token) {
        try {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
        } catch (e) {}
    }
    sessionStorage.removeItem("resumeAI_loggedIn");
    sessionStorage.removeItem("resumeAI_token");
    sessionStorage.removeItem("resumeAI_admin");
    window.location.href = "login.html";
}


// ================= STATE =================

let currentScreeningData = null;
let currentSearchMode = "ANY";
let activeView = "screen";
let cachedCandidates = [];


// ================= INITIALIZATION =================

document.addEventListener("DOMContentLoaded", function () {
    loadScreenJobsDropdown();
    setupQuickSkillPills();

    // Check URL query param for default tab or preselected job
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("tab") === "search" || window.location.hash === "#search") {
        switchView("search");
    } else {
        switchView("screen");
    }

    const preselectedJobId = urlParams.get("job_id");
    if (preselectedJobId) {
        setTimeout(() => {
            const select = document.getElementById("screenJobSelect");
            if (select) {
                select.value = preselectedJobId;
                select.dispatchEvent(new Event("change"));
            }
        }, 300);
    }

    // Job dropdown change event
    const jobSelect = document.getElementById("screenJobSelect");
    if (jobSelect) {
        jobSelect.addEventListener("change", function () {
            const selected = this.options[this.selectedIndex];
            const desc = selected.getAttribute("data-description");
            const textarea = document.getElementById("jobDescription");
            if (textarea && desc) {
                textarea.value = desc;
            }
        });
    }

    // Resume files change event & drag-and-drop support
    const resumeFiles = document.getElementById("resumeFiles");
    const selectedFiles = document.getElementById("selectedFiles");
    const uploadDropzone = document.getElementById("uploadDropzone");

    function renderSelectedFiles() {
        if (!selectedFiles || !resumeFiles) return;
        selectedFiles.innerHTML = "";
        const files = resumeFiles.files;
        if (!files || files.length === 0) return;

        const heading = document.createElement("div");
        heading.className = "selected-files-heading";
        heading.innerHTML = `
            <strong><i class="fa-solid fa-file-circle-check" style="color: #4f46e5; margin-right: 6px;"></i>${files.length} resume(s) selected for screening</strong>
            <button type="button" class="clear-files-btn" onclick="clearSelectedFiles()" title="Clear selected files">
                <i class="fa-solid fa-xmark"></i> Clear selection
            </button>
        `;
        selectedFiles.appendChild(heading);

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const isPdf = file.name.toLowerCase().endsWith(".pdf");
            const item = document.createElement("div");
            item.className = "selected-file-item";
            item.innerHTML = `
                <div>
                    <i class="fa-solid ${isPdf ? 'fa-file-pdf' : 'fa-triangle-exclamation'}" style="color: ${isPdf ? '#ef4444' : '#f59e0b'};"></i>
                    <span>${file.name}</span>
                </div>
                <small>${(file.size / 1024).toFixed(1)} KB ${!isPdf ? '<span style="color:#ef4444; font-weight:600; margin-left:4px;">(Not a PDF)</span>' : ''}</small>
            `;
            selectedFiles.appendChild(item);
        }
    }

    if (resumeFiles) {
        resumeFiles.addEventListener("change", renderSelectedFiles);
    }

    if (uploadDropzone && resumeFiles) {
        // Keyboard accessibility: open picker on Enter or Space when focused
        uploadDropzone.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                resumeFiles.click();
            }
        });

        // Drag and drop event handling
        ["dragenter", "dragover"].forEach(eventName => {
            uploadDropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                uploadDropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "dragend"].forEach(eventName => {
            uploadDropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                uploadDropzone.classList.remove("dragover");
            }, false);
        });

        uploadDropzone.addEventListener("drop", function (e) {
            e.preventDefault();
            e.stopPropagation();
            uploadDropzone.classList.remove("dragover");

            const dt = e.dataTransfer;
            if (dt && dt.files && dt.files.length > 0) {
                try {
                    resumeFiles.files = dt.files;
                } catch (err) {
                    console.warn("Direct DataTransfer assignment not supported, fallback active", err);
                }
                renderSelectedFiles();
            }
        }, false);
    }
});

// Clear selected files helper
function clearSelectedFiles() {
    const resumeFiles = document.getElementById("resumeFiles");
    const selectedFiles = document.getElementById("selectedFiles");
    if (resumeFiles) {
        resumeFiles.value = "";
    }
    if (selectedFiles) {
        selectedFiles.innerHTML = "";
    }
}
window.clearSelectedFiles = clearSelectedFiles;


// ================= TAB NAVIGATION =================

function switchView(viewName) {
    activeView = viewName;
    const viewScreen = document.getElementById("viewScreen");
    const viewSearch = document.getElementById("viewSearch");
    const tabBtnScreen = document.getElementById("tabBtnScreen");
    const tabBtnSearch = document.getElementById("tabBtnSearch");

    if (viewName === "screen") {
        viewScreen.style.display = "block";
        viewSearch.style.display = "none";
        tabBtnScreen.classList.add("active");
        tabBtnSearch.classList.remove("active");
    } else {
        viewScreen.style.display = "none";
        viewSearch.style.display = "block";
        tabBtnScreen.classList.remove("active");
        tabBtnSearch.classList.add("active");
        loadAllCandidatesDatabase();
    }
}


// ================= LOAD JOBS DROPDOWN =================

async function loadScreenJobsDropdown() {
    const select = document.getElementById("screenJobSelect");
    if (!select) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/jobs`);
        if (!response.ok) return;

        const jobs = await response.json();
        jobs.forEach(job => {
            const opt = document.createElement("option");
            opt.value = job.id;
            opt.innerText = `${job.title} (${job.min_experience}+ yrs exp)`;
            opt.setAttribute("data-description", job.description);
            select.appendChild(opt);
        });
    } catch (e) {
        console.warn("Could not load jobs into screening select:", e);
    }
}


// ================= MULTI-RESUME SCREENING =================

async function screenCandidates() {
    const jobSelect = document.getElementById("screenJobSelect");
    const jobDescription = document.getElementById("jobDescription").value.trim();
    const status = document.getElementById("candidateStatus");
    const results = document.getElementById("candidateResults");
    const failedContainer = document.getElementById("failedFilesContainer");
    const resumeFiles = document.getElementById("resumeFiles");
    const files = resumeFiles ? resumeFiles.files : [];

    if (!jobDescription && (!jobSelect || !jobSelect.value)) {
        status.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-circle-exclamation"></i>
                Please select a Job Description or enter custom requirements.
            </div>
        `;
        return;
    }

    if (!files || files.length === 0) {
        status.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-circle-exclamation"></i>
                Please select at least one PDF resume to screen.
            </div>
        `;
        return;
    }

    const formData = new FormData();
    if (jobSelect && jobSelect.value) {
        formData.append("job_id", jobSelect.value);
    }
    formData.append("job_description", jobDescription);

    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    status.innerHTML = `
        <div class="loading-message">
            <i class="fa-solid fa-spinner fa-spin"></i>
            AI is screening and ranking ${files.length} resume(s)...
        </div>
    `;

    results.innerHTML = `
        <div class="empty-result">
            <div class="empty-icon"><i class="fa-solid fa-brain"></i></div>
            <h2>Screening Candidates</h2>
            <p>Evaluating skills, degrees, experience, and calculating TF-IDF similarities...</p>
        </div>
    `;
    failedContainer.innerHTML = "";

    try {
        const response = await fetch(`${API_BASE_URL}/screen-multiple-resumes`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || "Screening API failed");
        }

        currentScreeningData = data;
        displayCandidateResults(data);

        // Display failed files notice if any
        if (data.failed_files && data.failed_files.length > 0) {
            failedContainer.innerHTML = `
                <div class="error-message" style="margin-top: 15px;">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <div>
                        <b>${data.failed_files.length} file(s) could not be processed:</b>
                        <ul style="margin: 4px 0 0 16px; padding: 0;">
                            ${data.failed_files.map(f => `<li><b>${f.filename}</b>: ${f.reason}</li>`).join("")}
                        </ul>
                    </div>
                </div>
            `;
        }

        status.innerHTML = `
            <div class="success-message">
                <i class="fa-solid fa-circle-check"></i>
                Batch screening completed successfully: ${data.total_candidates} candidate(s) ranked.
            </div>
        `;

    } catch (error) {
        console.error(error);
        status.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-circle-exclamation"></i>
                ${error.message || "Unable to connect to the FastAPI server."}
            </div>
        `;
        results.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <h2>Screening Failed</h2>
                <p>Ensure the FastAPI server is running on port 8000.</p>
            </div>
        `;
    }
}


// ================= DISPLAY SCREENING RESULTS =================

function displayCandidateResults(data) {
    const results = document.getElementById("candidateResults");
    const candidates = data.candidates || [];

    if (candidates.length === 0) {
        results.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-user-slash"></i></div>
                <h2>No Valid Candidates Found</h2>
                <p>No readable text could be extracted from the uploaded files.</p>
            </div>
        `;
        return;
    }

    const shortlisted = candidates.filter(c => c.status === "Shortlisted").length;
    const review = candidates.filter(c => c.status === "Review").length;
    const rejected = candidates.filter(c => c.status === "Not shortlisted" || c.status === "Rejected").length;

    let html = `
        <div class="result-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
            <div>
                <h2>Candidate Ranking &amp; Shortlisting</h2>
                <p>Role: <b>${data.job_title || 'General Screening'}</b> &bull; Ranked by combined AI matching score</p>
            </div>
            <div>
                <button class="screen-btn" onclick="exportCandidatesCSV()" style="margin: 0; padding: 10px 18px; font-size: 13px;">
                    <i class="fa-solid fa-file-csv"></i> Export Shortlist (CSV)
                </button>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="candidate-summary" style="grid-template-columns: repeat(${rejected > 0 ? 4 : 3}, 1fr);">
            <div class="summary-card">
                <div class="summary-icon"><i class="fa-solid fa-users"></i></div>
                <div>
                    <span>Total Evaluated</span>
                    <strong>${candidates.length}</strong>
                </div>
            </div>

            <div class="summary-card">
                <div class="summary-icon" style="color: #059669; background: #ecfdf5;"><i class="fa-solid fa-user-check"></i></div>
                <div>
                    <span>Shortlisted</span>
                    <strong style="color: #059669;">${shortlisted}</strong>
                </div>
            </div>

            <div class="summary-card">
                <div class="summary-icon" style="color: #d97706; background: #fffbeb;"><i class="fa-solid fa-user-clock"></i></div>
                <div>
                    <span>Under Review</span>
                    <strong style="color: #d97706;">${review}</strong>
                </div>
            </div>

            ${rejected > 0 ? `
            <div class="summary-card">
                <div class="summary-icon" style="color: #dc2626; background: #fef2f2;"><i class="fa-solid fa-user-xmark"></i></div>
                <div>
                    <span>Not Shortlisted</span>
                    <strong style="color: #dc2626;">${rejected}</strong>
                </div>
            </div>` : ""}
        </div>

        <!-- Ranking Table -->
        <div class="candidate-table-wrapper">
            <table class="candidate-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Candidate / Resume</th>
                        <th>Skill Match</th>
                        <th>Exp Match</th>
                        <th>Edu Match</th>
                        <th>TF-IDF</th>
                        <th>Overall Score</th>
                        <th>Decision Action</th>
                    </tr>
                </thead>
                <tbody>
    `;

    candidates.forEach((candidate, index) => {
        const candidateName = candidate.candidate_name && candidate.candidate_name !== "Not found"
            ? candidate.candidate_name
            : candidate.resume;

        const statusClass = candidate.status === "Shortlisted"
            ? "status-shortlisted"
            : (candidate.status === "Not shortlisted" || candidate.status === "Rejected")
            ? "status-review"
            : "status-review";

        html += `
            <tr>
                <td><div class="rank-number">${candidate.rank}</div></td>
                <td>
                    <div class="candidate-name" style="cursor: pointer;" onclick="openCandidateDetailModal(${candidate.id || index})">
                        <div class="candidate-avatar"><i class="fa-solid fa-user"></i></div>
                        <div>
                            <strong>${candidateName}</strong>
                            <small>${candidate.resume} &bull; ${candidate.matched_skills.length} matched</small>
                        </div>
                    </div>
                </td>
                <td><strong>${candidate.skill_score}%</strong></td>
                <td>
                    <span class="match-value" style="${candidate.experience_match === 'NO' ? 'background: #fef2f2; color: #b91c1c;' : ''}">
                        ${candidate.experience_match}
                    </span>
                </td>
                <td>
                    <span class="match-value" style="${candidate.education_match === 'NO' ? 'background: #fef2f2; color: #b91c1c;' : ''}">
                        ${candidate.education_match}
                    </span>
                </td>
                <td>${candidate.tfidf_score}</td>
                <td><div class="overall-score">${candidate.combined_score}</div></td>
                <td>
                    <select
                        class="candidate-status ${statusClass}"
                        onchange="updateLiveCandidateStatus(${index}, ${candidate.id || 0}, this.value)"
                        style="border: 1px solid #d1d5db; border-radius: 8px; padding: 6px 10px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 600;"
                    >
                        <option value="Shortlisted" ${candidate.status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                        <option value="Review" ${candidate.status === 'Review' ? 'selected' : ''}>Review</option>
                        <option value="Not shortlisted" ${(candidate.status === 'Not shortlisted' || candidate.status === 'Rejected') ? 'selected' : ''}>Not shortlisted</option>
                    </select>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>

        <!-- Candidate Detailed Breakdown Cards -->
        <div class="candidate-details-section">
            <h2>Detailed Skill Match Analysis</h2>
            <p>Individual candidate skill breakdowns and requirements alignment</p>
    `;

    candidates.forEach(candidate => {
        const candidateName = candidate.candidate_name && candidate.candidate_name !== "Not found"
            ? candidate.candidate_name
            : candidate.resume;

        const eduText = Array.isArray(candidate.education)
            ? candidate.education.join(", ")
            : candidate.education;

        html += `
            <div class="candidate-detail-card">
                <div class="candidate-detail-header">
                    <div>
                        <h3>#${candidate.rank} ${candidateName}</h3>
                        <span>
                            File: <b>${candidate.resume}</b>
                            &bull; Overall Score: <strong>${candidate.combined_score}</strong>
                            &bull; Experience: <strong>${candidate.experience}</strong> (${candidate.experience_match})
                            &bull; Education: <strong>${eduText}</strong> (${candidate.education_match})
                        </span>
                    </div>
                    <span class="candidate-status ${candidate.status === 'Shortlisted' ? 'status-shortlisted' : 'status-review'}">
                        ${candidate.status}
                    </span>
                </div>

                <div class="skills-columns">
                    <div>
                        <h4><i class="fa-solid fa-circle-check"></i> Matched Required Skills (${candidate.matched_skills.length})</h4>
                        <div class="skill-tags">
                            ${candidate.matched_skills.length > 0
                                ? candidate.matched_skills.map(s => `<span>${s}</span>`).join("")
                                : "<span>None detected</span>"
                            }
                        </div>
                    </div>

                    <div>
                        <h4><i class="fa-solid fa-circle-xmark"></i> Missing Required Skills (${candidate.missing_skills.length})</h4>
                        <div class="missing-tags">
                            ${candidate.missing_skills.length > 0
                                ? candidate.missing_skills.map(s => `<span>${s}</span>`).join("")
                                : "<span>None missing</span>"
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    results.innerHTML = html;
}


// ================= LIVE STATUS UPDATE (WITH PERSISTENCE) =================

async function updateLiveCandidateStatus(index, candidateId, newStatus) {
    if (currentScreeningData && currentScreeningData.candidates && currentScreeningData.candidates[index]) {
        currentScreeningData.candidates[index].status = newStatus;
        displayCandidateResults(currentScreeningData);
    }

    if (candidateId > 0) {
        try {
            await fetch(`${API_BASE_URL}/api/candidates/${candidateId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus })
            });
        } catch (e) {
            console.warn("Could not sync candidate status to DB:", e);
        }
    }
}


// ================= EXPORT CSV =================

function exportCandidatesCSV() {
    if (!currentScreeningData || !currentScreeningData.candidates || currentScreeningData.candidates.length === 0) {
        alert("No candidates available to export.");
        return;
    }

    const headers = [
        "Rank", "Candidate Name", "Email", "Resume File",
        "Overall Score", "Skill Score", "Experience Match",
        "Education Match", "TF-IDF Score", "Status",
        "Matched Skills", "Missing Skills"
    ];

    const rows = currentScreeningData.candidates.map(c => [
        c.rank,
        `"${(c.candidate_name || "").replace(/"/g, '""')}"`,
        `"${(c.candidate_email || "").replace(/"/g, '""')}"`,
        `"${(c.resume || "").replace(/"/g, '""')}"`,
        c.combined_score,
        c.skill_score,
        c.experience_match,
        c.education_match,
        c.tfidf_score,
        c.status,
        `"${(c.matched_skills || []).join(", ").replace(/"/g, '""')}"`,
        `"${(c.missing_skills || []).join(", ").replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `candidates_shortlist_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}


// =========================================
// CANDIDATE DATABASE & SKILL SEARCH
// =========================================

function setupQuickSkillPills() {
    const container = document.getElementById("quickSkillPills");
    if (!container) return;

    const topSkills = [
        "Python", "Java", "SQL", "React", "Machine Learning",
        "AWS", "Docker", "JavaScript", "HTML", "CSS", "APIs", "Git"
    ];

    container.innerHTML = topSkills.map(skill => `
        <span onclick="addSkillToSearch('${skill}')" style="cursor: pointer; user-select: none;">
            + ${skill}
        </span>
    `).join("");
}

function addSkillToSearch(skill) {
    const input = document.getElementById("skillSearchInput");
    if (!input) return;

    const currentVal = input.value.trim();
    const skills = currentVal ? currentVal.split(",").map(s => s.trim()) : [];

    if (!skills.map(s => s.toLowerCase()).includes(skill.toLowerCase())) {
        skills.push(skill);
        input.value = skills.join(", ");
    }
}

function setSearchMode(mode) {
    currentSearchMode = mode;
    const btnAny = document.getElementById("btnModeAny");
    const btnAll = document.getElementById("btnModeAll");
    if (mode === "ANY") {
        btnAny.classList.add("active");
        btnAll.classList.remove("active");
    } else {
        btnAll.classList.add("active");
        btnAny.classList.remove("active");
    }
}

function resetSkillSearch() {
    document.getElementById("skillSearchInput").value = "";
    document.getElementById("dbStatusFilter").value = "all";
    document.getElementById("dbMinScore").value = "";
    setSearchMode("ANY");
    loadAllCandidatesDatabase();
}

async function loadAllCandidatesDatabase() {
    const container = document.getElementById("databaseTableContainer");
    const heading = document.getElementById("searchResultsHeading");
    const sub = document.getElementById("searchResultsSub");

    if (heading) heading.innerText = "Candidate Database";
    if (sub) sub.innerText = "Showing all screened candidate records";

    try {
        const response = await fetch(`${API_BASE_URL}/api/candidates`);
        if (!response.ok) throw new Error("Could not load candidates");

        const candidates = await response.json();
        cachedCandidates = candidates;
        renderDatabaseTable(candidates);

    } catch (e) {
        console.warn(e);
        container.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-inbox"></i></div>
                <h2>No candidates recorded yet</h2>
                <p>Run a screening session to populate the candidate database.</p>
            </div>
        `;
    }
}

async function executeSkillSearch() {
    const skillInput = document.getElementById("skillSearchInput").value.trim();
    const statusFilter = document.getElementById("dbStatusFilter").value;
    const minScore = parseFloat(document.getElementById("dbMinScore").value) || 0;
    const container = document.getElementById("databaseTableContainer");
    const heading = document.getElementById("searchResultsHeading");
    const sub = document.getElementById("searchResultsSub");

    const skills = skillInput ? skillInput.split(",").map(s => s.trim()).filter(Boolean) : [];

    if (skills.length === 0) {
        // If no skills specified, filter existing database candidates
        let filtered = [...cachedCandidates];
        if (statusFilter !== "all") {
            filtered = filtered.filter(c => c.status === statusFilter);
        }
        if (minScore > 0) {
            filtered = filtered.filter(c => (c.combined_score || 0) >= minScore);
        }
        renderDatabaseTable(filtered);
        return;
    }

    container.innerHTML = `
        <div class="empty-result">
            <div class="empty-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
            <h2>Searching candidates by skill...</h2>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/api/candidates/skill-search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                skills: skills,
                mode: currentSearchMode,
                min_score: minScore,
                status: statusFilter
            })
        });

        const data = await response.json();

        if (heading) heading.innerText = `Skill Search Results (${data.total_matched})`;
        if (sub) sub.innerText = `Mode: Match ${data.mode} of [${skills.join(", ")}]`;

        renderDatabaseTable(data.candidates, true);

    } catch (e) {
        console.error(e);
        container.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <h2>Search failed</h2>
                <p>Ensure the FastAPI backend is running.</p>
            </div>
        `;
    }
}

function renderDatabaseTable(candidates, isSkillSearchResult = false) {
    const container = document.getElementById("databaseTableContainer");
    if (!container) return;

    if (!candidates || candidates.length === 0) {
        container.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-user-slash"></i></div>
                <h2>No matching candidates found</h2>
                <p>Try broadening your skills or lowering the minimum score.</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="candidate-table-wrapper">
            <table class="candidate-table">
                <thead>
                    <tr>
                        <th>Candidate Name</th>
                        <th>Email / Contact</th>
                        <th>Applied Role</th>
                        <th>${isSkillSearchResult ? 'Skill Match %' : 'Overall Score'}</th>
                        <th>${isSkillSearchResult ? 'Matched Skills' : 'Experience'}</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
    `;

    candidates.forEach(c => {
        const candidateName = c.candidate_name && c.candidate_name !== "Not found"
            ? c.candidate_name
            : c.resume_filename;

        const candidateEmail = c.candidate_email && c.candidate_email !== "Not found"
            ? c.candidate_email
            : "Email not listed";

        const statusClass = c.status === "Shortlisted"
            ? "status-shortlisted"
            : (c.status === "Not shortlisted" || c.status === "Rejected")
            ? "status-review"
            : "status-review";

        const scoreDisplay = isSkillSearchResult
            ? `${c.skill_match_percentage}%`
            : `${c.combined_score || 0}`;

        const secondaryDisplay = isSkillSearchResult
            ? (c.matched_search_skills || []).join(", ") || "None"
            : `${c.experience || 'Not Mentioned'}`;

        html += `
            <tr>
                <td>
                    <div class="candidate-name" style="cursor: pointer;" onclick="openCandidateDetailModal(${c.candidate_id || c.id})">
                        <div class="candidate-avatar"><i class="fa-solid fa-user"></i></div>
                        <div>
                            <strong>${candidateName}</strong>
                            <small>${c.resume_filename || ''}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <div>${candidateEmail}</div>
                    <small style="color: #64748b;">${c.phone && c.phone !== 'Not found' ? c.phone : ''}</small>
                </td>
                <td>${c.job_title || 'General Screening'}</td>
                <td><div class="overall-score">${scoreDisplay}</div></td>
                <td><small style="font-weight: 600; color: #475569;">${secondaryDisplay}</small></td>
                <td>
                    <select
                        class="candidate-status ${statusClass}"
                        onchange="updateDbCandidateStatus(${c.candidate_id || c.id}, this.value)"
                        style="border: 1px solid #d1d5db; border-radius: 8px; padding: 6px 10px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 600;"
                    >
                        <option value="Shortlisted" ${c.status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                        <option value="Review" ${c.status === 'Review' ? 'selected' : ''}>Review</option>
                        <option value="Not shortlisted" ${(c.status === 'Not shortlisted' || c.status === 'Rejected') ? 'selected' : ''}>Not shortlisted</option>
                    </select>
                </td>
                <td>
                    <button
                        class="screen-btn"
                        style="margin: 0; padding: 6px 12px; font-size: 12px;"
                        onclick="openCandidateDetailModal(${c.candidate_id || c.id})"
                    >
                        Details
                    </button>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
}

async function updateDbCandidateStatus(candidateId, newStatus) {
    try {
        await fetch(`${API_BASE_URL}/api/candidates/${candidateId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        loadAllCandidatesDatabase();
    } catch (e) {
        console.warn("Could not update candidate status in DB:", e);
    }
}

function exportDatabaseCSV() {
    window.location.href = `${API_BASE_URL}/api/reports/export-csv`;
}


// ================= CANDIDATE DETAIL MODAL =================

async function openCandidateDetailModal(candidateId) {
    const modal = document.getElementById("candidateDetailModal");
    const body = document.getElementById("modalBody");
    if (!modal || !body) return;

    modal.style.display = "flex";
    body.innerHTML = `
        <div style="text-align: center; padding: 40px 0;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 32px; color: #4f46e5;"></i>
            <p style="margin-top: 12px; color: #64748b;">Loading candidate profile...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/api/candidates/${candidateId}`);
        if (!response.ok) throw new Error("Could not load candidate details");

        const data = await response.json();
        const candidateName = data.name && data.name !== "Not found" ? data.name : data.filename;

        body.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h2 style="margin: 0 0 6px 0; color: #0f172a; font-size: 22px;">${candidateName}</h2>
                <p style="margin: 0; color: #64748b; font-size: 14px;">
                    <i class="fa-solid fa-file-pdf" style="color: #ef4444;"></i> ${data.filename}
                    &bull; Created: ${data.created_at || 'N/A'}
                </p>
            </div>

            <div class="info-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 20px;">
                <div class="info-card">
                    <h3>Contact Information</h3>
                    <p><b>Email:</b> ${data.email || 'Not found'}</p>
                    <p><b>Phone:</b> ${data.phone || 'Not found'}</p>
                </div>
                <div class="info-card">
                    <h3>Experience &amp; Education</h3>
                    <p><b>Experience:</b> ${data.experience || 'Not Mentioned'}</p>
                    <p><b>Education:</b> ${Array.isArray(data.education) ? data.education.join(', ') : data.education}</p>
                </div>
            </div>

            <div class="info-card" style="margin-bottom: 20px;">
                <h3>Extracted Technical &amp; Soft Skills (${(data.skills || []).length})</h3>
                <div class="skill-tags" style="margin-top: 8px;">
                    ${(data.skills || []).length > 0
                        ? data.skills.map(s => `<span>${s}</span>`).join("")
                        : "<span>No skills identified</span>"
                    }
                </div>
            </div>

            ${data.screening_history && data.screening_history.length > 0 ? `
                <div class="info-card" style="margin-bottom: 20px;">
                    <h3>Screening Score History</h3>
                    <ul style="padding-left: 20px; margin-top: 8px;">
                        ${data.screening_history.map(s => `
                            <li><b>${s.job_title || 'General'}:</b> Score: ${s.combined_score} (${s.status}) &bull; TF-IDF: ${s.tfidf_score}</li>
                        `).join("")}
                    </ul>
                </div>
            ` : ""}

            <div class="info-card">
                <h3>Extracted Resume Text Preview</h3>
                <pre style="background: #f8fafc; padding: 14px; border-radius: 8px; font-size: 12px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; color: #334155;">${data.raw_text ? data.raw_text.substring(0, 1500) + '...' : 'No text available'}</pre>
            </div>
        `;
    } catch (e) {
        body.innerHTML = `
            <div style="text-align: center; color: #ef4444; padding: 30px;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 32px; margin-bottom: 12px;"></i>
                <p>Failed to load candidate details.</p>
            </div>
        `;
    }
}

function closeCandidateModal() {
    const modal = document.getElementById("candidateDetailModal");
    if (modal) modal.style.display = "none";
}

window.addEventListener("click", function (event) {
    const modal = document.getElementById("candidateDetailModal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
});
