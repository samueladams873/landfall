# Landfall

**Move from Windows to Linux without losing anything, and without ever opening a terminal.**

Landfall is a free, open-source moving helper for people leaving Windows 10. Run it on your
Windows PC, plug in a USB drive, and it packs up your files, browser data, email, contacts,
Wi-Fi networks and more into one password-locked bundle. Plug that drive into your new Linux
PC, double-click Landfall, and everything lands where it belongs, with your apps installed.

It works with any Linux distro, and it only ever *reads* your Windows drive. It never changes
or repartitions anything.

> **Status: early development (v0.2).** Landfall can already check a Windows PC, pack your
> personal folders into a locked bundle, and unpack them on Linux with your apps installed.
> The rest of the list below is being built now, one piece at a time.

![Landfall on Windows](docs/screenshots/v0.2-welcome.png)

## What Landfall will move

| | What | Status |
|---|---|---|
| 🔍 | **Readiness report:** which apps and hardware will work on Linux | ✅ Working |
| 🎨 | **Friendly step-by-step wizard** with a classic Windows-style look | ✅ Working |
| 📁 | **Your files:** Desktop, Documents, Pictures, Downloads, Music, Videos | ✅ Working |
| 🌐 | **Browsers:** bookmarks, saved passwords, history (Chrome, Edge, Firefox) | Planned |
| ✉️ | **Email and contacts:** Outlook and Thunderbird mail, Windows and Outlook contacts | Planned |
| 📶 | **Wi-Fi networks and passwords** | Planned |
| 🖼️ | **Personal touches:** wallpaper and fonts | Planned |
| 🎮 | **Game saves** | Planned |
| 🔑 | **Product keys and licenses list**, so you don't lose paid software | Planned |
| 📦 | **Apps:** matched Linux apps installed with one click | ✅ Working |

## On the Linux side

- Double-click the Landfall installer on the USB drive (.deb for Ubuntu and Mint, .rpm for
  Fedora), click **Install**, then open Landfall from your app menu. No terminal, ever.
- Enter the bundle password you chose on Windows.
- Landfall puts your files in the matching folders, installs your apps, loads your bookmarks
  and contacts, connects your Wi-Fi and sets your wallpaper.
- You finish with a short "what's left to do" checklist.

## Safety first

- **Read-only on Windows:** Landfall never modifies, deletes or repartitions anything.
- **Encrypted:** passwords, browser data and email only travel inside an AES-256 bundle you
  can open with free 7-Zip.
- **No internet needed, no tracking:** Landfall has no network code and sends nothing anywhere.
- **No surprises:** see the bundle size before packing, check the USB has room, resume if
  unplugged, and verify every file arrived intact.

## Roadmap

- [x] Phase 0: Setup and build pipeline
- [x] Phase 1: Readiness report
- [ ] Phase 2: Wizard look, and packing everything into the encrypted bundle (files done)
- [ ] Phase 3: Linux importer (unpack, install apps, restore settings) (files and apps done)
- [ ] Phase 4: Public launch (v1.0)

## Run from source

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m landfall
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
