document.addEventListener("DOMContentLoaded", () => {
  const depositPanel = document.getElementById("deposit-panel");
  const accountOverview = document.getElementById("account-overview");
  const crumbDeposit = document.getElementById("crumb-deposit");
  const depositTriggers = document.querySelectorAll('[data-action="show-deposit"]');

  const openDepositPanel = () => {
    if (!depositPanel) {
      return;
    }
    depositPanel.classList.remove("is-hidden");
    accountOverview?.classList.add("is-hidden");
    crumbDeposit?.classList.add("is-active");
    depositPanel.scrollIntoView({ block: "start", behavior: "smooth" });
  };

  depositTriggers.forEach((trigger) => {
    trigger.addEventListener("click", openDepositPanel);
  });

  const mapScript = document.getElementById("address-map");
  const assetSelect = document.getElementById("asset-select");
  const chainSelect = document.getElementById("chain-select");
  const addressBox = document.getElementById("deposit-address");
  const qrImage = document.getElementById("deposit-qr");
  const copyButton = document.querySelector('[data-action="copy-address"]');
  let addressMap = {};

  if (mapScript?.textContent) {
    try {
      addressMap = JSON.parse(mapScript.textContent);
    } catch (error) {
      console.warn("Unable to parse deposit address map", error);
    }
  }

  const updateAssetDetails = () => {
    if (!assetSelect || !addressBox || !addressMap) {
      return;
    }
    const asset = assetSelect.value;
    const info = addressMap[asset];
    if (!info) {
      return;
    }

    addressBox.textContent = info.address;
    if (qrImage && info.qr) {
      qrImage.src = info.qr;
      qrImage.alt = `${asset} deposit QR`;
    }
    if (chainSelect && info.chain) {
      chainSelect.value = info.chain;
    }

    const tip = depositPanel?.querySelector(".c-024");
    if (tip) {
      tip.textContent = `Security tip: Only send ${asset} to this address. Assets sent here are credited automatically.`;
    }
  };

  if (assetSelect) {
    assetSelect.addEventListener("change", updateAssetDetails);
    updateAssetDetails();
  }

  if (copyButton && addressBox) {
    const defaultText = copyButton.textContent;
    copyButton.addEventListener("click", async () => {
      const address = addressBox.textContent?.trim();
      if (!address) {
        return;
      }
      try {
        await navigator.clipboard?.writeText(address);
      } catch (error) {
        console.warn("Clipboard unavailable", error);
      }
      copyButton.classList.add("copied");
      copyButton.textContent = "Copied";
      setTimeout(() => {
        copyButton.classList.remove("copied");
        copyButton.textContent = defaultText ?? "Copy address";
      }, 1600);
    });
  }

  const registerForm = document.querySelector(".auth-form");
  const agreeBox = document.getElementById("agree-box");
  const signupBtn = document.getElementById("signup-btn");

  if (registerForm && signupBtn && agreeBox && registerForm.action.includes("register")) {
    const requiredFields = registerForm.querySelectorAll("[data-required='true']");
    const updateButtonState = () => {
      const filled = Array.from(requiredFields).every(
        (input) => input.value && input.value.trim().length > 0,
      );
      signupBtn.disabled = !(filled && agreeBox.checked);
    };
    requiredFields.forEach((input) => {
      input.addEventListener("input", updateButtonState);
    });
    agreeBox.addEventListener("change", updateButtonState);
    updateButtonState();
  }
});
