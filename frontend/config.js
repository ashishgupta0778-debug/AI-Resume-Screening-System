// ==========================================
// AI Resume Screening System - Production Config
// ==========================================

window.APP_CONFIG = {
    // Default live FastAPI backend hosted on Render
    BACKEND_URL: "https://ai-resume-screening-system-nfks.onrender.com",

    // Fallback local development backend
    LOCAL_BACKEND_URL: "http://127.0.0.1:8000"
};

// Helper to determine the active API Base URL
window.getApiBaseUrl = function () {
    // 1. User manual override saved in localStorage
    const stored = localStorage.getItem("resumeAI_backend_url");
    if (stored && stored.trim()) {
        return stored.trim().replace(/\/+$/, "");
    }

    // 2. Local development on VS Code Live Server or raw file
    if (window.location.port === "5500" || window.location.protocol === "file:") {
        return window.APP_CONFIG.LOCAL_BACKEND_URL;
    }

    // 3. Localhost or 127.0.0.1 direct FastAPI access
    if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
        return window.location.origin;
    }

    // 4. Remote / Netlify production: use the live Render backend
    if (window.APP_CONFIG && window.APP_CONFIG.BACKEND_URL) {
        return window.APP_CONFIG.BACKEND_URL.replace(/\/+$/, "");
    }

    return window.location.origin;
};
