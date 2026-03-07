function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function initPasswordMessage() {
  const password = document.getElementById("password");
  const passwordConfirm = document.getElementById("password_confirm");
  const message = document.getElementById("password-match-message");
  if (!password || !passwordConfirm || !message) {
    return;
  }
  const syncMessage = () => {
    if (!passwordConfirm.value) {
      message.textContent = "";
      return;
    }
    if (password.value === passwordConfirm.value) {
      message.textContent = "Passwords match.";
      message.classList.add("ok");
      message.classList.remove("error");
      return;
    }
    message.textContent = "Passwords do not match.";
    message.classList.add("error");
    message.classList.remove("ok");
  };
  password.addEventListener("input", syncMessage);
  passwordConfirm.addEventListener("input", syncMessage);
}

function renderTopNav(state, activeKey) {
  const items = Array.isArray(state.navItems) ? state.navItems : [];
  const nav = items
    .map((item) => {
      const isActive = item.key === activeKey;
      return `<a class="${isActive ? "active" : ""}" href="${escapeHtml(
        item.href
      )}">${escapeHtml(item.label)}</a>`;
    })
    .join("");

  return `
    <header class="cfd-topbar">
      <a class="cfd-logo" href="/dashboard">
        <span class="brand-main">TITAN TRADE</span>
        <span class="brand-sub">GLOBAL LTD</span>
      </a>
      <nav class="cfd-nav">${nav}</nav>
      <div class="cfd-meta">
        <span>EN</span>
        <span class="balance-chip">$0.00</span>
        <span class="avatar">${escapeHtml(
          (state.user && state.user.display_name || "U").slice(0, 1).toUpperCase()
        )}</span>
      </div>
    </header>
  `;
}

function renderFooter() {
  return `
    <footer class="cfd-footer">
      <div class="cfd-footer-left">
        <span class="brand-main">TITAN TRADE</span>
        <span class="brand-sub">GLOBAL LTD</span>
      </div>
      <div class="cfd-footer-links">
        <a href="/trade-view">Exchange</a>
        <a href="/trade">Market</a>
        <a href="/contact-us">Contact us</a>
      </div>
      <div class="cfd-footer-copy">Copyright © 2026 TITAN LLC. All rights reserved.</div>
    </footer>
  `;
}

function renderDashboardPage(payload) {
  return `
    <section class="dashboard-overview">
      <h1>${escapeHtml(payload.headline || "Dashboard")}</h1>
      <p>${escapeHtml(payload.subline || "")}</p>
      <div class="overview-grid">
        <article>
          <h3>Total Balance</h3>
          <p>${escapeHtml(payload.balance || "$0.00")}</p>
        </article>
        <article>
          <h3>Equity</h3>
          <p>${escapeHtml(payload.equity || "$0.00")}</p>
        </article>
        <article>
          <h3>Open Positions</h3>
          <p>${escapeHtml(String(payload.open_positions || 0))}</p>
        </article>
      </div>
    </section>
  `;
}

function renderSimplePage(payload) {
  return `
    <section class="simple-card">
      <h1>${escapeHtml(payload.headline || "Section")}</h1>
      <p>${escapeHtml(payload.subline || "")}</p>
      <div class="simple-table">
        <div><span>Status</span><b>Online</b></div>
        <div><span>Last update</span><b>${new Date().toLocaleString()}</b></div>
        <div><span>Account model</span><b>Retail CFD</b></div>
      </div>
    </section>
  `;
}

function renderWalletOverview(payload) {
  const showModal = payload.modal === "withdraw";
  return `
    <section class="wallet-page">
      <h1>Wallet Overview</h1>
      <p>Manage deposits, withdrawals, and available account balances.</p>
      <div class="overview-grid">
        <article><h3>Balance</h3><p>${escapeHtml(payload.balance || "$0.00")}</p></article>
        <article><h3>Equity</h3><p>${escapeHtml(payload.equity || "$0.00")}</p></article>
        <article><h3>Available</h3><p>$0.00</p></article>
      </div>
      <a class="link-btn" href="/wallet-overview?modal=withdraw">Open withdrawal modal</a>
    </section>
    ${
      showModal
        ? `
      <div class="modal-backdrop" id="withdraw-modal">
        <div class="modal-card">
          <button class="modal-close" id="close-withdraw-modal" type="button">×</button>
          <h2>Withdrawal Request</h2>
          <p>Submit your destination wallet or account details.</p>
          <form class="modal-form">
            <label>Amount <input type="number" min="20" step="0.01" placeholder="100.00"></label>
            <label>Method
              <select>
                <option>Bank Transfer</option>
                <option>Bitcoin</option>
                <option>Ethereum</option>
              </select>
            </label>
            <label>Destination <input type="text" placeholder="Wallet / Account"></label>
            <button type="button" id="submit-withdraw-button">Submit Request</button>
          </form>
          <div class="inline-note" id="withdraw-note"></div>
        </div>
      </div>
    `
        : ""
    }
  `;
}

function attachWalletHandlers(root) {
  const close = root.querySelector("#close-withdraw-modal");
  if (close) {
    close.addEventListener("click", () => {
      const modal = root.querySelector("#withdraw-modal");
      if (modal) {
        modal.remove();
      }
    });
  }
  const submit = root.querySelector("#submit-withdraw-button");
  if (submit) {
    submit.addEventListener("click", () => {
      const note = root.querySelector("#withdraw-note");
      if (note) {
        note.textContent = "Request submitted for operations review.";
      }
    });
  }
}

function renderDepositBase(payload) {
  const min = Number(payload.minAmount || 1);
  const max = Number(payload.maxAmount || 1000000);
  return `
    <section class="deposit-layout" data-min="${min}" data-max="${max}">
      <aside class="deposit-steps">
        <h2>Deposit</h2>
        <ol>
          <li class="active">Select methods</li>
          <li>Deposit details</li>
        </ol>
      </aside>
      <div class="deposit-main">
        <h1>Deposit</h1>
        <p id="method-subtitle">on Crypto</p>
        <div class="total-balance">
          <span>Total Balance</span>
          <b>${escapeHtml(payload.balance || "$0.00")}</b>
        </div>
        <div id="deposit-stage"></div>
      </div>
    </section>
  `;
}

function renderMethodCards() {
  const rows = [
    ["crypto", "Crypto", "Bitcoin, Ethereum & more"],
    ["amex", "American Express", "Visa, Mastercard"],
    ["card", "Credit or Debit Card", "Visa, Mastercard"],
    ["bank", "Bank Transfer", "Bank transfer"],
  ];
  return `
    <div class="method-list">
      ${rows
        .map(
          ([key, title, sub]) => `
        <button class="method-row" type="button" data-method="${key}">
          <span>
            <b>${escapeHtml(title)}</b>
            <small>${escapeHtml(sub)}</small>
          </span>
          <i>›</i>
        </button>
      `
        )
        .join("")}
    </div>
  `;
}

function renderCardForm(selectedMethod) {
  const subtitle = selectedMethod === "amex" ? "Credit/Debit Card cc-ext" : "Credit/Debit Card";
  return `
    <div class="card-form-block">
      <h2>Credit/Debit Card</h2>
      <p class="inline-note">${escapeHtml(subtitle)}</p>
      <label>Card Number <input type="text" placeholder="XXXX XXXXXXX XXXXX"></label>
      <label>Card Holder <input type="text" placeholder="John Doe"></label>
      <div class="form-split">
        <label>Expiration Date <input type="text" placeholder="MM / YY"></label>
        <label>CVC <input type="text" placeholder="CVC"></label>
      </div>
      <div class="form-split">
        <label>Amount <input type="text" placeholder="USD"></label>
        <label>Currency
          <select><option>USD</option><option>EUR</option><option>GBP</option></select>
        </label>
      </div>
      <div class="inline-note">Deposit amount range: $1.00 - $1,000,000.00</div>
      <div class="button-row">
        <button type="button" class="continue-btn">Continue</button>
      </div>
    </div>
  `;
}

function renderBankForm() {
  return `
    <div class="card-form-block">
      <h2>Bank Transfer</h2>
      <p class="inline-note">Wire details are provided after submitting transfer intent.</p>
      <label>Transfer Amount <input type="number" min="1" step="0.01" placeholder="1000"></label>
      <label>Reference Note <input type="text" placeholder="Your account email"></label>
      <div class="button-row">
        <button type="button" class="continue-btn">Continue</button>
      </div>
    </div>
  `;
}

function renderCryptoDetails(assetOptions) {
  const options = (assetOptions || ["Bitcoin", "Ethereum", "Bitcoin Cash"])
    .map((asset) => `<option>${escapeHtml(asset)}</option>`)
    .join("");
  return `
    <div class="crypto-form-block">
      <div class="inline-note">Deposit amount range: $1.00 - $1,000,000.00</div>
      <label>Enter Deposit Amount
        <input id="crypto-amount" type="number" min="1" max="1000000" step="0.01" value="1000">
      </label>
      <label>Select Asset
        <select id="crypto-asset">${options}</select>
      </label>
      <div class="button-row">
        <button id="crypto-next" type="button">Next</button>
      </div>
      <div class="inline-note error" id="deposit-error"></div>
    </div>
  `;
}

function renderCryptoWallet(data) {
  return `
    <div class="wallet-block">
      <div class="qr-wrap">
        <img src="${escapeHtml(data.qr_data_uri)}" alt="${escapeHtml(data.chain)} wallet qr">
      </div>
      <div class="address-row">
        <input id="wallet-address-field" type="text" readonly value="${escapeHtml(
          data.address
        )}">
        <button type="button" id="copy-wallet-btn">Copy</button>
      </div>
      <p class="inline-note">Network: ${escapeHtml(data.asset)} (${escapeHtml(data.chain)})</p>
    </div>
  `;
}

function setupDepositFlow(root, state) {
  const stage = root.querySelector("#deposit-stage");
  const subtitle = root.querySelector("#method-subtitle");
  const shell = root.querySelector(".deposit-layout");
  if (!stage || !subtitle || !shell) {
    return;
  }

  const minAmount = Number(shell.getAttribute("data-min") || "1");
  const maxAmount = Number(shell.getAttribute("data-max") || "1000000");
  let selectedMethod = "crypto";
  let walletData = null;

  const render = () => {
    if (selectedMethod === "crypto") {
      subtitle.textContent = "on Crypto";
      stage.innerHTML = walletData
        ? renderCryptoWallet(walletData)
        : renderCryptoDetails(state.assetOptions);
    } else if (selectedMethod === "amex" || selectedMethod === "card") {
      subtitle.textContent = selectedMethod === "amex" ? "Credit/Debit Card cc-ext" : "Credit/Debit Card";
      stage.innerHTML = renderCardForm(selectedMethod);
    } else {
      subtitle.textContent = "on Bank transfer";
      stage.innerHTML = renderBankForm();
    }

    const methodList = root.querySelector(".method-list");
    if (methodList) {
      methodList.remove();
    }
    stage.insertAdjacentHTML("afterbegin", renderMethodCards());

    stage.querySelectorAll(".method-row").forEach((button) => {
      button.addEventListener("click", () => {
        selectedMethod = button.getAttribute("data-method") || "crypto";
        walletData = null;
        render();
      });
    });

    const cryptoNext = root.querySelector("#crypto-next");
    if (cryptoNext) {
      cryptoNext.addEventListener("click", async () => {
        const amountInput = root.querySelector("#crypto-amount");
        const assetSelect = root.querySelector("#crypto-asset");
        const errorNode = root.querySelector("#deposit-error");
        if (!amountInput || !assetSelect || !errorNode) {
          return;
        }
        const amount = Number(amountInput.value);
        if (!Number.isFinite(amount) || amount < minAmount || amount > maxAmount) {
          errorNode.textContent = `Deposit amount must be between $${minAmount.toFixed(
            2
          )} and $${maxAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}.`;
          return;
        }
        errorNode.textContent = "Requesting wallet address...";
        try {
          const response = await fetch(
            `/api/deposit/address?asset=${encodeURIComponent(assetSelect.value)}&amount=${encodeURIComponent(
              amount.toFixed(2)
            )}`,
            { headers: { Accept: "application/json" } }
          );
          const body = await response.json();
          if (!response.ok) {
            errorNode.textContent = body.error || "Failed to load wallet address.";
            return;
          }
          walletData = body;
          render();
        } catch (_error) {
          errorNode.textContent = "Network error while requesting wallet address.";
        }
      });
    }

    const copyButton = root.querySelector("#copy-wallet-btn");
    if (copyButton) {
      copyButton.addEventListener("click", async () => {
        const input = root.querySelector("#wallet-address-field");
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
        copyButton.textContent = "Copied";
        setTimeout(() => {
          copyButton.textContent = "Copy";
        }, 900);
      });
    }

    const continueBtn = root.querySelector(".continue-btn");
    if (continueBtn) {
      continueBtn.addEventListener("click", () => {
        continueBtn.textContent = "Submitted";
      });
    }
  };

  render();
}

function renderCfdApp(root, state) {
  const payload = state.payload || {};
  const page = state.page || "dashboard";
  const activeKey = payload.activeNav || "trade";

  let content = "";
  if (page === "deposit") {
    content = renderDepositBase(payload);
  } else if (page === "wallet-overview") {
    content = renderWalletOverview(payload);
  } else if (page === "simple-page") {
    content = renderSimplePage(payload);
  } else {
    content = renderDashboardPage(payload);
  }

  root.innerHTML = `
    <div class="cfd-app">
      ${renderTopNav(state, activeKey)}
      <main class="cfd-main">${content}</main>
      ${renderFooter()}
    </div>
  `;

  if (page === "deposit") {
    setupDepositFlow(root, state);
  }
  if (page === "wallet-overview") {
    attachWalletHandlers(root);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initPasswordMessage();

  const stateNode = document.getElementById("initial-state");
  const root = document.getElementById("root");
  if (!stateNode || !root) {
    return;
  }

  let state = {};
  try {
    state = JSON.parse(stateNode.textContent || "{}");
  } catch (_error) {
    root.innerHTML = "<p>Failed to load page state.</p>";
    return;
  }
  renderCfdApp(root, state);
});
