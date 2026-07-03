# Blender Sync

Sync Blender settings, addons, and extensions across multiple computers using Git.

## Installation

1. **Install Git** — [git-scm.com](https://git-scm.com)
2. **Install the addon** — Download `blender_sync.zip` from [Releases](https://github.com/your-org/blender-sync/releases), then Blender → Edit → Preferences → Add-ons → Install
3. **Configure** — Set your Git remote URL and branch in Preferences
4. **Sync** — Click **Sync Now** in the 3D View sidebar (press `N` to open)

## What Gets Synced

| Path | Description |
|------|-------------|
| `config/userpref.blend` | User preferences |
| `config/startup.blend` | Startup file |
| `config/bookmarks.txt` | File browser bookmarks |
| `config/recent-*.txt` | Recent files & searches (opt-in) |
| `scripts/presets/` | User presets |
| `scripts/addons/` | Traditional addons (≤ 50 MB each) |
| `extensions/` | Blender extensions |

**Not synced:** cache, temp files, large assets, system addons, credentials.

## Sidebar Controls

| Button | What it does |
|--------|--------------|
| **Sync Now** | Full sync: export → commit → pull → merge → push → apply |
| **Check Remote** | Check if remote has new changes |
| **Push Local** | Upload local settings to remote |
| **Pull Remote** | Download and apply remote settings |
| **Resolve Conflict** | Choose "keep local" or "keep remote" |
| **View History** | Browse sync commit history |
| **Rollback** | Restore to a previous sync point |

## Configuration

All settings live in Blender → Edit → Preferences → Add-ons → Blender Sync:

- **Remote URL** — Git repo URL (SSH or HTTPS)
- **Branch** — Git branch (default: `main`)
- **Sync Interval** — Auto-check every N seconds (default: 7200 = 2 hours)
- **Ignore Patterns** — Glob patterns to skip files/directories (one per line)
- **Plugin Size Threshold** — Skip large addon directories (default: 50 MB)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Git not found" | Install Git and add it to your PATH |
| Authentication failed | Check SSH key (`ssh -T git@github.com`) or HTTPS credential helper |
| Remote unreachable | Check network and Remote URL |
| UI stuck after button | Wait — network ops run in background. Result appears as popup. |
| Lock file left after crash | Delete `blender-sync-state/runtime/lock` in plugin data dir |
| Debug logging | Enable **Debug Logging** in Preferences, click **Open Log File** |

## Data Storage

All sync data lives at:
```
<Blender user dir>/scripts/blender_sync_data/blender-sync-state/
├── repo/          # Git staging repository
├── runtime/       # Status files, lock, logs
└── backups/       # Timestamped backups before each apply
```

## License

MIT
