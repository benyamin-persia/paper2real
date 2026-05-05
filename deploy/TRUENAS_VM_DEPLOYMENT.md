# TrueNAS Deployment For Paper2Real

Do not run Paper2Real directly on the TrueNAS host shell. TrueNAS warns against
manual OS changes because they can break upgrades and system management.

Use this architecture:

```text
TrueNAS host
  -> Ubuntu 24.04 VM
      -> Paper2Real FastAPI trader
      -> systemd service/timers
      -> SQLite paper_trader.db
```

## Is TrueNAS Enough Instead Of A VPS?

Yes, if the Ubuntu VM gets at least:

```text
2 vCPU
4 GB RAM
80 GB disk
Ubuntu 24.04
```

That is enough for:

- 24/7 FastAPI paper trader
- Claude API calls
- SQLite
- risk engine
- live BTC scans
- critical events refresh
- Tier 1 X/Twitter scraping at light settings
- decision_evaluator.py every 4 hours

For heavier Playwright scraping, use:

```text
4 vCPU
8 GB RAM
80+ GB disk
```

Do not run full 84-account X/Twitter scraping before every trade. Run it as a
daily/off-hours job only if needed.

## Detected Local TrueNAS Hardware

Checked read-only on 2026-05-04:

```text
Host: truenas
CPU: Intel Core i7 950 @ 3.07 GHz
CPU threads: 8
RAM: about 24 GB total, about 19 GB available at check time
Virtualization: VT-x available
KVM device: /dev/kvm exists
Disks visible: 238 GB boot disk plus four 4.5 TB disks
```

Conclusion: this machine is enough to replace a small VPS for Paper2Real if the
bot runs inside an Ubuntu VM. Recommended VM allocation on this hardware:

```text
Live trader: 2 vCPU, 4 GB RAM, 80 GB disk
Comfortable full setup: 4 vCPU, 8 GB RAM, 80+ GB disk
```

## VM Setup

1. In TrueNAS WebUI, create an Ubuntu 24.04 VM.
2. Assign CPU/RAM/disk:
   - Minimum: 2 vCPU, 4 GB RAM, 80 GB disk.
   - Better: 4 vCPU, 8 GB RAM, 80+ GB disk.
3. Enable SSH inside Ubuntu.
4. Copy this repo to `/opt/paper2real`.
5. Create `/opt/paper2real/.env` from `.env.example` and set `ANTHROPIC_API_KEY`.

## Install On Ubuntu VM

From inside the Ubuntu VM:

```bash
sudo bash /opt/paper2real/deploy/install_ubuntu.sh
```

Then run the commands printed by that script after the project files are in
`/opt/paper2real`.

## Services

Installed systemd units:

- `paper2real.service` - runs `uvicorn main:app --host 0.0.0.0 --port 8000`.
- `paper2real-evaluator.timer` - runs `decision_evaluator.py` every 4 hours.
- `paper2real-collect.timer` - optional weekly `collect.py` refresh.
- `paper2real-backup.timer` - local daily backup.

Useful commands:

```bash
sudo systemctl status paper2real.service
sudo journalctl -u paper2real.service -f
sudo systemctl list-timers 'paper2real*'
sudo systemctl restart paper2real.service
```

Dashboard:

```text
http://<ubuntu-vm-ip>:8000
```

## Backup

Backups are written to:

```text
/opt/paper2real/backups/
```

The backup keeps:

- `paper_trader.db`
- `data/reports`
- `data/raw`
- `data/processed`
- `.env`

Old backups older than 14 days are deleted.
