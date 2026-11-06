async function submitJson(event, endpoint, messageElement) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Unable to complete sign-in.");
    window.location.assign(result.redirect || `/dashboard/${result.customer.role}`);
  } catch (error) {
    messageElement.textContent = error.message;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.querySelector("#loginPageForm");
  if (loginForm) {
    loginForm.addEventListener("submit", event =>
      submitJson(event, "/api/auth/login", document.querySelector("#loginMessage"))
    );
    const selectedRole = new URLSearchParams(window.location.search).get("role");
    if (["admin", "chef", "delivery_partner", "customer"].includes(selectedRole)) {
      const option = loginForm.querySelector(`[name="role"][value="${selectedRole}"]`);
      if (option) option.checked = true;
    }
  }
  const signupForm = document.querySelector("#signupPageForm");
  if (signupForm) {
    signupForm.addEventListener("submit", event =>
      submitJson(event, "/api/auth/register", document.querySelector("#signupMessage"))
    );
  }
});
