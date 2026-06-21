# Windows (WSL) — detailed guide

On Windows, odpm runs via **WSL2** and **Docker Desktop**. Run your project and `odpm --init` on the Linux filesystem (`/home/...`), not on `C:\` via `/mnt/c` — otherwise bind mounts in Docker will be slow.

## Why use WSL instead of “plain Windows”

When working with directories on the Windows drive (`/mnt/c/...`), files look like network shares to WSL, and mounting them into a container is **very slow**. Keep the odpm working directory **inside WSL** (`/home/<user>/projects/...`).

**Limitations:** copying between Windows and WSL is slow; the WSL disk grows dynamically. For small and learning projects this is fine; for heavy industrial development, **native Linux** is more reliable. Or you know exactly what you are doing.

## Prerequisites

- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- [Visual Studio Code](https://code.visualstudio.com/)

Installing Docker Desktop usually pulls in **WSL2** and the `docker-desktop` / `docker-desktop-data` utility distros.

Next, install a **separate** Linux distro for day-to-day work — the original article uses **Debian** (steps below). Ubuntu works too; `apt` commands are the same.

---

## 1. Enable WSL (PowerShell as administrator)

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
```

Check the WSL version and switch to WSL2 — see [Microsoft documentation](https://learn.microsoft.com/en-us/windows/wsl/install).  
To remove an extra distro if needed — `wsl --unregister`.

---

## 2. Install Debian in WSL

```powershell
wsl --install -d Debian
```

Debian is not essential; you can use Ubuntu or another distro, but all steps below were tested on Debian and may differ, so keep that in mind.
On first launch, set a username and password. The example below uses user `odoo` (you can pick your own name):

```
odoo@DESKTOP-XXXXXX:~$
```

To log in again:

```powershell
wsl --distribution Debian --user odoo
```

---

## 3. Configure Docker Desktop

Start Docker Desktop.

![WSL Integration settings in Docker Desktop](../../install/assets/windows-wsl/configure_docker_desktop.png)

1. Open **Settings** (gear icon).
2. Go to **Resources → WSL integration** (older versions: **WSL Integration**).
3. **Disable** the built-in `docker-desktop` distro if it gets in the way (as in the original article).
4. **Enable** integration for **Debian**.
5. **Apply & restart**.


---

## 4. VS Code: Remote Development extension

![Installing the Remote Development extension](../../install/assets/windows-wsl/install_extension.png)

1. Open the Extensions panel.
2. Search for **Remote Development** (or **WSL**).
3. Install it.

---

## 5. Connect to Debian (WSL)

![Connecting to WSL](../../install/assets/windows-wsl/connect_to_wsl.png)

1. Click **Remote** in the bottom-left corner (or use the Command Palette).
2. **WSL: Connect to WSL** → choose **Debian**.

The first connection may take several minutes (installing the server component in WSL).

---

## 6. Working directory in WSL

![Opening the working folder](../../install/assets/windows-wsl/open_working_folder.png)

1. **File → Open Folder**.
2. Pick your home directory, for example `/home/odoo`.

![Trust workspace authors](../../install/assets/windows-wsl/trust_the_author.png)

3. When asked about trusting authors — check “trust” and confirm.

Open the integrated terminal: **Terminal → New Terminal**.

![Opening the terminal](../../install/assets/windows-wsl/open_terminal.png)

The terminal should be **inside Debian** (status bar: `WSL: Debian`).

---

## 7. Packages in Debian and installing odpm

Minimal set:

```bash
sudo apt update
sudo apt install -y git
```

Install odpm using one of these methods:

**Option A — .deb (recommended):** see [Debian / Ubuntu install](linux-deb.md) — download a `.deb` from [GitHub Releases](https://github.com/aayartsev/odpm/releases) or add the APT repository.

```bash
sudo apt install ./odpm_*.deb
odpm --version
```

**Option B — pip / pipx:** see [pip and source install](pip-legacy.md).

Optional for file navigation:

```bash
sudo apt install -y mc
```

User home directory: `/home/odoo` (or your username). Linux filesystem root is `/`.

---

## 8. Project directory and first `odpm --init`

```bash
mkdir -p ~/projects
cd ~/projects
mkdir my-odoo-project-17
cd my-odoo-project-17
```

Initialize (substitute **your** git repository):

```bash
odpm --init https://github.com/your-org/your-odoo-project.git --branch 17.0
```

> Full walkthrough without a demo repo — [Local development from scratch](../getting-started/local-dev-from-scratch.md).

The wizard will ask about directories and scenario; for unfamiliar items you can press **Enter** (defaults).

After preparation:

```bash
odpm -d test_db -i -u
```

Browser: `http://127.0.0.1:8069`.

Open the project folder in VS Code via **Open Folder** → `/home/odoo/projects/my-odoo-project-17` (already in a WSL session).

---

## 9. Git and SSH

For private repositories, set up an SSH key **inside WSL** (Linux instructions, not Windows). See also [Repository links](../reference/git-links.md).

---

## 10. Restarting odpm

Stop: `Ctrl+C` in the terminal where odpm / compose is running. To start again — run `odpm` or commands from the [CLI reference](../reference/cli.md).

---

## `file://` links in WSL

```text
file:///home/odoo/my_addons
```

Three slashes after `file:` — see [git-links](../reference/git-links.md).

---

## Full install table

[Installing odpm (all platforms)](README.md).
