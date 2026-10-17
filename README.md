# 🔑 keyaudit

**Find the API keys your AI tools left in plain text on your Mac. In ~8 seconds. Without ever printing a key.**

![demo](demo.gif)

Every AI tool wants your keys: Claude Code, Codex, Cursor, OpenCode, MCP servers. Every one of them stores them differently, and some quietly copy them into backups.

I ran this on my own machine and found **1 token in 7 copies**: Claude Code's auto-backups had cloned an MCP token from `~/.claude.json` into six more files.

## Quick start

```bash
git clone https://github.com/HeyAIpenguin/keyaudit && cd keyaudit
python3 keyaudit.py
```

No dependencies. Python 3 only.

## What it checks

| Where | Examples |
|---|---|
| Shell files | `.zshrc`, `.bashrc`, `.zprofile`, `.zsh_history` |
| AI tools | `~/.claude.json` **+ its backups**, `~/.codex`, `~/.config/opencode`, `~/.gemini`, `~/.continue` |
| Editors & MCP | Cursor / VS Code / Windsurf / Zed settings, `mcp.json`, Claude Desktop config |
| Your projects | every `.env*`, `mcp.json`, `settings.json`, `config.*` under `~/Projects`, `~/code`, `~/dev`, `~/Desktop`, `~/Documents`, … |
| Classics | `~/.aws`, `.npmrc`, `.netrc`, Docker config |

**Detects:** Anthropic, OpenAI, OpenRouter, Google AI, Groq, Hugging Face, DeepSeek-style `sk-`, GitHub, GitLab, Slack, AWS, Stripe live, npm, plus any `*_TOKEN` / `*_API_KEY` / `secret` field with a random-looking value.

**Flags:** `.env` files tracked by git, and files any user on the machine can read.

Scan extra folders:

```bash
python3 keyaudit.py ~/some/other/dir
```

Save a JSON report (masked values only):

```bash
python3 keyaudit.py --json report.json
```

## Safety

- **Never prints or stores a secret.** Output is the key type, file, line and a mask like `sk-ant-api03-…a4f2`. The JSON stores a short SHA-256 fingerprint so the same key can be matched across files.
- **Read-only.** It doesn't change, move or delete anything.
- **Offline.** No network calls. ~200 lines, read it before you run it.

## Run it every day (macOS)

```bash
./install-keyaudit.sh
```

Installs a `launchd` job that runs daily at 10:00 and shows a macOS notification **only when a new plaintext key appears**. Keys it has already seen don't trigger it again.

Remove it:

```bash
./uninstall-keyaudit.sh
```

## Found something? 10-minute lockdown

1. **Move it to Keychain**
   ```bash
   security add-generic-password -a "$USER" -s MY_API_KEY -w
   export MY_API_KEY="$(security find-generic-password -s MY_API_KEY -w)"   # in .zshrc
   ```
2. **Reference the env var** in MCP and tool configs instead of the raw value, then clean up old backups.
3. **One key per tool, with a monthly spend cap**, so a leak in one tool doesn't drain everything.
4. **Rotate** anything that was in shell history, a git-tracked file, or a third-party web console.

## Why now

On Oct 17, 2026 OpenCode [confirmed a breach](https://x.com/opencode) affecting 1.4% of Console users who had connected their own OpenAI/Anthropic/Google keys. You can't audit someone else's server. You can know exactly where your keys are on your own machine.

## License

MIT · made by [@HeyAIpenguin](https://x.com/HeyAIpenguin)
