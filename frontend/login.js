const API_BASE_URL = (() => {
    const stored = localStorage.getItem("resumeAI_backend_url");
    if (stored) return stored.replace(/\/+$/, "");
    if (window.location.port === "5500" || window.location.protocol === "file:") {
        return "http://127.0.0.1:8000";
    }
    return window.location.origin;
})();

const loginForm = document.getElementById("loginForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const togglePassword = document.getElementById("togglePassword");
const loginMessage = document.getElementById("loginMessage");

togglePassword.addEventListener("click", function () {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePassword.classList.remove("fa-eye");
        togglePassword.classList.add("fa-eye-slash");
    } else {
        passwordInput.type = "password";
        togglePassword.classList.remove("fa-eye-slash");
        togglePassword.classList.add("fa-eye");
    }
});

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    loginMessage.innerHTML = "";

    const submitBtn = loginForm.querySelector("button[type='submit']");
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Signing in...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok && data.token) {
            sessionStorage.setItem("resumeAI_loggedIn", "true");
            sessionStorage.setItem("resumeAI_token", data.token);
            sessionStorage.setItem("resumeAI_admin", data.user.email);
            window.location.href = "index.html";
            return;
        } else {
            loginMessage.innerHTML = `
                <div class="login-error">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    ${data.detail || "Invalid email or password."}
                </div>
            `;
        }
    } catch (err) {
        // Fallback for offline local demo
        if (email === "admin@resumeai.com" && password === "admin123") {
            sessionStorage.setItem("resumeAI_loggedIn", "true");
            sessionStorage.setItem("resumeAI_admin", email);
            window.location.href = "index.html";
            return;
        }
        loginMessage.innerHTML = `
            <div class="login-error">
                <i class="fa-solid fa-circle-exclamation"></i>
                Cannot connect to backend server. Make sure FastAPI is running on port 8000.
            </div>
        `;
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});
