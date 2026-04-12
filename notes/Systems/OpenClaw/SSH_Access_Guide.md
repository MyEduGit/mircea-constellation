# OpenClaw SSH & Termius Setup (Fixed)

**Server IP:** 46.225.51.30  
**Username:** root  

## Working method (April 2026)
1. Open Mac terminal
2. Run: `ssh -L 5678:localhost:5678 root@46.225.51.30`
3. Keep terminal open (closing it breaks the tunnel)
4. Access n8n at: http://localhost:5678

## Common problems we fixed
- Wrong username
- Password not updated after Hetzner reset
- Safari cookie error → use Chrome or Firefox
- SSH timeout → reconnect and run commands immediately

**Pro tip:** Once SSH key is attached you never type password again.
