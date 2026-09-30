function analyzeJob() {
    const title = document.getElementById("jobTitle").value.trim();
    const description = document.getElementById("jobDescription").value.trim();
    const experience = document.getElementById("experience").value;
    const education = document.getElementById("education").value;
    const result = document.getElementById("jobResult");

    if (!title || !description) {
        result.innerHTML = `
            <div class="result-header">
                <h2>Missing Information</h2>
                <p>Please enter Job Title and Job Description.</p>
            </div>`;
        return;
    }

    const skillsList = [
        "python", "java", "c++", "c#", "sql", "html", "css",
        "javascript", "react", "node.js", "machine learning",
        "deep learning", "communication", "problem solving",
        "database", "databases", "apis", "git", "github",
        "mongodb", "mysql", "excel", "power bi", "aws", "docker"
    ];

    const lowerDescription = description.toLowerCase();

    const extractedSkills = skillsList.filter(skill =>
        lowerDescription.includes(skill)
    );

    let detectedExperience = experience;

    const experienceMatch = lowerDescription.match(
        /(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience/
    );

    if (!detectedExperience && experienceMatch) {
        detectedExperience = experienceMatch[1];
    }

    let detectedEducation = education;

    if (!detectedEducation) {
        if (
            lowerDescription.includes("bachelor") ||
            lowerDescription.includes("b.tech") ||
            lowerDescription.includes("btech") ||
            lowerDescription.includes("b.e")
        ) {
            detectedEducation = "Bachelor's Degree";
        } else if (
            lowerDescription.includes("master") ||
            lowerDescription.includes("m.tech") ||
            lowerDescription.includes("mtech") ||
            lowerDescription.includes("mca")
        ) {
            detectedEducation = "Master's Degree";
        }
    }

    const job = {
        id: Date.now(),
        title,
        description,
        skills: extractedSkills,
        experience: detectedExperience || "Not Specified",
        education: detectedEducation || "Not Specified",
        createdAt: new Date().toLocaleDateString()
    };

    const jobs = JSON.parse(
        localStorage.getItem("resumeAI_jobs") || "[]"
    );

    jobs.push(job);

    localStorage.setItem("resumeAI_jobs", JSON.stringify(jobs));

    result.innerHTML = `
        <div class="result-header">
            <h2>AI Job Analysis</h2>
            <p>Job: <b>${title}</b></p>
        </div>

        <div class="info-grid">
            <div class="info-card">
                <h3>Extracted Skills</h3>
                ${
                    extractedSkills.length
                        ? `<ul>${extractedSkills.map(
                            skill => `<li>${skill}</li>`
                        ).join("")}</ul>`
                        : "<p>No matching skills detected.</p>"
                }
            </div>

            <div class="info-card">
                <h3>Required Experience</h3>
                <p>${detectedExperience || "Not Specified"} ${
                    detectedExperience ? "Years" : ""
                }</p>
            </div>

            <div class="info-card">
                <h3>Education</h3>
                <p>${detectedEducation || "Not Specified"}</p>
            </div>

            <div class="info-card">
                <h3>Analysis Status</h3>
                <p>Job description analyzed successfully.</p>
                <p>${extractedSkills.length} relevant skills detected.</p>
            </div>
        </div>
    `;

    loadJobs();
}

function loadJobs() {
    const container = document.getElementById("savedJobs");

    if (!container) return;

    const jobs = JSON.parse(
        localStorage.getItem("resumeAI_jobs") || "[]"
    );

    if (jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-icon">
                <i class="fa-solid fa-briefcase"></i>
            </div>
            <h2>No jobs created yet</h2>
            <p>Create your first job description above.</p>`;
        return;
    }

    container.innerHTML = jobs.map(job => `
        <div class="job-item">
            <div>
                <h3>${job.title}</h3>
                <p>
                    ${job.skills.length} skills detected
                    &bull; ${job.experience}
                    ${job.experience !== "Not Specified" ? " Years" : ""}
                </p>
                <small>Created: ${job.createdAt}</small>
            </div>

            <button class="delete-btn" onclick="deleteJob(${job.id})">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `).join("");
}

function deleteJob(id) {
    let jobs = JSON.parse(
        localStorage.getItem("resumeAI_jobs") || "[]"
    );

    jobs = jobs.filter(job => job.id !== id);

    localStorage.setItem("resumeAI_jobs", JSON.stringify(jobs));

    loadJobs();
}

document.addEventListener("DOMContentLoaded", loadJobs);