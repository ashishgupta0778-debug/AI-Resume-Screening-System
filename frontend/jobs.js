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


// ================= ANALYZE & SAVE JOB =================

async function analyzeJob() {
    const title = document.getElementById("jobTitle").value.trim();
    const description = document.getElementById("jobDescription").value.trim();
    const reqSkillsRaw = document.getElementById("requiredSkillsInput").value.trim();
    const prefSkillsRaw = document.getElementById("preferredSkillsInput").value.trim();
    const experience = parseInt(document.getElementById("experience").value) || 0;
    const education = document.getElementById("education").value;
    const result = document.getElementById("jobResult");

    if (!title || !description) {
        alert("Please provide both Job Title and Description.");
        return;
    }

    let requiredSkills = reqSkillsRaw
        ? reqSkillsRaw.split(",").map(s => s.trim().toLowerCase()).filter(Boolean)
        : [];

    let preferredSkills = prefSkillsRaw
        ? prefSkillsRaw.split(",").map(s => s.trim().toLowerCase()).filter(Boolean)
        : [];

    // Fallback auto-detection if required skills not explicitly typed
    if (requiredSkills.length === 0) {
        const skillsList = [
            "python", "java", "c++", "c#", "sql", "html", "css",
            "javascript", "react", "node.js", "machine learning",
            "deep learning", "communication", "problem solving",
            "database", "databases", "apis", "git", "github",
            "mongodb", "mysql", "excel", "power bi", "aws", "docker"
        ];
        const lowerDesc = description.toLowerCase();
        requiredSkills = skillsList.filter(s => lowerDesc.includes(s));
    }

    const jobData = {
        title: title,
        description: description,
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        min_experience: experience,
        education: education || "Not Specified"
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/jobs`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jobData)
        });

        if (!response.ok) {
            throw new Error("Failed to save job description.");
        }

        const data = await response.json();

        result.innerHTML = `
            <div class="result-header">
                <div>
                    <h2>Job Created: ${title}</h2>
                    <p>Successfully saved to database with AI requirement mapping.</p>
                </div>
                <div>
                    <button class="screen-btn" onclick="useJobForScreening(${data.job.id})" style="margin: 0; padding: 10px 18px; font-size: 13px;">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Screen Candidates for this Job
                    </button>
                </div>
            </div>

            <div class="info-grid">
                <div class="info-card">
                    <h3>Required Skills (${requiredSkills.length})</h3>
                    <div class="skill-tags" style="margin-top: 6px;">
                        ${requiredSkills.length > 0
                            ? requiredSkills.map(s => `<span>${s}</span>`).join("")
                            : "<span>None configured</span>"
                        }
                    </div>
                </div>

                <div class="info-card">
                    <h3>Preferred Skills (${preferredSkills.length})</h3>
                    <div class="skill-tags" style="margin-top: 6px;">
                        ${preferredSkills.length > 0
                            ? preferredSkills.map(s => `<span>${s}</span>`).join("")
                            : "<span>None configured</span>"
                        }
                    </div>
                </div>

                <div class="info-card">
                    <h3>Minimum Experience</h3>
                    <p><b>${experience}+ Years</b> of relevant experience</p>
                </div>

                <div class="info-card">
                    <h3>Education Requirement</h3>
                    <p><b>${education || 'Not Specified'}</b></p>
                </div>
            </div>
        `;

        // Clear input form
        document.getElementById("jobForm").reset();

        // Refresh list
        loadJobs();

    } catch (e) {
        console.error(e);
        alert("Error saving job. Please ensure the backend is running.");
    }
}


// ================= LOAD SAVED JOBS =================

async function loadJobs() {
    const container = document.getElementById("savedJobs");
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/jobs`);
        if (!response.ok) throw new Error("Could not fetch jobs");

        const jobs = await response.json();
        renderJobsList(jobs);

    } catch (e) {
        console.warn(e);
        container.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <h2>Could not load jobs</h2>
                <p>Ensure the FastAPI server is running.</p>
            </div>
        `;
    }
}


function renderJobsList(jobs) {
    const container = document.getElementById("savedJobs");
    if (!container) return;

    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-result">
                <div class="empty-icon"><i class="fa-solid fa-briefcase"></i></div>
                <h2>No jobs created yet</h2>
                <p>Use the form above to add your first job opening.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = jobs.map(job => {
        const reqCount = Array.isArray(job.required_skills) ? job.required_skills.length : 0;
        const prefCount = Array.isArray(job.preferred_skills) ? job.preferred_skills.length : 0;

        return `
            <div class="job-item">
                <div style="flex: 1;">
                    <h3>${job.title}</h3>
                    <p style="margin-bottom: 4px;">
                        ${reqCount} required skill(s)
                        ${prefCount > 0 ? ` &bull; ${prefCount} preferred skill(s)` : ''}
                        &bull; Experience: <b>${job.min_experience}+ yrs</b>
                        &bull; Education: <b>${job.education}</b>
                    </p>
                    <small style="color: #64748b;">Created: ${job.created_at || 'Recently'}</small>
                </div>

                <div style="display: flex; align-items: center; gap: 8px;">
                    <button
                        class="screen-btn"
                        style="margin: 0; padding: 8px 14px; font-size: 13px;"
                        onclick="useJobForScreening(${job.id})"
                    >
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Screen Resumes
                    </button>

                    <button
                        class="delete-btn"
                        title="Delete Job Description"
                        onclick="deleteJob(${job.id})"
                    >
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join("");
}


// ================= ACTIONS =================

function useJobForScreening(jobId) {
    window.location.href = `candidates.html?job_id=${jobId}`;
}


async function deleteJob(id) {
    if (!confirm("Are you sure you want to delete this job description?")) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/jobs/${id}`, {
            method: "DELETE"
        });
        if (response.ok) {
            loadJobs();
        } else {
            alert("Could not delete job.");
        }
    } catch (e) {
        console.error(e);
        alert("Error connecting to server.");
    }
}

document.addEventListener("DOMContentLoaded", loadJobs);
