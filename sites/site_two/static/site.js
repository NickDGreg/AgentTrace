document.addEventListener("DOMContentLoaded", () => {
  const closeModalButton = document.querySelector("[data-close-modal]");
  if (closeModalButton) {
    closeModalButton.addEventListener("click", () => {
      const modal = document.getElementById("notice-modal");
      if (modal) {
        modal.remove();
      }
    });
  }

  const copyButtons = document.querySelectorAll("[data-copy-target]");
  copyButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const targetId = button.getAttribute("data-copy-target");
      if (!targetId) {
        return;
      }
      const input = document.getElementById(targetId);
      if (!input) {
        return;
      }

      const value = input.value.trim();
      if (!value) {
        return;
      }

      try {
        await navigator.clipboard.writeText(value);
      } catch (_error) {
        input.select();
        document.execCommand("copy");
      }

      const original = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = original;
      }, 1200);
    });
  });

  const password = document.getElementById("password");
  const passwordConfirm = document.getElementById("password_confirm");
  const message = document.getElementById("password-match-message");
  if (password && passwordConfirm && message) {
    const syncPasswordMessage = () => {
      if (!passwordConfirm.value) {
        message.textContent = "";
        return;
      }
      if (password.value === passwordConfirm.value) {
        message.textContent = "";
      } else {
        message.textContent = "Passwords do not match.";
      }
    };
    password.addEventListener("input", syncPasswordMessage);
    passwordConfirm.addEventListener("input", syncPasswordMessage);
  }
});
