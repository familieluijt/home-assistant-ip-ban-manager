# Home Assistant IP Ban Manager

Adds a management panel for viewing and managing IP addresses in Home Assistant's `ip_bans.yaml` file.

## Installation

1. Open HACS in Home Assistant.
2. Open **Integrations**, then **Custom repositories**.
3. Add this repository with category **Integration**.
4. Download **IP Ban Manager**.
5. Restart Home Assistant.
6. Open **Settings > Devices & services**, add **IP Ban Manager**, and enable the panel.

## Services

- `ip_ban_manager.add_ban`
- `ip_ban_manager.remove_ban`
- `ip_ban_manager.refresh`
