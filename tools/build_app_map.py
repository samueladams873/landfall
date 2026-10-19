"""Generates src/landfall/data/app_map.json.

Edit the lists below, then run:  python tools/build_app_map.py
Rules: up to 5 Linux options per Windows app, the most widely used / best data-moving pick
first, real Linux apps only (never Microsoft apps), every Flatpak ID checked against Flathub
(tests/test_phase1.py and tools/fetch_logos.py both check).
Sources: Flathub listings; github.com/hardbsdk/awesome-alternatives; AlternativeTo.
"""
import json
from pathlib import Path


def o(name, fp=None, about="", cmds=(), snap=None, url=None, new=False, included=False):
    d = {"name": name, "about": about}
    if included:
        d["included"] = True   # comes with Linux already: shown, never installed
    if fp:
        d["flatpak"] = fp
    if cmds:
        d["commands"] = list(cmds)
    if snap:
        d["snap"] = snap
    if url:
        d["url"] = url
    if new:
        d["new"] = True
    return d


# --- browsers: the description says what data comes along ---------------------------------
FF_KEEP = o("Firefox", "org.mozilla.firefox", "Your best match: Firefox bookmarks, history and passwords can come over as they are.", ["firefox"], "firefox")
FF = o("Firefox", "org.mozilla.firefox", "Fast, private browser. Imports your bookmarks and saved passwords.", ["firefox"], "firefox")
CHR = o("Chromium", "org.chromium.Chromium", "Chrome without Google. Same look; imports your bookmarks and passwords.", ["chromium", "chromium-browser"], "chromium")
GC = o("Google Chrome", "com.google.Chrome", "Google's browser. Sign in and your bookmarks and passwords come back.", ["google-chrome", "google-chrome-stable"])
BRV = o("Brave", "com.brave.Browser", "Chrome-like, blocks ads and trackers. Imports bookmarks and passwords.", ["brave-browser"], "brave")
VIV = o("Vivaldi", "com.vivaldi.Vivaldi", "Chrome-based and very customisable. Imports bookmarks and passwords.", ["vivaldi"])
ZEN = o("Zen Browser", "app.zen_browser.zen", "Sleek Firefox-based browser with vertical tabs.", ["zen-browser"])
# --- everyday apps --------------------------------------------------------------------------
TB = o("Thunderbird", "org.mozilla.Thunderbird", "Email, calendar and contacts. Works with Gmail, Outlook.com and more.", ["thunderbird"], "thunderbird")
BETTERBIRD = o("Betterbird", "eu.betterbird.Betterbird", "Thunderbird with extra fixes and features.", ["betterbird"])
EVOLUTION = o("Evolution", "org.gnome.Evolution", "Email, calendar and contacts in one, Outlook-style.", ["evolution"])
GEARY = o("Geary", "org.gnome.Geary", "Simple, modern email app.", ["geary"])
LO = o("LibreOffice", "org.libreoffice.LibreOffice", "Free office suite. Opens and saves Word, Excel and PowerPoint files.", ["libreoffice", "soffice"])
OO = o("ONLYOFFICE", "org.onlyoffice.desktopeditors", "Office suite with a familiar ribbon toolbar. Opens Word and Excel files.", ["onlyoffice-desktopeditors"])
STRAWBERRY = o("Strawberry", "org.strawberrymusicplayer.strawberry", "Music library player, great for big collections.", ["strawberry"])
RHYTHMBOX = o("Rhythmbox", "org.gnome.Rhythmbox3", "Simple music player and library.", ["rhythmbox"])
ELISA = o("Elisa", "org.kde.elisa", "Clean, easy music player.", ["elisa"])
LOLLYPOP = o("Lollypop", "org.gnome.Lollypop", "Good-looking music player for your albums.", ["lollypop"])
AMBEROL = o("Amberol", "io.bassi.Amberol", "Tiny player: drop in songs and press play.", ["amberol"])
VLC = o("VLC", "org.videolan.VLC", "Plays almost any video or music file.", ["vlc"], "vlc")
MPV = o("mpv", "io.mpv.Mpv", "Simple, fast video player.", ["mpv"])
CELLULOID = o("Celluloid", "io.github.celluloid_player.Celluloid", "Easy video player with a clean look.", ["celluloid"])
HARUNA = o("Haruna", "org.kde.haruna", "Video player with handy extras like YouTube links.", ["haruna"])
SHOWTIME = o("Showtime", "org.gnome.Showtime", "Simple video player for everyday watching.")
KODI = o("Kodi", "tv.kodi.Kodi", "Turns your PC into a home-theatre media centre.", ["kodi"])
PLEX = o("Plex", "tv.plex.PlexDesktop", "Watch your Plex library.")
GIMP = o("GIMP", "org.gimp.GIMP", "Powerful photo editor, the classic Photoshop alternative.", ["gimp"], "gimp")
KRITA = o("Krita", "org.kde.krita", "Great for drawing and painting.", ["krita"], "krita")
PINTA = o("Pinta", "com.github.PintaProject.Pinta", "Simple image editor, like Paint.NET.", ["pinta"], "pinta")
PHOTOCRAFT = o("PhotoCraft", None, "Brand-new free Photoshop look-alike that opens PSD files. Still young.", url="https://github.com/storytold/photocraft", new=True)
INKSCAPE = o("Inkscape", "org.inkscape.Inkscape", "Professional vector drawing and logos.", ["inkscape"], "inkscape")
VECTORCRAFT = o("VectorCraft", None, "Brand-new free Illustrator look-alike. Still young.", url="https://github.com/storytold/vectorcraft", new=True)
DRAWIO = o("draw.io", "com.jgraph.drawio.desktop", "Diagrams and flowcharts. Opens Visio files.", ["drawio"])
KDENLIVE = o("Kdenlive", "org.kde.kdenlive", "Full video editor, easy to learn.", ["kdenlive"], "kdenlive")
SHOTCUT = o("Shotcut", "org.shotcut.Shotcut", "Simple, reliable video editor.", ["shotcut"], "shotcut")
OPENSHOT = o("OpenShot", "org.openshot.OpenShot", "Beginner-friendly video editor.", ["openshot-qt"])
RESOLVE = o("DaVinci Resolve", None, "Hollywood-grade editor. Free download from Blackmagic.", url="https://www.blackmagicdesign.com/products/davinciresolve")
FILMCRAFT = o("FilmCraft", None, "Brand-new free Premiere look-alike. Still young.", url="https://github.com/storytold/filmcraft", new=True)
HANDBRAKE = o("HandBrake", "fr.handbrake.ghb", "Converts and shrinks videos.", ["ghb"])
DARKTABLE = o("darktable", "org.darktable.Darktable", "Photo library and RAW editor.", ["darktable"], "darktable")
RAWTHERAPEE = o("RawTherapee", "com.rawtherapee.RawTherapee", "Powerful RAW photo developer.", ["rawtherapee"])
DIGIKAM = o("digiKam", "org.kde.digikam", "Organises big photo collections.", ["digikam"])
LIGHTCRAFT = o("LightCraft", None, "Brand-new free Lightroom look-alike. Still young.", url="https://github.com/storytold/lightcraft", new=True)
OKULAR = o("Okular", "org.kde.okular", "Read, fill in and sign PDFs.", ["okular"], "okular")
PAPERS = o("Papers", "org.gnome.Papers", "Simple, fast PDF reader.")
PDFARRANGER = o("PDF Arranger", "com.github.jeromerobert.pdfarranger", "Merge, split and reorder PDF pages.", ["pdfarranger"])
XOURNAL = o("Xournal++", "com.github.xournalpp.xournalpp", "Write and draw on PDFs, handwritten notes.", ["xournalpp"])
PDFCRAFT = o("PdfCraft", None, "Brand-new free Acrobat look-alike. Still young.", url="https://github.com/storytold/pdfcraft", new=True)
KATE = o("Kate", "org.kde.kate", "Powerful text editor with tabs, like Notepad++.", ["kate"], "kate")
NOTEPADQQ = o("Notepadqq", "com.notepadqq.Notepadqq", "Made to look like Notepad++.", ["notepadqq"])
GTEXT = o("Text Editor", "org.gnome.TextEditor", "Clean, simple text editor.", ["gnome-text-editor"])
VSCODE = o("Visual Studio Code", "com.visualstudio.code", "The popular code editor.", ["code"], "code")
VSCODIUM = o("VSCodium", "com.vscodium.codium", "VS Code without the tracking.", ["codium"], "codium")
SUBLIME = o("Sublime Text", "com.sublimetext.three", "Fast, polished text and code editor.", ["subl"])
PEAZIP = o("PeaZip", "io.github.peazip.PeaZip", "Opens zip, 7z, rar and more.", ["peazip"])
ARK = o("Ark", "org.kde.ark", "Simple zip and archive manager.", ["ark"])
FILEROLLER = o("Archive Manager", "org.gnome.FileRoller", "Opens and makes zip files.", ["file-roller"])
KEEPASSXC = o("KeePassXC", "org.keepassxc.KeePassXC", "Opens your KeePass password files.", ["keepassxc"], "keepassxc")
BITWARDEN = o("Bitwarden", "com.bitwarden.desktop", "Free password manager that syncs everywhere.", ["bitwarden"], "bitwarden")
OBSIDIAN = o("Obsidian", "md.obsidian.Obsidian", "Popular notes app; your notes stay as simple files.", ["obsidian"])
JOPLIN = o("Joplin", "net.cozic.joplin_desktop", "Free notes app. Imports OneNote and Evernote notes.", ["joplin"])
LOGSEQ = o("Logseq", "com.logseq.Logseq", "Notes and outlines that link together.", ["logseq"])
APPFLOWY = o("AppFlowy", "io.appflowy.AppFlowy", "Notion-style notes, tasks and databases.")
ERRANDS = o("Errands", "io.github.mrvladus.List", "Simple to-do lists.")
STEAM = o("Steam", "com.valvesoftware.Steam", "The same Steam. Most Windows games run through Proton.", ["steam"])
HEROIC = o("Heroic Games Launcher", "com.heroicgameslauncher.hgl", "Plays your Epic, GOG and Amazon games on Linux.", ["heroic"])
LUTRIS = o("Lutris", "net.lutris.Lutris", "Runs Battle.net, EA and Ubisoft games through Wine.", ["lutris"])
BOTTLES = o("Bottles", "com.usebottles.bottles", "Runs many Windows programs on Linux.", ["bottles"])
PRISM = o("Prism Launcher", "org.prismlauncher.PrismLauncher", "Minecraft Java with easy mods.", ["prismlauncher"])
DISCORD = o("Discord", "com.discordapp.Discord", "Chat, voice and communities.", ["discord"], "discord")
VESKTOP = o("Vesktop", "dev.vencord.Vesktop", "Discord with better screen sharing on Linux.")
QBIT = o("qBittorrent", "org.qbittorrent.qBittorrent", "Clean, ad-free torrent app.", ["qbittorrent"])
TRANSMISSION = o("Transmission", "com.transmissionbt.Transmission", "Simple, light torrent app.", ["transmission-gtk"])
FILEZILLA = o("FileZilla", "org.filezillaproject.Filezilla", "Reliable FTP and SFTP file transfer.", ["filezilla"])
RUSTDESK = o("RustDesk", "com.rustdesk.RustDesk", "Free remote-desktop app, like TeamViewer.", ["rustdesk"])
ANYDESK = o("AnyDesk", "com.anydesk.Anydesk", "Popular remote-desktop app.", ["anydesk"])
FLAMESHOT = o("Flameshot", "org.flameshot.Flameshot", "Screenshots you can mark up, like Snipping Tool.", ["flameshot"])
OBS = o("OBS Studio", "com.obsproject.Studio", "Record your screen and stream live.", ["obs"], "obs-studio")
AUDACITY = o("Audacity", "org.audacityteam.Audacity", "Record and edit audio.", ["audacity"])
TENACITY = o("Tenacity", "org.tenacityaudio.Tenacity", "Audacity-based, no tracking.")
LMMS = o("LMMS", "io.lmms.LMMS", "Free music-making studio, like FL Studio.", ["lmms"])
ARDOUR = o("Ardour", "org.ardour.Ardour", "Pro recording and mixing studio.", ["ardour"])
FREECAD = o("FreeCAD", "org.freecad.FreeCAD", "3D design for real-world parts.", ["freecad"])
LIBRECAD = o("LibreCAD", "org.librecad.librecad", "2D drafting, opens DXF drawings.", ["librecad"])
BLENDER = o("Blender", "org.blender.Blender", "Free, professional 3D modelling and animation.", ["blender"], "blender")
CALIBRE = o("Calibre", "com.calibre_ebook.calibre", "Organise and convert e-books.", ["calibre"])
FSEARCH = o("FSearch", "io.github.cboxdoerfer.FSearch", "Instant file search, like Everything.", ["fsearch"])
BLEACHBIT = o("BleachBit", "org.bleachbit.BleachBit", "Frees up space and clears junk, like CCleaner.", ["bleachbit"])
ZAPZAP = o("ZapZap", "com.rtosta.zapzap", "WhatsApp on your desktop.", ["zapzap"])
ANKI = o("Anki", "net.ankiweb.Anki", "Flashcards that help you remember.", ["anki"])
OCTAVE = o("GNU Octave", "org.octave.Octave", "Runs most MATLAB code.", ["octave"])
POSTMAN = o("Postman", "com.getpostman.Postman", "Test and build web APIs.")
NATRON = o("Natron", "fr.natron.Natron", "Visual effects and compositing.", ["natron"])
EFFECTCRAFT = o("EffectCraft", None, "Brand-new free After Effects look-alike. Still young.", url="https://github.com/storytold/effectcraft", new=True)
SCRIBUS = o("Scribus", "net.scribus.Scribus", "Page layout for flyers, magazines and books.", ["scribus"], "scribus")
DESIGNCRAFT = o("DesignCraft", None, "Brand-new free InDesign look-alike. Still young.", url="https://github.com/storytold/designcraft", new=True)
LOUPE = o("Image Viewer", "org.gnome.Loupe", "Fast, simple photo viewer.", ["loupe"])
GWENVIEW = o("Gwenview", "org.kde.gwenview", "Photo viewer with quick edits.", ["gwenview"])
SHOTWELL = o("Shotwell", "org.gnome.Shotwell", "Photo albums and simple fixes.", ["shotwell"])
DRAWING = o("Drawing", "com.github.maoschanz.drawing", "Basic drawing app, just like Paint.", ["drawing"])
GCALC = o("Calculator", "org.gnome.Calculator", "Everyday calculator.", ["gnome-calculator"])
KCALC = o("KCalc", "org.kde.kcalc", "Scientific calculator.", ["kcalc"])
QALC = o("Qalculate!", "io.github.Qalculate", "Powerful calculator with unit conversion.", ["qalculate-gtk"])
STICKY = o("Sticky Notes", "com.vixalien.sticky", "Little notes on your desktop.")
RECORDER = o("Sound Recorder", "org.gnome.SoundRecorder", "Record voice memos.", ["gnome-sound-recorder"])
SNAPSHOT = o("Camera", "org.gnome.Snapshot", "Take photos and videos with your webcam.", ["snapshot"])
CHEESE = o("Cheese", "org.gnome.Cheese", "Webcam photos with fun effects.", ["cheese"])
CLOCKS = o("Clocks", "org.gnome.clocks", "Alarms, timers and world clocks.", ["gnome-clocks"])
WEATHER = o("Weather", "org.gnome.Weather", "Today's weather and the forecast.", ["gnome-weather"])
MAPS = o("Maps", "org.gnome.Maps", "Maps and directions.", ["gnome-maps"])
GCAL = o("Calendar", "org.gnome.Calendar", "Simple calendar. Connects to Google and Outlook accounts.", ["gnome-calendar"])


RCLONE = o("RClone Manager", "io.github.zarestia_dev.rclone-manager", "Syncs OneDrive, Google Drive, Dropbox and iCloud on Linux.")
ONLINE = o("Online Accounts", None, "Comes with Ubuntu: sign in under Settings, and your cloud drive shows up in Files.", included=True)
DROPBOX = o("Dropbox", "com.dropbox.Client", "Dropbox's own Linux app.", ["dropbox"])
NEXTCLOUD = o("Nextcloud", "com.nextcloud.desktopclient.nextcloud", "Sync with your own private cloud.", ["nextcloud"])
TEAMS_LINUX = o("Teams for Linux", "com.github.IsmaelMartinez.teams_for_linux", "Free, unofficial app for joining your Teams chats and meetings.", ["teams-for-linux"])
JITSI = o("Jitsi Meet", "org.jitsi.jitsi-meet", "Free video calls, no account needed.")
ZOOM = o("Zoom", "us.zoom.Zoom", "Video meetings.", ["zoom"], "zoom-client")
SIGNAL = o("Signal", "org.signal.Signal", "Private messages and calls.", ["signal-desktop"], "signal-desktop")
GREENLIGHT = o("Greenlight", "io.github.unknownskl.greenlight", "Plays your Xbox Cloud Gaming and Game Pass library.")
CLAMTK = o("ClamTk", "com.gitlab.davem.ClamTk", "Optional virus scanner. Most Linux users don't need one.")
FILES = o("Files", None, "Comes with Linux: your file manager, with all your folders.", included=True)
SETTINGS = o("Settings", None, "Comes with Linux: Wi-Fi, display, printers, accounts and more.", included=True)
SOFTWARE = o("App Center", None, "Comes with Linux: the app store for finding and updating apps.", included=True)
TERMINAL = o("Terminal", None, "Comes with Linux. You won't need it, but it's there.", included=True)
MISSION = o("Mission Center", "io.missioncenter.MissionCenter", "See what's using your CPU, memory and disks, like Task Manager.")
RESOURCES = o("Resources", "net.nokyan.Resources", "Simple system monitor; close stuck apps.")
BAOBAB = o("Disk Usage Analyzer", "org.gnome.baobab", "See what's filling up your disk.", ["baobab"])
REMMINA = o("Remmina", "org.remmina.Remmina", "Connects to Windows PCs with Remote Desktop.", ["remmina"])
PIKA = o("Pika Backup", "org.gnome.World.PikaBackup", "Easy, automatic backups.")
DEJADUP = o("Deja Dup", "org.gnome.DejaDup", "Simple backups to a drive or the cloud.", ["deja-dup"])
CHARACTERS = o("Characters", "org.gnome.Characters", "Find and copy special characters and emoji.", ["gnome-characters"])
SOLITAIRE = o("Solitaire", "org.gnome.Aisleriot", "Classic card games: Klondike, FreeCell, Spider and more.", ["sol"])
LOCALSEND = o("LocalSend", "org.localsend.localsend_app", "Send files to your phone over Wi-Fi.")
CONTACTS = o("Contacts", "org.gnome.Contacts", "Your address book.", ["gnome-contacts"])

ONE = lambda name, fp, about, cmds=(), snap=None: [o(name, fp, about, cmds, snap)]

# (Windows app, name patterns, status, category, options).  status "none" = nothing to install.
APPS = [
 # Web browsers: the recommended pick is the one that carries the user's data best.
 ("Mozilla Firefox", ["^mozilla firefox"], "same", "Web browser", [FF_KEEP, ZEN, CHR, BRV]),
 ("Google Chrome", ["^google chrome"], "same", "Web browser", [GC, CHR, BRV, FF, VIV]),
 ("Microsoft Edge", ["^microsoft edge$"], "alternative", "Web browser", [FF, CHR, BRV, GC, VIV]),
 ("Brave", ["^brave"], "same", "Web browser", [BRV, FF, CHR]),
 ("Opera", ["^opera"], "alternative", "Web browser", [VIV, BRV, FF, CHR]),
 ("Vivaldi", ["^vivaldi"], "same", "Web browser", [VIV, FF, CHR]),
 # Email
 ("Mozilla Thunderbird", ["thunderbird"], "same", "Email", [TB, BETTERBIRD]),
 ("Microsoft Outlook", ["^microsoft outlook"], "alternative", "Email", [TB, EVOLUTION, BETTERBIRD, GEARY]),
 ("Mailbird", ["^mailbird"], "alternative", "Email", [TB, GEARY, EVOLUTION]),
 ("eM Client", ["^em client"], "alternative", "Email", [TB, EVOLUTION, BETTERBIRD]),
 # Office
 ("Microsoft Office", ["^microsoft office", "^microsoft 365"], "alternative", "Office", [LO, OO]),
 ("WPS Office", ["^wps office"], "alternative", "Office", [LO, OO]),
 ("Microsoft Visio", ["^microsoft visio"], "alternative", "Diagrams", [DRAWIO, LO]),
 # Music and video
 ("iTunes", ["^itunes$"], "alternative", "Music player", [STRAWBERRY, RHYTHMBOX, ELISA, LOLLYPOP, AMBEROL]),
 ("MusicBee", ["^musicbee"], "alternative", "Music player", [STRAWBERRY, ELISA, LOLLYPOP, RHYTHMBOX]),
 ("foobar2000", ["^foobar2000"], "alternative", "Music player", [STRAWBERRY, ELISA, AMBEROL]),
 ("Winamp", ["^winamp"], "alternative", "Music player", [STRAWBERRY, AMBEROL, ELISA]),
 ("AIMP", ["^aimp"], "alternative", "Music player", [STRAWBERRY, ELISA, AMBEROL]),
 ("Spotify", ["^spotify"], "same", "Music streaming", ONE("Spotify", "com.spotify.Client", "The same Spotify.", ["spotify"], "spotify")),
 ("VLC media player", ["^vlc media player"], "same", "Video player", [VLC, MPV, CELLULOID, HARUNA, SHOWTIME]),
 ("PotPlayer", ["potplayer"], "alternative", "Video player", [VLC, MPV, CELLULOID, HARUNA]),
 ("MPC-HC", ["^mpc-hc", "media player classic"], "alternative", "Video player", [MPV, VLC, CELLULOID, HARUNA]),
 ("KMPlayer", ["^kmplayer"], "alternative", "Video player", [VLC, MPV, CELLULOID]),
 ("Kodi", ["^kodi"], "same", "Media centre", [KODI]),
 ("Plex", ["^plex"], "same", "Media centre", [PLEX, KODI]),
 # Photos and design
 ("Adobe Photoshop", ["^adobe photoshop"], "alternative", "Photo editing", [GIMP, KRITA, PHOTOCRAFT, PINTA]),
 ("GIMP", ["^gimp"], "same", "Photo editing", [GIMP]),
 ("Paint.NET", ["^paint\\.net"], "alternative", "Photo editing", [PINTA, GIMP, KRITA]),
 ("Affinity Photo", ["^affinity photo"], "alternative", "Photo editing", [GIMP, KRITA, PHOTOCRAFT]),
 ("Adobe Illustrator", ["^adobe illustrator"], "alternative", "Drawing and design", [INKSCAPE, VECTORCRAFT, KRITA]),
 ("CorelDRAW", ["^coreldraw"], "alternative", "Drawing and design", [INKSCAPE, VECTORCRAFT]),
 ("Affinity Designer", ["^affinity designer"], "alternative", "Drawing and design", [INKSCAPE, VECTORCRAFT]),
 ("Adobe Lightroom", ["^adobe lightroom"], "alternative", "Photo library", [DARKTABLE, RAWTHERAPEE, DIGIKAM, LIGHTCRAFT]),
 ("Adobe Premiere Pro", ["^adobe premiere"], "alternative", "Video editing", [KDENLIVE, SHOTCUT, RESOLVE, OPENSHOT, FILMCRAFT]),
 ("Filmora", ["filmora"], "alternative", "Video editing", [KDENLIVE, SHOTCUT, OPENSHOT]),
 ("CapCut", ["^capcut"], "alternative", "Video editing", [KDENLIVE, SHOTCUT, OPENSHOT]),
 ("VEGAS Pro", ["^vegas pro"], "alternative", "Video editing", [KDENLIVE, SHOTCUT, RESOLVE]),
 ("DaVinci Resolve", ["^davinci resolve"], "same", "Video editing", [RESOLVE, KDENLIVE]),
 ("HandBrake", ["^handbrake"], "same", "Video converting", [HANDBRAKE]),
 ("Adobe After Effects", ["^adobe after effects"], "alternative", "Visual effects", [NATRON, EFFECTCRAFT]),
 ("Adobe InDesign", ["^adobe indesign"], "alternative", "Page layout", [SCRIBUS, DESIGNCRAFT]),
 ("Adobe Acrobat", ["^adobe acrobat"], "alternative", "PDF", [OKULAR, PAPERS, PDFARRANGER, XOURNAL, PDFCRAFT]),
 ("Foxit PDF Reader", ["^foxit"], "alternative", "PDF", [OKULAR, PAPERS, XOURNAL]),
 ("SumatraPDF", ["^sumatrapdf"], "alternative", "PDF", [PAPERS, OKULAR]),
 ("Blender", ["^blender"], "same", "3D", [BLENDER]),
 ("AutoCAD", ["^autocad"], "alternative", "CAD", [FREECAD, LIBRECAD]),
 ("SketchUp", ["^sketchup"], "alternative", "CAD", [FREECAD, BLENDER]),
 # Audio
 ("Audacity", ["^audacity"], "same", "Audio editing", [AUDACITY, TENACITY]),
 ("FL Studio", ["^fl studio", "^image-line fl studio"], "alternative", "Music making", [LMMS, ARDOUR]),
 ("Ableton Live", ["^ableton live"], "alternative", "Music making", [ARDOUR, LMMS]),
 # Writing, notes, tasks
 ("Notepad++", ["^notepad\\+\\+"], "alternative", "Text editor", [KATE, NOTEPADQQ, GTEXT, SUBLIME]),
 ("Sublime Text", ["^sublime text"], "same", "Text editor", [SUBLIME, KATE]),
 ("Visual Studio Code", ["^microsoft visual studio code"], "same", "Coding", [VSCODE, VSCODIUM]),
 ("Microsoft OneNote", ["^microsoft onenote"], "alternative", "Notes", [JOPLIN, XOURNAL, OBSIDIAN, LOGSEQ]),
 ("Evernote", ["^evernote"], "alternative", "Notes", [JOPLIN, OBSIDIAN, LOGSEQ]),
 ("Obsidian", ["^obsidian"], "same", "Notes", [OBSIDIAN, LOGSEQ]),
 ("Notion", ["^notion"], "alternative", "Notes", [APPFLOWY, OBSIDIAN, JOPLIN]),
 ("Microsoft To Do", ["^microsoft to do"], "alternative", "To-do lists", [ERRANDS]),
 ("Anki", ["^anki"], "same", "Study", [ANKI]),
 ("Calibre", ["^calibre"], "same", "E-books", [CALIBRE]),
 # Passwords
 ("KeePass", ["^keepass"], "alternative", "Passwords", [KEEPASSXC]),
 ("Bitwarden", ["^bitwarden"], "same", "Passwords", [BITWARDEN, KEEPASSXC]),
 ("LastPass", ["^lastpass"], "alternative", "Passwords", [BITWARDEN, KEEPASSXC]),
 ("1Password", ["^1password"], "alternative", "Passwords", [BITWARDEN, KEEPASSXC]),
 ("Dashlane", ["^dashlane"], "alternative", "Passwords", [BITWARDEN, KEEPASSXC]),
 # Chat and calls
 ("Discord", ["^discord$"], "same", "Chat", [DISCORD, VESKTOP]),
 ("Slack", ["^slack"], "same", "Chat", ONE("Slack", "com.slack.Slack", "The same Slack.", ["slack"], "slack")),
 ("Signal", ["^signal"], "same", "Chat", ONE("Signal", "org.signal.Signal", "The same Signal.", ["signal-desktop"], "signal-desktop")),
 ("Telegram Desktop", ["^telegram"], "same", "Chat", ONE("Telegram", "org.telegram.desktop", "The same Telegram.", ["telegram-desktop"], "telegram-desktop")),
 ("WhatsApp", ["^whatsapp"], "alternative", "Chat", [ZAPZAP]),
 ("Zoom", ["^zoom"], "same", "Video calls", ONE("Zoom", "us.zoom.Zoom", "The same Zoom.", ["zoom"], "zoom-client")),
 ("Microsoft Teams", ["^microsoft teams"], "alternative", "Video calls", [TEAMS_LINUX, ZOOM, JITSI]),
 ("Skype", ["^skype"], "alternative", "Video calls", [ZOOM, SIGNAL, JITSI]),
 # Games
 ("Steam", ["^steam$"], "same", "Games", [STEAM]),
 ("Epic Games Launcher", ["^epic games launcher"], "alternative", "Games", [HEROIC, LUTRIS]),
 ("GOG GALAXY", ["^gog galaxy"], "alternative", "Games", [HEROIC, LUTRIS]),
 ("EA app", ["^ea app$", "^ea desktop", "^origin$"], "alternative", "Games", [LUTRIS, HEROIC, BOTTLES]),
 ("Ubisoft Connect", ["^ubisoft connect", "^uplay"], "alternative", "Games", [LUTRIS, HEROIC]),
 ("Battle.net", ["^battle\\.net"], "wine", "Games", [LUTRIS, BOTTLES]),
 ("Minecraft Launcher", ["^minecraft launcher", "^minecraft$"], "alternative", "Games", [PRISM]),
 ("Xbox", ["^xbox"], "alternative", "Games", [GREENLIGHT, STEAM]),
 # Recording, sharing, tools
 ("OBS Studio", ["^obs studio"], "same", "Screen recording", [OBS]),
 ("ShareX", ["^sharex"], "alternative", "Screenshots", [FLAMESHOT]),
 ("Greenshot", ["^greenshot"], "alternative", "Screenshots", [FLAMESHOT]),
 ("Snagit", ["^snagit"], "alternative", "Screenshots", [FLAMESHOT, OBS]),
 ("7-Zip", ["^7-zip"], "alternative", "Zip files", [PEAZIP, ARK, FILEROLLER]),
 ("WinRAR", ["^winrar"], "alternative", "Zip files", [PEAZIP, ARK, FILEROLLER]),
 ("WinZip", ["^winzip"], "alternative", "Zip files", [PEAZIP, ARK, FILEROLLER]),
 ("qBittorrent", ["^qbittorrent"], "same", "Downloads", [QBIT]),
 ("uTorrent", ["torrent$", "^bittorrent"], "alternative", "Downloads", [QBIT, TRANSMISSION]),
 ("FileZilla", ["^filezilla"], "same", "File transfer", [FILEZILLA]),
 ("WinSCP", ["^winscp"], "alternative", "File transfer", [FILEZILLA]),
 ("TeamViewer", ["^teamviewer"], "alternative", "Remote desktop", [RUSTDESK, ANYDESK]),
 ("AnyDesk", ["^anydesk"], "same", "Remote desktop", [ANYDESK, RUSTDESK]),
 ("Everything", ["^everything"], "alternative", "File search", [FSEARCH]),
 ("CCleaner", ["^ccleaner"], "alternative", "Clean-up", [BLEACHBIT]),
 ("Postman", ["^postman"], "same", "Coding", [POSTMAN]),
 ("MATLAB", ["^matlab"], "alternative", "Maths and science", [OCTAVE]),
 # Cloud storage: no Linux app needed; the files themselves move with everything else.
 ("Microsoft OneDrive", ["^microsoft onedrive"], "alternative", "Cloud storage", [ONLINE, RCLONE, NEXTCLOUD]),
 ("Dropbox", ["^dropbox"], "same", "Cloud storage", [DROPBOX, RCLONE]),
 ("Google Drive", ["^google drive"], "alternative", "Cloud storage", [ONLINE, RCLONE]),
 ("iCloud", ["^icloud"], "alternative", "Cloud storage", [RCLONE]),
 # Antivirus: Linux doesn't need these.
 ("Norton", ["^norton"], "alternative", "Antivirus", [CLAMTK]),
 ("McAfee", ["^mcafee"], "alternative", "Antivirus", [CLAMTK]),
 ("Avast", ["^avast"], "alternative", "Antivirus", [CLAMTK]),
 ("AVG", ["^avg "], "alternative", "Antivirus", [CLAMTK]),
 ("Malwarebytes", ["^malwarebytes"], "alternative", "Antivirus", [CLAMTK]),
 ("Bitdefender", ["^bitdefender"], "alternative", "Antivirus", [CLAMTK]),
]

# Programs built into every copy of Windows. They never appear in the installed-programs
# list, so Landfall always includes them. "exe" is used to show their real icon.
SYS = "C:\\Windows\\System32\\"
BUILTIN = [
 ("Notepad", "Text editor", SYS + "notepad.exe", [GTEXT, KATE, NOTEPADQQ]),
 ("Paint", "Drawing", SYS + "mspaint.exe", [PINTA, DRAWING, KRITA]),
 ("Photos", "Photo viewer", "", [LOUPE, GWENVIEW, SHOTWELL, DIGIKAM]),
 ("Snipping Tool", "Screenshots", SYS + "SnippingTool.exe", [FLAMESHOT]),
 ("Calculator", "Calculator", SYS + "calc.exe", [GCALC, KCALC, QALC]),
 ("Windows Media Player", "Video player", "C:\\Program Files\\Windows Media Player\\wmplayer.exe", [VLC, CELLULOID, SHOWTIME, MPV]),
 ("Mail and Calendar", "Email", "", [TB, EVOLUTION, GEARY]),
 ("WordPad", "Office", "C:\\Program Files\\Windows NT\\Accessories\\wordpad.exe", [LO, OO]),
 ("Sticky Notes", "Notes", "", [STICKY, JOPLIN]),
 ("Voice Recorder", "Voice recording", SYS + "SoundRecorder.exe", [RECORDER, AUDACITY]),
 ("Camera", "Camera", "", [SNAPSHOT, CHEESE]),
 ("Alarms & Clock", "Clock", "", [CLOCKS]),
 ("Weather", "Weather", "", [WEATHER]),
 ("Maps", "Maps", "", [MAPS]),
 ("Windows Security", "Antivirus", "", [CLAMTK]),
 ("Microsoft Edge", "Web browser", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe", [FF, CHR, BRV, GC, VIV]),
 ("Mail (Outlook)", "Email", "", [TB, EVOLUTION, GEARY]),
 ("OneDrive", "Cloud storage", "", [ONLINE, RCLONE, NEXTCLOUD]),
 ("File Explorer", "Files", "C:\\Windows\\explorer.exe", [FILES]),
 ("Settings and Control Panel", "Settings", SYS + "control.exe", [SETTINGS]),
 ("Microsoft Store", "App store", "", [SOFTWARE]),
 ("Task Manager", "System monitor", SYS + "Taskmgr.exe", [MISSION, RESOURCES]),
 ("Disk Cleanup", "Clean-up", SYS + "cleanmgr.exe", [BAOBAB, BLEACHBIT]),
 ("Command Prompt and PowerShell", "Terminal", SYS + "cmd.exe", [TERMINAL]),
 ("Remote Desktop Connection", "Remote desktop", SYS + "mstsc.exe", [REMMINA, RUSTDESK]),
 ("Backup and File History", "Backups", "", [PIKA, DEJADUP]),
 ("Character Map", "Special characters", SYS + "charmap.exe", [CHARACTERS]),
 ("Microsoft Solitaire Collection", "Card games", "", [SOLITAIRE]),
 ("Phone Link", "Phone", "", [LOCALSEND]),
 ("People", "Contacts", "", [CONTACTS]),
 ("Movies & TV", "Video player", "", [VLC, CELLULOID, SHOWTIME]),
 ("Xbox Game Bar", "Screen recording", "", [OBS]),
]

out = {
    "version": 4,
    "notes": "status: same = the same app exists on Linux; alternative = a different app does "
             "the same job; wine = only runs through Wine; none = nothing to install. The first "
             "option is the recommended pick.",
    "apps": [{"windows": w, "patterns": p, "status": s, "category": c, "linux": opts}
             for w, p, s, c, opts in APPS]
            + [{"windows": w, "patterns": ["^" + w.replace("+", "\\+") + "$"],
                "status": "alternative" if opts else "none", "category": c, "builtin": True,
                "exe": exe, "linux": opts}
               for w, c, exe, opts in BUILTIN],
}
target = Path(__file__).resolve().parent.parent / "src" / "landfall" / "data" / "app_map.json"
target.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
ids = sorted({x["flatpak"] for a in out["apps"] for x in a["linux"] if "flatpak" in x})
print(len(out["apps"]), "Windows apps,", len(ids), "Linux apps with Flatpak IDs")
