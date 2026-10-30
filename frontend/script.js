// ================= CONFIGURATION =================

const API_BASE_URL = (() => {
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

// Display logged in user email
const adminEmail = sessionStorage.getItem("resumeAI_admin");
if (adminEmail) {
    const badge = document.getElementById("userEmailBadge");
    if (badge) {
        badge.innerText = adminEmail;
    }
}


// ================= LOGOUT =================

async function logout() {
    const token = sessionStorage.getItem("resumeAI_token");
    if (token) {
        try {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });
        } catch (e) {
            console.log("Logout notification sent:", e);
        }
    }
    sessionStorage.removeItem("resumeAI_loggedIn");
    sessionStorage.removeItem("resumeAI_token");
    sessionStorage.removeItem("resumeAI_admin");
    window.location.href = "login.html";
}


// ================= DASHBOARD INITIALIZATION =================

document.addEventListener("DOMContentLoaded", function () {
    loadDashboardStats();
    loadJobsDropdown();

    const fileInput = document.getElementById("resumeFile");
    const status = document.getElementById("status");

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                if (status) {
                    status.innerHTML = `
                        <div style="margin-top: 12px; color: #4338ca; font-weight: 500;">
                            <i class="fa-solid fa-file-pdf"></i>
                            Selected: <b>${file.name}</b> (${(file.size / 1024).toFixed(1)} KB)
                        </div>
                    `;
                }
            }
        });
    }

    const jobSelect = document.getElementById("jobSelect");
    if (jobSelect) {
        jobSelect.addEventListener("change", function () {
            const selectedOption = this.options[this.selectedIndex];
            const desc = selectedOption.getAttribute("data-description");
            const jdTextarea = document.getElementById("jobDescription");
            if (jdTextarea && desc) {
                jdTextarea.value = desc;
            }
        });
    }
});


// ================= LOAD DASHBOARD STATS =================

async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`);
        if (!response.ok) return;

        const data = await response.json();

        // Update Counter Numbers
        document.getElementById("statTotalScreened").innerText = data.total_resumes_screened || 0;
        document.getElementById("statTotalCandidates").innerText = data.total_unique_candidates || 0;
        document.getElementById("statShortlisted").innerText = data.total_shortlisted || 0;
        document.getElementById("statReview").innerText = data.total_review || 0;
        document.getElementById("statTotalJobs").innerText = data.total_jobs || 0;

        // Update Score Distribution
        const dist = data.score_distribution || {};
        const c80 = dist["80-100"] || 0;
        const c60 = dist["60-79"] || 0;
        const c40 = dist["40-59"] || 0;
        const c0 = dist["<40"] || 0;
        const totalScreened = (c80 + c60 + c40 + c0) || 1;

        document.getElementById("count80").innerText = c80;
        document.getElementById("count60").innerText = c60;
        document.getElementById("count40").innerText = c40;
        document.getElementById("count0").innerText = c0;

        document.getElementById("bar80").style.width = `${Math.round((c80 / totalScreened) * 100)}%`;
        document.getElementById("bar60").style.width = `${Math.round((c60 / totalScreened) * 100)}%`;
        document.getElementById("bar40").style.width = `${Math.round((c40 / totalScreened) * 100)}%`;
        document.getElementById("bar0").style.width = `${Math.round((c0 / totalScreened) * 100)}%`;

        // Update Recent Activity
        renderRecentActivity(data.recent_sessions, data.recent_candidates);

    } catch (e) {
        console.warn("Could not load dashboard stats from backend:", e);
    }
}


function renderRecentActivity(sessions, candidates) {
    const container = document.getElementById("recentActivityContainer");
    if (!container) return;

    if ((!sessions || sessions.length === 0) && (!candidates || candidates.length === 0)) {
        return;
    }

    let html = `
        <div class="candidate-table-wrapper" style="margin-top: 10px;">
            <table class="candidate-table">
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>Candidate / Resume</th>
                        <th>Job Title</th>
                        <th>Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;

    if (candidates && candidates.length > 0) {
        candidates.forEach(c => {
            const statusClass = c.status === "Shortlisted" ? "status-shortlisted" : "status-review";
            html += `
                <tr>
                    <td><small style="color: #64748b;">${c.created_at || 'Recent'}</small></td>
                    <td>
                        <div class="candidate-name">
                            <div class="candidate-avatar"><i class="fa-solid fa-user"></i></div>
                            <div>
                                <strong>${c.candidate_name && c.candidate_name !== 'Not found' ? c.candidate_name : c.resume_filename}</strong>
                                <small>${c.resume_filename}</small>
                            </div>
                        </div>
                    </td>
                    <td>${c.job_title || 'General Screening'}</td>
                    <td><div class="overall-score">${c.combined_score}</div></td>
                    <td><span class="candidate-status ${statusClass}">${c.status}</span></td>
                </tr>
            `;
        });
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
}


// ================= LOAD JOBS DROPDOWN =================

async function loadJobsDropdown() {
    const select = document.getElementById("jobSelect");
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
        console.warn("Could not load jobs dropdown:", e);
    }
}


// ================= SINGLE RESUME SCREENING =================

async function screenResume() {
    const fileInput = document.getElementById("resumeFile");
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    const jdInput = document.getElementById("jobDescription");
    const jobSelect = document.getElementById("jobSelect");

    if (!fileInput || fileInput.files.length === 0) {
        status.innerHTML = `
            <div style="margin-top: 12px; color: #dc2626; font-weight: 500;">
                <i class="fa-solid fa-circle-exclamation"></i>
                Please select a PDF resume.
            </div>
        `;
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    if (jobSelect && jobSelect.value) {
        formData.append("job_id", jobSelect.value);
    }

    if (jdInput && jdInput.value.trim()) {
        formData.append("job_description", jdInput.value.trim());
    }

    status.innerHTML = `
        <div style="margin-top: 12px; color: #2563eb; font-weight: 500;">
            <i class="fa-solid fa-spinner fa-spin"></i>
            AI is analyzing resume...
        </div>
    `;

    result.innerHTML = "";

    try {
        const response = await fetch(`${API_BASE_URL}/screen-resume`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || "API request failed");
        }

        const educationDisplay = Array.isArray(data.education)
            ? data.education.join(", ")
            : (data.education || "Not Specified");

        const candidateName = data.candidate_name && data.candidate_name !== "Not found"
            ? data.candidate_name
            : data.resume;

        result.innerHTML = `
            <div class="result-header">
                <div>
                    <h2>Candidate Analysis: ${candidateName}</h2>
                    <p>
                        File: <b>${data.resume}</b>
                        ${data.candidate_email && data.candidate_email !== 'Not found' ? ` &bull; Email: <b>${data.candidate_email}</b>` : ''}
                        ${data.candidate_phone && data.candidate_phone !== 'Not found' ? ` &bull; Phone: <b>${data.candidate_phone}</b>` : ''}
                    </p>
                </div>
                <div>
                    <span class="candidate-status ${data.status === 'Shortlisted' ? 'status-shortlisted' : 'status-review'}" style="font-size: 14px; padding: 8px 16px;">
                        ${data.status}
                    </span>
                </div>
            </div>

            <!-- Score Cards -->
            <div class="score-grid">
                <div class="score-card">
                    <h3>Skill Score</h3>
                    <div class="score">${data.skill_score}%</div>
                </div>
                <div class="score-card">
                    <h3>Rule-Based Score</h3>
                    <div class="score">${data.rule_based_score}</div>
                </div>
                <div class="score-card">
                    <h3>TF-IDF Similarity</h3>
                    <div class="score">${data.tfidf_score}</div>
                </div>
                <div class="score-card">
                    <h3>Overall Match</h3>
                    <div class="score">${data.combined_score}</div>
                </div>
            </div>

            <!-- Candidate Information -->
            <div class="info-grid">
                <div class="info-card">
                    <h3>Matched Required Skills (${data.matched_skills.length})</h3>
                    <ul>
                        ${data.matched_skills.length > 0
                            ? data.matched_skills.map(s => `<li>${s}</li>`).join("")
                            : "<li>No matched skills</li>"
                        }
                    </ul>
                </div>

                <div class="info-card">
                    <h3>Missing Required Skills (${data.missing_skills.length})</h3>
                    <ul>
                        ${data.missing_skills.length > 0
                            ? data.missing_skills.map(s => `<li style="color: #ef4444;">${s}</li>`).join("")
                            : "<li>No missing skills</li>"
                        }
                    </ul>
                </div>

                <div class="info-card">
                    <h3>Experience</h3>
                    <p>Candidate: <b>${data.experience}</b></p>
                    <p>Required: <b>${data.required_experience}+ Years</b></p>
                    <p>Match: <b>${data.experience_match}</b></p>
                </div>

                <div class="info-card">
                    <h3>Education</h3>
                    <p>Extracted: <b>${educationDisplay}</b></p>
                    <p>Required: <b>${data.required_education}</b></p>
                    <p>Match: <b>${data.education_match}</b></p>
                </div>
            </div>
        `;

        status.innerHTML = `
            <div style="margin-top: 12px; color: #047857; font-weight: 500;">
                <i class="fa-solid fa-circle-check"></i>
                Resume screening completed successfully.
            </div>
        `;

        // Refresh stats on dashboard
        loadDashboardStats();

    } catch (error) {
        status.innerHTML = `
            <div style="margin-top: 12px; color: #dc2626; font-weight: 500;">
                <i class="fa-solid fa-triangle-exclamation"></i>
                ${error.message || "Error connecting to the FastAPI server."}
            </div>
        `;
        console.error(error);
    }
}
