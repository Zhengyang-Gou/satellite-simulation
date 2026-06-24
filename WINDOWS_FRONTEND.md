# Windows Frontend + Linux Backend

This project can run the PySide6/PyVista GUI on Windows while keeping deployment,
measurement scripts, Redis, containers, and OVS on the Linux backend host.

The default backend is bundled in the app configuration:

```text
SSH:   s223@121.48.163.223:22
Deploy script:  /home/s223/yzy/scripts/deploy.sh
Measure script: /home/s223/yzy/scripts/measure_slice.sh
Redis: Linux backend 127.0.0.1:6379 through an SSH tunnel
Key:   ~/.ssh/id_ed25519_satellite_simulation, when that file exists
```

So the normal Windows launch path is simply:

```powershell
conda env create -f environment.yml
conda activate satsim
python main.py
```

Windows needs a local OpenSSH client. Check it with:

```powershell
ssh -V
```

## SSH Requirements

The GUI no longer requires a `%USERPROFILE%\.ssh\config` alias. It builds direct
SSH commands using the bundled host, user, port, and key path.

Verify the same connection from PowerShell:

```powershell
ssh -p 22 -i "$env:USERPROFILE\.ssh\id_ed25519_satellite_simulation" s223@121.48.163.223 "echo ok"
```

If the key is managed by `ssh-agent` or another default OpenSSH identity, the
explicit `-i` file is not required.

## Optional Overrides

Use these only when the backend changes:

```powershell
$env:SATNET_SSH_HOST = "121.48.163.223"
$env:SATNET_SSH_PORT = "22"
$env:SATNET_SSH_USERNAME = "s223"
$env:SATNET_SSH_PRIVATE_KEY = "$env:USERPROFILE\.ssh\id_ed25519_satellite_simulation"
$env:SATNET_REMOTE_DEPLOY_SCRIPT = "/home/s223/yzy/scripts/deploy.sh"
$env:SATNET_REMOTE_MEASURE_SCRIPT = "/home/s223/yzy/scripts/measure_slice.sh"
python main.py
```

If you prefer using an OpenSSH alias, set it explicitly:

```powershell
$env:SATNET_SSH_HOST_ALIAS = "satellite-simulation"
python main.py
```

Redis is accessed through an SSH tunnel by default. To enable Redis query on launch:

```powershell
$env:SATNET_REDIS_ENABLED = "1"
```

If sudo/Redis needs a password, put it in the default file below or override the
path with `SATNET_REDIS_PASSWORD_FILE`:

```text
%USERPROFILE%\.config\satellite-simulation\redis_password
```

You can also set `SATNET_REDIS_PASSWORD` directly for the current shell.