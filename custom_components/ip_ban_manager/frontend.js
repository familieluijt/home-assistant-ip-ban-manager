class IPBanManagerPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
  }

  set narrow(narrow) {}
  set route(route) {}

  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.render();
  }

  async refresh() {
    const result = await this._hass.callWS({ type: "ip_ban_manager/list" });
    this._bans = result.bans;
    this.render();
  }

  render() {
    if (!this._hass) return;
    if (!this._bans) {
      this.refresh();
      return;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; min-height:100vh; background:var(--primary-background-color); color:var(--primary-text-color); }
        .page { max-width:900px; margin:auto; padding:24px; }
        h1 { margin:0 0 16px; }
        .card { background:var(--card-background-color); border-radius:var(--ha-card-border-radius,12px); padding:16px; margin-bottom:16px; box-shadow:var(--ha-card-box-shadow); }
        form { display:flex; gap:8px; }
        input { flex:1; min-width:120px; border:1px solid var(--divider-color); border-radius:4px; background:var(--card-background-color); color:var(--primary-text-color); padding:10px; }
        button { border:0; border-radius:4px; background:var(--primary-color); color:var(--text-primary-color); padding:10px 14px; cursor:pointer; }
        table { width:100%; border-collapse:collapse; }
        th,td { text-align:left; padding:12px 8px; border-bottom:1px solid var(--divider-color); }
        .remove { background:var(--error-color); }
        .empty { color:var(--secondary-text-color); padding:24px 8px; }
      </style>
      <div class="page">
        <h1>IP Ban Manager</h1>
        <div class="card">
          <form id="ban-form">
            <input id="ip" name="ip" placeholder="IP address" required>
            <button type="submit">Ban IP</button>
          </form>
        </div>
        <div class="card">
          ${this._bans.length ? `
            <table>
              <thead><tr><th>IP address</th><th>Banned at</th><th></th></tr></thead>
              <tbody>${this._bans.map(ban => `
                <tr><td>${this.escape(ban.ip)}</td><td>${this.escape(ban.banned_at || "")}</td>
                <td><button class="remove" data-ip="${this.escape(ban.ip)}">Remove</button></td></tr>`).join("")}</tbody>
            </table>` : `<div class="empty">No IP addresses are currently banned.</div>`}
        </div>
      </div>
    `;

    this.shadowRoot.querySelector("#ban-form").addEventListener("submit", async event => {
      event.preventDefault();
      const ip = this.shadowRoot.querySelector("#ip").value.trim();
      await this._hass.callWS({ type: "ip_ban_manager/add", ip });
      await this.refresh();
    });
    this.shadowRoot.querySelectorAll(".remove").forEach(button => {
      button.addEventListener("click", async () => {
        await this._hass.callWS({ type: "ip_ban_manager/remove", ip: button.dataset.ip });
        await this.refresh();
      });
    });
  }

  escape(value) {
    const node = document.createElement("span");
    node.textContent = value;
    return node.innerHTML;
  }
}

customElements.define("ip-ban-manager-panel", IPBanManagerPanel);
