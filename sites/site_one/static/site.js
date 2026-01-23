document.addEventListener("DOMContentLoaded", () => {
  const accountOverview = document.getElementById("account-overview");
  const crumbDeposit = document.getElementById("crumb-deposit");
  const depositTriggers = document.querySelectorAll('[data-action="show-deposit"]');
  const depositPanelContainer = document.getElementById("deposit-panel-container");

  const depositState = {
    panel: null,
    assetSelect: null,
    chainSelect: null,
    addressBox: null,
    qrImage: null,
    copyButton: null,
    addressMap: null,
    loadPromise: null,
  };

  const parseAddressMap = () => {
    if (!depositPanelContainer) {
      return;
    }
    const mapScript = depositPanelContainer.querySelector("[data-address-map='true']");
    if (!mapScript?.textContent) {
      return;
    }
    try {
      depositState.addressMap = JSON.parse(mapScript.textContent);
    } catch (error) {
      console.warn("Unable to parse deposit address map", error);
      depositState.addressMap = null;
    }
    mapScript.remove();
  };

  const updateAssetDetails = () => {
    const { assetSelect, addressBox, addressMap } = depositState;
    if (!assetSelect || !addressBox || !addressMap) {
      return;
    }
    const asset = assetSelect.value;
    const info = addressMap[asset];
    if (!info) {
      return;
    }

    addressBox.textContent = info.address;
    if (depositState.qrImage && info.qr) {
      depositState.qrImage.src = info.qr;
      depositState.qrImage.alt = `${asset} deposit QR`;
    }
    if (depositState.chainSelect && info.chain) {
      depositState.chainSelect.value = info.chain;
    }

    const tip = depositState.panel?.querySelector(".c-024");
    if (tip) {
      tip.textContent = `Security tip: Only send ${asset} to this address. Assets sent here are credited automatically.`;
    }
  };

  const bindCopyButton = () => {
    const { copyButton, addressBox } = depositState;
    if (!copyButton || !addressBox) {
      return;
    }
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
  };

  const initDepositPanel = () => {
    if (!depositPanelContainer) {
      return null;
    }
    depositState.panel = depositPanelContainer.querySelector("#deposit-panel");
    if (!depositState.panel) {
      return null;
    }
    depositState.assetSelect = depositState.panel.querySelector("#asset-select");
    depositState.chainSelect = depositState.panel.querySelector("#chain-select");
    depositState.addressBox = depositState.panel.querySelector("#deposit-address");
    depositState.qrImage = depositState.panel.querySelector("#deposit-qr");
    depositState.copyButton = depositState.panel.querySelector('[data-action="copy-address"]');

    parseAddressMap();
    if (depositState.assetSelect) {
      depositState.assetSelect.addEventListener("change", updateAssetDetails);
    }
    bindCopyButton();
    updateAssetDetails();
    return depositState.panel;
  };

  const loadDepositPanel = () => {
    if (depositState.panel) {
      return Promise.resolve(depositState.panel);
    }
    if (!depositPanelContainer) {
      return Promise.resolve(null);
    }
    if (depositState.loadPromise) {
      return depositState.loadPromise;
    }
    const url = depositPanelContainer.dataset.panelUrl;
    if (!url) {
      return Promise.resolve(null);
    }
    depositState.loadPromise = fetch(url, {
      credentials: "include",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Deposit panel request failed: ${response.status}`);
        }
        return response.text();
      })
      .then((html) => {
        depositPanelContainer.innerHTML = html;
        return initDepositPanel();
      })
      .catch((error) => {
        console.warn("Unable to load deposit panel", error);
        return null;
      });
    return depositState.loadPromise;
  };

  const openDepositPanel = () => {
    loadDepositPanel().then((panel) => {
      if (!panel) {
        return;
      }
      panel.classList.remove("is-hidden");
      accountOverview?.classList.add("is-hidden");
      crumbDeposit?.classList.add("is-active");
      updateAssetDetails();
      panel.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  };

  depositTriggers.forEach((trigger) => {
    trigger.addEventListener("click", openDepositPanel);
  });

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
