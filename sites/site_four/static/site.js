"use strict";

(function () {
  document.addEventListener("DOMContentLoaded", () => {
    initAssetsMenu();
    initRegisterHint();
    initDepositPage();
  });

  function initAssetsMenu() {
    const button = document.getElementById("assets-menu-btn");
    const dropdown = document.getElementById("assets-dropdown");
    if (!button || !dropdown) {
      return;
    }

    const close = () => {
      dropdown.classList.remove("open");
    };

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      dropdown.classList.toggle("open");
    });

    document.addEventListener("click", (event) => {
      if (!dropdown.contains(event.target) && !button.contains(event.target)) {
        close();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        close();
      }
    });
  }

  function initRegisterHint() {
    const pass = document.getElementById("password");
    const confirm = document.getElementById("password_confirm");
    const hint = document.getElementById("password-match-message");
    if (!pass || !confirm || !hint) {
      return;
    }

    const updateHint = () => {
      if (!confirm.value) {
        hint.textContent = "";
        hint.classList.remove("hint-ok", "hint-error");
        return;
      }
      if (pass.value === confirm.value) {
        hint.textContent = "Passwords match.";
        hint.classList.add("hint-ok");
        hint.classList.remove("hint-error");
      } else {
        hint.textContent = "Passwords do not match.";
        hint.classList.add("hint-error");
        hint.classList.remove("hint-ok");
      }
    };

    pass.addEventListener("input", updateHint);
    confirm.addEventListener("input", updateHint);
  }

  function initDepositPage() {
    const configScript = document.getElementById("deposit-page-config");
    if (!configScript) {
      return;
    }

    const config = safeParseJSON(configScript.textContent || "{}");
    if (!config || !config.coinsEndpoint) {
      return;
    }

    const refs = {
      assetTrigger: document.getElementById("asset-select-trigger"),
      assetValue: document.getElementById("asset-selected-value"),
      networkBox: document.getElementById("network-box"),
      detailsBox: document.getElementById("deposit-details-box"),
      drawer: document.getElementById("asset-drawer"),
      drawerMask: document.querySelector("#asset-drawer .ant-drawer-mask"),
      searchInput: document.getElementById("asset-search-input"),
      hotList: document.getElementById("hot-coin-list"),
      fullList: document.getElementById("full-coin-list"),
      historyBody: document.getElementById("deposit-history-body"),
      stepTwoCircle: document.getElementById("step-two-circle"),
      stepThreeCircle: document.getElementById("step-three-circle"),
      stepTwoTitle: document.getElementById("step-two-title"),
      stepThreeTitle: document.getElementById("step-three-title"),
    };

    const state = {
      coins: [],
      selectedCoin: null,
      selectedNetwork: null,
    };

    wireDrawerHandlers(refs, () => renderCoinDrawer(refs, state, config));
    wireSearchHandlers(refs, () => renderCoinDrawer(refs, state, config));

    if (refs.assetTrigger) {
      refs.assetTrigger.addEventListener("click", () => openDrawer(refs.drawer));
    }

    primeRequestChain(config);
    loadCoins();
    loadHistory();

    async function loadCoins() {
      try {
        const payload = await fetchJSON(config.coinsEndpoint);
        state.coins = apiData(payload);
        renderCoinDrawer(refs, state, config);
      } catch (_error) {
        renderError(refs.networkBox, "Unable to load assets.");
      }
    }

    async function loadHistory() {
      try {
        const payload = await fetchJSON(`${config.historyEndpoint}?page=1&size=10`);
        renderHistoryRows(refs.historyBody, apiData(payload));
      } catch (_error) {
        renderHistoryError(refs.historyBody);
      }
    }

    async function chooseCoin(coinCode) {
      const coin = state.coins.find((item) => item.coin === coinCode);
      if (!coin || !coin.available) {
        return;
      }

      state.selectedCoin = coin;
      state.selectedNetwork = null;
      if (refs.assetValue) {
        refs.assetValue.textContent = `${coin.coin} ${coin.name}`;
      }
      closeDrawer(refs.drawer);
      setStepDoing(refs.stepTwoCircle, refs.stepTwoTitle);
      resetStep(refs.stepThreeCircle, refs.stepThreeTitle);
      renderLoading(refs.networkBox, "Loading available transfer networks...");
      clearPanel(refs.detailsBox);

      try {
        const payload = await fetchJSON(
          `${config.networksEndpoint}?coin=${encodeURIComponent(coin.coin)}`
        );
        const networks = apiData(payload);
        renderNetworks(networks);
      } catch (_error) {
        renderError(refs.networkBox, "Unable to load transfer networks.");
      }
    }

    function renderNetworks(networks) {
      if (!refs.networkBox) {
        return;
      }
      refs.networkBox.classList.remove("placeholder");
      refs.networkBox.textContent = "";

      if (!networks.length) {
        renderError(
          refs.networkBox,
          "No transfer networks are available for this asset."
        );
        return;
      }

      const list = document.createElement("div");
      list.className = "network-list";
      networks.forEach((networkItem) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "network-pill";
        button.textContent = networkItem.network;
        button.dataset.network = networkItem.network;
        button.addEventListener("click", () => chooseNetwork(networkItem.network, list));
        list.appendChild(button);
      });
      refs.networkBox.appendChild(list);
    }

    async function chooseNetwork(network, networkContainer) {
      if (!state.selectedCoin) {
        return;
      }
      state.selectedNetwork = network;
      markActiveNetwork(networkContainer, network);
      setStepDoing(refs.stepThreeCircle, refs.stepThreeTitle);
      renderLoading(refs.detailsBox, "Loading deposit details...");

      try {
        const payload = await fetchJSON(
          `${config.addressEndpoint}?coin=${encodeURIComponent(
            state.selectedCoin.coin
          )}&network=${encodeURIComponent(network)}`
        );
        renderDetails(apiData(payload));
      } catch (_error) {
        renderError(refs.detailsBox, "Unable to load deposit details.");
      }
    }

    function renderDetails(data) {
      if (!refs.detailsBox) {
        return;
      }
      refs.detailsBox.classList.remove("placeholder");
      refs.detailsBox.textContent = "";

      const card = document.createElement("section");
      card.className = "details-card";

      const heading = document.createElement("h4");
      heading.textContent = `${data.coin} ${data.network} Deposit Details`;
      card.appendChild(heading);

      const networkNote = document.createElement("p");
      networkNote.className = "inline-note";
      networkNote.textContent = `Selected transfer network: ${data.network}`;
      card.appendChild(networkNote);

      const tip = document.createElement("p");
      tip.className = "details-tip";
      tip.textContent =
        data.depositTip ||
        "Please choose the same network as the coin charging platform to avoid loss of funds.";
      card.appendChild(tip);

      const qr = document.createElement("div");
      qr.className = "details-qr";
      const image = document.createElement("img");
      image.alt = "Deposit address QR";
      image.src = data.qrDataUri;
      qr.appendChild(image);
      card.appendChild(qr);

      const addressRow = document.createElement("div");
      addressRow.className = "address-row";

      const input = document.createElement("input");
      input.value = data.address;
      input.readOnly = true;
      input.setAttribute("aria-label", "Deposit address");
      addressRow.appendChild(input);

      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.textContent = "Copy";
      copyButton.addEventListener("click", async () => {
        const ok = await copyText(data.address);
        const original = copyButton.textContent;
        copyButton.textContent = ok ? "Copied" : "Copy failed";
        window.setTimeout(() => {
          copyButton.textContent = original;
        }, 1200);
      });
      addressRow.appendChild(copyButton);

      card.appendChild(addressRow);
      refs.detailsBox.appendChild(card);
    }

    function renderCoinDrawer(localRefs, localState) {
      const search = (localRefs.searchInput?.value || "").trim().toLowerCase();
      const candidates = localState.coins.filter((coin) => {
        if (!search) {
          return true;
        }
        const label = `${coin.coin} ${coin.name}`.toLowerCase();
        return label.includes(search);
      });

      const hotCoins = candidates.filter((coin) => coin.hot);
      renderHotCoins(localRefs.hotList, hotCoins, chooseCoin);
      renderFullCoinList(localRefs.fullList, candidates, chooseCoin);
    }
  }

  function wireDrawerHandlers(refs, redraw) {
    if (!refs.drawer) {
      return;
    }
    if (refs.drawerMask) {
      refs.drawerMask.addEventListener("click", () => closeDrawer(refs.drawer));
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeDrawer(refs.drawer);
      }
    });
    refs.drawer.addEventListener("transitionend", redraw);
  }

  function wireSearchHandlers(refs, redraw) {
    if (!refs.searchInput) {
      return;
    }
    refs.searchInput.addEventListener("input", redraw);
  }

  function openDrawer(drawer) {
    if (!drawer) {
      return;
    }
    drawer.hidden = false;
    document.body.classList.add("drawer-open");
  }

  function closeDrawer(drawer) {
    if (!drawer) {
      return;
    }
    drawer.hidden = true;
    document.body.classList.remove("drawer-open");
  }

  function renderHotCoins(container, list, onSelect) {
    if (!container) {
      return;
    }
    container.textContent = "";
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "inline-note";
      empty.textContent = "No matching assets";
      container.appendChild(empty);
      return;
    }
    container.className = "hot-chip-list";
    list.forEach((coin) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hot-chip";
      button.textContent = coin.coin;
      if (!coin.available) {
        button.disabled = true;
      }
      button.addEventListener("click", () => onSelect(coin.coin));
      container.appendChild(button);
    });
  }

  function renderFullCoinList(container, list, onSelect) {
    if (!container) {
      return;
    }
    container.textContent = "";
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "inline-note";
      empty.textContent = "No matching assets";
      container.appendChild(empty);
      return;
    }
    list.forEach((coin) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "coin-item";
      if (!coin.available) {
        item.classList.add("disabled");
      }
      item.setAttribute("aria-label", `Select ${coin.coin}`);

      const left = document.createElement("span");
      left.className = "coin-item-left";

      const symbol = document.createElement("span");
      symbol.className = "coin-symbol";
      symbol.textContent = coin.coin.slice(0, 1);
      left.appendChild(symbol);

      const labelWrap = document.createElement("span");
      labelWrap.className = "coin-label-wrap";
      const code = document.createElement("span");
      code.className = "coin-code";
      code.textContent = coin.coin;
      const name = document.createElement("span");
      name.className = "coin-name";
      name.textContent = coin.name;
      labelWrap.appendChild(code);
      labelWrap.appendChild(name);
      left.appendChild(labelWrap);
      item.appendChild(left);

      const arrow = document.createElement("span");
      arrow.className = "coin-arrow";
      arrow.textContent = "›";
      item.appendChild(arrow);

      if (coin.available) {
        item.addEventListener("click", () => onSelect(coin.coin));
      } else {
        item.disabled = true;
      }

      container.appendChild(item);
    });
  }

  function renderHistoryRows(tbody, payload) {
    if (!tbody) {
      return;
    }
    tbody.textContent = "";
    const list = (payload && payload.list) || [];
    if (!list.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 8;
      cell.className = "empty-cell";
      cell.innerHTML = "<div class='history-empty-art'>⌁</div><div>No recharge record</div>";
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }

    list.forEach((entry) => {
      const row = document.createElement("tr");
      const values = [
        formatDateTime(entry.time),
        entry.assetName || "",
        entry.amt || "",
        entry.network || "",
        entry.address || "",
        entry.txid || "",
        "--",
        entry.status || "",
      ];
      values.forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
  }

  function renderHistoryError(tbody) {
    if (!tbody) {
      return;
    }
    tbody.textContent = "";
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "empty-cell";
    cell.textContent = "Unable to load deposit history.";
    row.appendChild(cell);
    tbody.appendChild(row);
  }

  function setStepDoing(circle, title) {
    if (circle) {
      circle.classList.remove("step-todo", "step-active");
      circle.classList.add("step-doing");
    }
    if (title) {
      title.classList.remove("left-muted");
    }
  }

  function resetStep(circle, title) {
    if (circle) {
      circle.classList.remove("step-doing", "step-active");
      circle.classList.add("step-todo");
    }
    if (title) {
      title.classList.add("left-muted");
    }
  }

  function clearPanel(panel) {
    if (!panel) {
      return;
    }
    panel.textContent = "";
    panel.classList.add("placeholder");
  }

  function renderLoading(panel, message) {
    if (!panel) {
      return;
    }
    panel.textContent = "";
    panel.classList.remove("placeholder");
    const note = document.createElement("p");
    note.className = "inline-note";
    note.textContent = message;
    panel.appendChild(note);
  }

  function renderError(panel, message) {
    if (!panel) {
      return;
    }
    panel.textContent = "";
    panel.classList.remove("placeholder");
    const error = document.createElement("p");
    error.className = "deposit-error";
    error.textContent = message;
    panel.appendChild(error);
  }

  function markActiveNetwork(container, network) {
    if (!container) {
      return;
    }
    container.querySelectorAll(".network-pill").forEach((button) => {
      const active = button.dataset.network === network;
      button.classList.toggle("active", active);
    });
  }

  async function copyText(value) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch (_error) {
      // fallback below
    }
    try {
      const input = document.createElement("input");
      input.value = value;
      document.body.appendChild(input);
      input.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(input);
      return ok;
    } catch (_error) {
      return false;
    }
  }

  function primeRequestChain(config) {
    const warmup = [
      "/v1/app/public/app/country",
      "/v1/future-u/user/user/collection/list",
      "/v1/spot/balance/public/currencies",
      "/v1/spot/balance/public/currencies?version=2a64aad4d12d1ac0277870a6be5f85d1",
      "/v1/spot/balance/public/price/currency/country-currency",
      config.userInfoEndpoint,
      config.coinsEndpoint,
      `${config.historyEndpoint}?page=1&size=10`,
      "/v1/spot/market/public/ticker/24h",
      "/v1/future-u/market/public/q/tickers",
      "/v1/user/kyc/getRealAuthInfo",
      "/v1/message/private/user-letter/list",
      "/v1/spot/balance/public/price/currency/convert?converts=usd,btc",
      "/v1/spot/account/symbol-star/list?noHandle401=true",
    ];
    warmup.forEach((path) => {
      fetch(path, { credentials: "same-origin" }).catch(() => {});
    });
  }

  async function fetchJSON(path) {
    const response = await fetch(path, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  function apiData(payload) {
    if (!payload || payload.code !== 0) {
      throw new Error(payload?.message || "Request failed");
    }
    return payload.data;
  }

  function safeParseJSON(raw) {
    try {
      return JSON.parse(raw);
    } catch (_error) {
      return null;
    }
  }

  function formatDateTime(raw) {
    if (!raw) {
      return "";
    }
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) {
      return raw;
    }
    return date.toLocaleString("en-GB", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }
})();
