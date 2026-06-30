# Production hardening checklist for волгу-наука.рф

This runbook is intended for the VPS host. Run commands through SSH as a sudo-capable user.
Do not close the current SSH session while changing firewall or sshd settings.

## Target architecture

Public internet:

- `80/tcp` nginx HTTP redirect and ACME challenge only
- `443/tcp` nginx HTTPS reverse proxy
- `22/tcp` OpenSSH for administration

Private/local only:

- Django/Gunicorn: `127.0.0.1:8000`
- PostgreSQL container: Docker network only, no host port
- dnsmasq: disabled, or bound to `127.0.0.1` only if really needed

## Main risks found

Critical:

- PostgreSQL is exposed to the internet on `5432/tcp`. This is directly exploitable by password brute force, credential reuse, version probing, and database-level vulnerabilities.
- Django dev server is exposed to the internet on `8000/tcp`. `runserver` is not a production WSGI server and bypasses nginx controls, TLS, rate limits, and security headers.

High:

- `dnsmasq` is exposed on `53/tcp/udp`. If it is an open resolver or old/misconfigured DNS forwarder, it can be abused for DNS amplification, cache poisoning scenarios, and service fingerprinting.
- nginx `1.14.1` is very old for a public edge service. Even when distro-patched, it should be reviewed and upgraded if the OS is EOL.
- SSH password login/root login may allow brute force if enabled.

Medium:

- Production safety depends on `.env`: `DEBUG=0`, strong `SECRET_KEY`, strict `DJANGO_ALLOWED_HOSTS`, HTTPS CSRF origins.
- Rate limiting was absent at the reverse proxy layer.

## Pre-change audit

```bash
hostnamectl
date -Is
whoami
pwd

sudo ss -tulpen
sudo systemctl status nginx --no-pager
sudo systemctl status sshd --no-pager || sudo systemctl status ssh --no-pager
sudo systemctl status dnsmasq --no-pager || true

cd /home/axawys/volsu-science-system
git rev-parse --short HEAD
docker compose ps
docker compose logs --tail=100 web
docker compose logs --tail=100 db
```

Back up host configs before edits:

```bash
sudo mkdir -p /root/sciencehub-hardening-backup
sudo cp -a /etc/nginx /root/sciencehub-hardening-backup/nginx.$(date +%Y%m%d-%H%M%S)
sudo cp -a /etc/ssh/sshd_config /root/sciencehub-hardening-backup/sshd_config.$(date +%Y%m%d-%H%M%S)
sudo cp -a /etc/dnsmasq.conf /root/sciencehub-hardening-backup/dnsmasq.conf.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
```

## Deploy Docker architecture fix

The repository `compose.yaml` must not publish PostgreSQL to the host and must bind the web container to localhost only.

```bash
cd /home/axawys/volsu-science-system
git pull --ff-only
docker compose up -d --build --force-recreate
docker compose ps
```

Expected host sockets after this step:

- `127.0.0.1:8000` may be listening
- no public `0.0.0.0:8000`
- no host `5432`

Verify:

```bash
sudo ss -tulpen | grep -E '(:8000|:5432)' || true
curl -I http://127.0.0.1:8000/
```

Rollback:

```bash
cd /home/axawys/volsu-science-system
git log --oneline -5
git checkout <previous-good-commit>
docker compose up -d --build --force-recreate
```

## nginx reverse proxy

Install the prepared config:

```bash
sudo cp /home/axawys/volsu-science-system/deploy/nginx/sciencehub.conf /etc/nginx/conf.d/sciencehub.conf
sudo nginx -t
sudo systemctl reload nginx
```

If your nginx uses `sites-available/sites-enabled`, use:

```bash
sudo cp /home/axawys/volsu-science-system/deploy/nginx/sciencehub.conf /etc/nginx/sites-available/sciencehub.conf
sudo ln -sf /etc/nginx/sites-available/sciencehub.conf /etc/nginx/sites-enabled/sciencehub.conf
sudo nginx -t
sudo systemctl reload nginx
```

Verify:

```bash
curl -I http://волгу-наука.рф/
curl -I https://волгу-наука.рф/
curl -I http://127.0.0.1:8000/
```

Rollback:

```bash
sudo rm -f /etc/nginx/conf.d/sciencehub.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Firewall

Use only one firewall stack. If the server already uses `firewalld`, prefer it. If it uses `ufw`, use `ufw`.

### Option A: firewalld

```bash
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --set-default-zone=public
sudo firewall-cmd --permanent --remove-service=postgresql 2>/dev/null || true
sudo firewall-cmd --permanent --remove-service=dns 2>/dev/null || true
sudo firewall-cmd --permanent --remove-port=8000/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --remove-port=5432/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --remove-port=53/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --remove-port=53/udp 2>/dev/null || true
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

### Option B: ufw

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

Verify externally with nmap from another machine:

```bash
nmap -Pn -p 21,22,53,80,443,5432,8000 волгу-наука.рф
```

Expected:

- `22/open`
- `80/open`
- `443/open`
- `53/closed|filtered`
- `5432/closed|filtered`
- `8000/closed|filtered`

## dnsmasq

If dnsmasq is not needed on a public VPS, disable it:

```bash
sudo systemctl disable --now dnsmasq
sudo ss -tulpen | grep ':53' || true
```

If dnsmasq is needed locally, restrict it:

```bash
sudo cp -a /etc/dnsmasq.conf /etc/dnsmasq.conf.before-hardening
printf '%s\n' 'interface=lo' 'listen-address=127.0.0.1' 'bind-interfaces' | sudo tee /etc/dnsmasq.d/local-only.conf
sudo systemctl restart dnsmasq
sudo ss -tulpen | grep ':53' || true
```

## SSH hardening

Before disabling password auth, confirm that key auth works in a second terminal:

```bash
ssh -o PreferredAuthentications=publickey <user>@волгу-наука.рф
```

Then edit `/etc/ssh/sshd_config`:

```sshconfig
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
MaxAuthTries 3
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
```

Optionally restrict users:

```sshconfig
AllowUsers axawys
```

Validate and reload:

```bash
sudo sshd -t
sudo systemctl reload sshd || sudo systemctl reload ssh
```

Rollback from the still-open SSH session:

```bash
sudo cp /root/sciencehub-hardening-backup/sshd_config.* /etc/ssh/sshd_config
sudo sshd -t
sudo systemctl reload sshd || sudo systemctl reload ssh
```

## fail2ban

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y fail2ban
```

RHEL/CentOS/Alma/Rocky:

```bash
sudo dnf install -y epel-release
sudo dnf install -y fail2ban
```

Create `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port = ssh
maxretry = 5
findtime = 10m
bantime = 1h
```

Enable:

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

## System updates and version risks

Check package ownership and patch level:

```bash
nginx -v
python3 --version || true
psql --version || true
docker compose exec -T db psql --version
cat /etc/os-release
sudo dnf check-update || true
sudo apt list --upgradable 2>/dev/null || true
```

Recommendations:

- If host PostgreSQL 9.6 is installed and exposed, stop/disable it after confirming the app uses Docker PostgreSQL 17.
- PostgreSQL 9.6 is end-of-life. Migrate any host database to PostgreSQL 17 or remove the host service entirely.
- nginx 1.14.1 is old. If the OS is EOL, migrate to a supported distribution or official nginx stable packages.
- Keep Docker base images rebuilt regularly.

## Django production checks

On the server:

```bash
cd /home/axawys/volsu-science-system
grep -E '^(DEBUG|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|SECURE_|SESSION_COOKIE_SECURE|CSRF_COOKIE_SECURE)=' .env
docker compose exec -T web sh -c 'cd /app/src && python manage.py check --deploy'
```

Expected `.env` essentials:

```env
DEBUG=0
DJANGO_ALLOWED_HOSTS=волгу-наука.рф,xn----8sbaff8bdsf6cd.xn--p1ai
DJANGO_CSRF_TRUSTED_ORIGINS=https://волгу-наука.рф,https://xn----8sbaff8bdsf6cd.xn--p1ai
SECURE_SSL_REDIRECT=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
SECURE_HSTS_SECONDS=31536000
```

## Secret hygiene

Check that real secrets are not committed:

```bash
git status --short
git ls-files .env
git log --all -- .env
```

Rotate if exposed:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DJANGO_SUPERUSER_PASSWORD`
- SMTP credentials
- GitHub deploy SSH key if it was ever pasted into repo/logs

