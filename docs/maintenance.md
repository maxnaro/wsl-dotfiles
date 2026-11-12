# Maintaining this setup

Run `./setup.sh` for the complete installation on Linux or WSL, on x86_64 or ARM64.
Git, curl, Python 3.11+, tar with gzip/xz support, sha256sum, tmux, and a C linker
must already be available. Submodules use SSH URLs and require GitHub SSH access.
Rust follows the existing stable-toolchain policy. No sudo is used.

## Downloads and reruns

`setup/tools.json` records release versions, official download URLs, and SHA-256
hashes for both architectures. Installed tools are retained and their versions
are displayed beside the pins. To update a pin, review the upstream release,
replace both architecture URLs and hashes using official release metadata,
and validate on the target architectures. FZF shell scripts use the pinned FZF
release and their own hashes; update these together.

Missing tools are downloaded and checked in temporary staging directories before
installation. Neovim keeps its runtime under `~/.local/share/dotfiles/`. Interrupted
setup can be rerun; completed components remain installed. This is not a global
transaction. Configuration links are created only after builds and font setup
succeed. Existing destinations move to unique adjacent `.bak.*` directories,
with the original stored as `original`. Keep these until satisfied with setup.
Correct symlinks are retained. A failed replacement link restores its backup.

Pokémon greeting source is pinned to the manifest commit. Its upstream installer
still downloads sprites from the moving pokemon-colorscripts main branch.
Rustup bootstrap and stable Rust also remain network-dependent moving inputs.

## Explicit upgrades and rollback

Use `./setup.sh --upgrade TOOL... --dry-run` to inspect the selected changes and
prerequisites, then omit `--dry-run` to install. Supported names are manifest
binary packages and `tmux`; fzf automatically includes both Bash integration
files. Matching pins and newer installed versions are retained. No arguments
still run ordinary setup, which retains existing executables.

On Ubuntu, prepare the tmux build dependencies once:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends build-essential libevent-dev libncurses-dev pkg-config
```

Downloads, checksum checks, source builds, executable version checks, completions,
and Atuin data compatibility checks finish before activation. Packages install
under `~/.local`, shadowing system executables without changing `/usr/bin`.
Neovim and tmux retain versioned runtime directories. Source-build dependencies
remain system-managed; the installer never invokes sudo.

Each upgrade prints a transaction ID and a rollback command:

```bash
./setup.sh --rollback TRANSACTION_ID
```

Journals and backups live in `~/.local/state/dotfiles/upgrades/`. Transactions are
serialized; interrupted activation is recovered before the next upgrade. Failed
activation restores prior destinations. Rollback refuses to overwrite files
changed since the transaction. Previously absent local executables are removed
on rollback so their system versions become visible again. Backups and runtime
directories are retained for inspection and already-running processes.

Atuin discovers actual database locations and backs up SQLite consistently,
including committed WAL data. Forward and backward readers are checked against
copies. Rollback checks a copy of current history and never restores an old
database over newly recorded commands. An incompatible old reader blocks the
rollback. History imports, sync, and shell/editor restarts are not part of an
upgrade. Neovim's configuration and plugin lock remain unchanged.

## Automated tool updates

CI runs on PRs and pushes to `main`. It installs the exact manifest versions in
an isolated home on native Ubuntu x86_64 and ARM64 runners, then runs installer,
shell, tmux, Neovim theme, and notebook checks. The aggregate required check is
named `ci`. Performance output is uploaded as evidence, without wall-clock
latency thresholds on shared runners. Local WSL rendering and overnight behavior
still need local observation.

The `Update tools` workflow checks every Monday at 03:17 UTC. Manual dispatch
supports an optional package name and defaults to discovery only. The updater
excludes prereleases, submodules, and the Pokémon source commit. It verifies both
architecture archives, groups fzf scripts with its binary, and maintains one
`deps/TOOL` PR per package. Human-edited branches are left alone. The updater
does not install anything on your laptop.

Automatic merging is restricted to three-component numeric versions whose major
and minor components stay the same, including `0.x` versions. Other updates,
including tmux letter-suffix releases, require manual merging. Before merging,
trusted default-branch code verifies the bot identity, commit ownership, exact
tested head, manifest-only package diff, official release hashes, and successful
aggregate CI. Stale branches are refreshed for another CI run. PR code and test
artifacts are never executed in a job holding the updater App's credentials.

One-time repository setup:

1. Publish referenced submodule commits before the parent repository. CI checks
   out public submodules over HTTPS; developer SSH URLs remain unchanged.
2. Establish a successful candidate CI run before enabling automation.
3. Create a dedicated GitHub App in your account's Developer settings. Use this
   repository's URL as its homepage, disable webhooks, and install it only on
   `maxnaro/wsl-dotfiles`. Repository permissions: **Contents: read/write**,
   **Pull requests: read/write**, **Actions: read**, and **Checks: read**.
4. Generate a private key. Configure repository variable `UPDATER_APP_ID` and
   secret `UPDATER_APP_PRIVATE_KEY`. Never commit the key. For example:

   ```bash
   gh variable set UPDATER_APP_ID --repo maxnaro/wsl-dotfiles --body APP_ID
   gh secret set UPDATER_APP_PRIVATE_KEY --repo maxnaro/wsl-dotfiles < /path/to/private-key.pem
   ```

5. Enable squash merging and repository auto-merge. Protect `main`: require `ci`,
   require branches to be up to date, prevent force pushes/deletion, and give the
   bot no bypass. Do not require human approval on every PR if patch updates
   should merge unattended.
6. Set repository variable `UPDATER_ENABLED=true`, dispatch discovery only, then
   publish a candidate PR. Confirm both architectures pass and patch eligibility
   is enforced. Without this variable, discovery works but publishing and merging
   remain disabled.

To pause publishing and merging, set `UPDATER_ENABLED=false`; existing branches,
PRs, and installed packages remain available. App tokens are short-lived and
restricted to this repository. Workflow actions are pinned to full commits.

## Shells and machine settings

Interactive Bash starts Fish when available. Use `DOTFILES_NO_FISH=1 bash` for
Bash fallback. Missing optional Rust/NVM/Pyenv files do not prevent startup.

Use `~/.bashrc.local` and `~/.config/fish/local.fish` for machine settings. They are
optional. The Fish override and generated `fish_variables` file are ignored by
Git. Existing universal variables remain on disk when tracking is removed.
Fish uses session PATH modifications rather than persisting new universal paths.

Only WSL sessions filter mounted Windows paths. A VS Code directory already on
PATH is retained; if it is absent, add the appropriate directory in the local
override file. No Windows username is assumed.

## Validation

Run `python3 -m unittest discover -s tests`, `bash -n setup.sh bash/.bashrc
bash/.bash_aliases scripts/.scripts/auto_venv.sh`, and `fish -n` on the tracked
Fish scripts. Tests use temporary homes and mocked downloads and do not execute
the real full setup. Release metadata has been verified for both architectures;
ARM64 binaries still require a real ARM64 machine for execution validation.

For typing latency, run `python3 tests/live_terminal_latency.py`. It compares
direct PTY echo, a private tmux server without configuration, and a private
server with these dotfiles. It reports median, p95, maximum, 500-character burst
latency, and output bytes per key on a filled screen. These measurements cover
the Linux PTY path; they exclude physical keyboard input, the WSL/ConPTY bridge,
and Windows Terminal's rendering. To include a running server, pass
`--socket /path/to/tmux/socket`; the probe creates and removes its own session
and client without sending input to existing panes.

The running-cat plugin stores activity and animation state in hidden tmux
environment entries and refreshes only affected status lines. Updating tmux
options for every key or animation frame causes full pane redraws, which can
flood the terminal connection. The plugin also queries clients directly to
avoid the command-string reference leak in older tmux `if-shell -F` versions.
Run `python3 tmux/.config/tmux/plugins/tmux-runcat/tests/idle_memory.py` on Linux
for a private-server idle memory check. Reload the rebuilt plugin to apply these
fixes; existing sessions remain open. Previously leaked server memory stays
allocated until the server exits, so stable RSS after reloading is the useful
check. Do not restart the server while it holds unsaved running programs.

## Workspaces, recovery, and history

Setup installs pinned Sesh and Atuin binaries and generates their Bash/Fish
completions. Resurrect and Continuum are pinned submodules; update their pointers
explicitly rather than running a plugin-manager update.

In tmux, press your prefix (`Ctrl-b` or `Ctrl-a`) followed by:

| Key | Action |
| --- | --- |
| `g` | Pick an existing session or Zoxide directory |
| `Ctrl-s` | Save the workspace now |
| `Ctrl-r` | Restore the saved workspace |
| `r` | Reload configuration |

New workspaces start with one shell. Use `sesh connect /path/to/project` to start
a first project; visiting directories builds Zoxide's project list. Escape or
Ctrl-c cancels the picker without creating a session. The delayed help popup
includes workspace and recovery shortcuts when enabled.

Continuum saves every 15 minutes while tmux's status line is active. Recovery is
manual and restores layouts and working directories, with process restoration
disabled. Snapshots live in `~/.local/state/tmux/resurrect`. Running process memory
and unsaved editor buffers are not recovered. Continuum can suspend automatic
saving when another tmux server is running; manual save remains available.

Atuin uses `Ctrl-r` in interactive Fish and Bash fallback sessions; Up-arrow keeps
its native behavior. Selecting a command returns it for editing. Sync and update
checks are disabled, with no account creation or automatic history import. The
tracked configuration is linked at `~/.config/atuin/config.toml`; history remains
in Atuin's local data directory outside the repository. To import existing
history deliberately, run `atuin import fish` or `atuin import bash` once.

Run `python3 tests/live_recovery.py` for an isolated real-tmux check, in addition
to the unit suite. It creates and cleans up its own socket and temporary home.
Changes to prefix-help must be committed in its repository before updating the
parent pointer. Publish that plugin commit before sharing the parent commit.
