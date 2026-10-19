"""Generates src/landfall/data/app_map.json. Edit the lists here, then run: python tools/build_app_map.py"""
import json
def o(name, fp=None, about="", cmds=(), snap=None, url=None, new=False):
    d = {"name": name, "about": about}
    if fp: d["flatpak"] = fp
    if cmds: d["commands"] = list(cmds)
    if snap: d["snap"] = snap
    if url: d["url"] = url
    if new: d["new"] = True
    return d
FF  = o("Firefox", "org.mozilla.firefox", "Fast, private browser. Comes with most Linux PCs.", ["firefox"], "firefox")
CHR = o("Chromium", "org.chromium.Chromium", "The open-source browser Chrome is built on. Looks and works like Chrome.", ["chromium", "chromium-browser"], "chromium")
GC  = o("Google Chrome", "com.google.Chrome", "The same Chrome you know. Sign in to get your bookmarks back.", ["google-chrome", "google-chrome-stable"])
BRV = o("Brave", "com.brave.Browser", "Chrome-like browser that blocks ads and trackers.", ["brave-browser"], "brave")
VIV = o("Vivaldi", "com.vivaldi.Vivaldi", "Customisable Chrome-based browser.", ["vivaldi"])
OPR = o("Opera", "com.opera.Opera", "The same Opera browser.", ["opera"])
LO  = o("LibreOffice", "org.libreoffice.LibreOffice", "Free office suite. Opens and saves Word, Excel and PowerPoint files.", ["libreoffice", "soffice"])
OO  = o("ONLYOFFICE", "org.onlyoffice.desktopeditors", "Office suite with a familiar ribbon toolbar. Opens Word and Excel files.", ["onlyoffice-desktopeditors"])
apps = [
 ("Google Chrome", ["^google chrome"], "same", [GC, CHR, BRV, FF]),
 ("Mozilla Firefox", ["^mozilla firefox"], "same", [FF]),
 ("Microsoft Edge", ["^microsoft edge$"], "alternative", [FF, CHR, BRV, GC]),
 ("Brave", ["^brave"], "same", [BRV, FF, CHR]),
 ("Opera", ["^opera"], "same", [OPR, FF, CHR]),
 ("Vivaldi", ["^vivaldi"], "same", [VIV, FF, CHR]),
 ("Mozilla Thunderbird", ["thunderbird"], "same", [o("Thunderbird", "org.mozilla.Thunderbird", "The same email app.", ["thunderbird"], "thunderbird")]),
 ("Microsoft Outlook", ["^microsoft outlook"], "alternative", [o("Thunderbird", "org.mozilla.Thunderbird", "Free email and calendar app. Works with Outlook.com and Gmail.", ["thunderbird"], "thunderbird")]),
 ("Spotify", ["^spotify"], "same", [o("Spotify", "com.spotify.Client", "The same Spotify.", ["spotify"], "spotify")]),
 ("Discord", ["^discord$"], "same", [o("Discord", "com.discordapp.Discord", "The same Discord.", ["discord"], "discord")]),
 ("Steam", ["^steam$"], "same", [o("Steam", "com.valvesoftware.Steam", "The same Steam. Most Windows games run through Proton.", ["steam"])]),
 ("VLC media player", ["^vlc media player"], "same", [o("VLC", "org.videolan.VLC", "The same VLC.", ["vlc"], "vlc"), o("mpv", "io.mpv.Mpv", "Simple, fast video player.", ["mpv"])]),
 ("Zoom", ["^zoom"], "same", [o("Zoom", "us.zoom.Zoom", "The same Zoom.", ["zoom"], "zoom-client")]),
 ("Slack", ["^slack"], "same", [o("Slack", "com.slack.Slack", "The same Slack.", ["slack"], "slack")]),
 ("Signal", ["^signal"], "same", [o("Signal", "org.signal.Signal", "The same Signal.", ["signal-desktop"], "signal-desktop")]),
 ("Telegram Desktop", ["^telegram"], "same", [o("Telegram", "org.telegram.desktop", "The same Telegram.", ["telegram-desktop"], "telegram-desktop")]),
 ("OBS Studio", ["^obs studio"], "same", [o("OBS Studio", "com.obsproject.Studio", "The same OBS.", ["obs"], "obs-studio")]),
 ("Audacity", ["^audacity"], "same", [o("Audacity", "org.audacityteam.Audacity", "The same Audacity.", ["audacity"])]),
 ("Blender", ["^blender"], "same", [o("Blender", "org.blender.Blender", "The same Blender.", ["blender"], "blender")]),
 ("GIMP", ["^gimp"], "same", [o("GIMP", "org.gimp.GIMP", "The same GIMP.", ["gimp"], "gimp")]),
 ("Visual Studio Code", ["^microsoft visual studio code"], "same", [o("Visual Studio Code", "com.visualstudio.code", "The same VS Code.", ["code"], "code")]),
 ("Obsidian", ["^obsidian"], "same", [o("Obsidian", "md.obsidian.Obsidian", "The same Obsidian.", ["obsidian"])]),
 ("Bitwarden", ["^bitwarden"], "same", [o("Bitwarden", "com.bitwarden.desktop", "The same Bitwarden.", ["bitwarden"], "bitwarden")]),
 ("Microsoft Office", ["^microsoft office", "^microsoft 365"], "alternative", [LO, OO]),
 ("Microsoft Teams", ["^microsoft teams"], "none", []),
 ("Microsoft OneDrive", ["^microsoft onedrive"], "none", []),
 ("Adobe Photoshop", ["^adobe photoshop"], "alternative", [o("GIMP", "org.gimp.GIMP", "Powerful photo editor, the classic Photoshop alternative.", ["gimp"], "gimp"), o("Krita", "org.kde.krita", "Great for drawing and painting.", ["krita"], "krita"), o("PhotoCraft", None, "Brand-new free Photoshop look-alike that opens PSD files. Still young.", url="https://github.com/storytold/photocraft", new=True)]),
 ("Adobe Illustrator", ["^adobe illustrator"], "alternative", [o("Inkscape", "org.inkscape.Inkscape", "Professional vector drawing.", ["inkscape"], "inkscape"), o("VectorCraft", None, "Brand-new free Illustrator look-alike. Still young.", url="https://github.com/storytold/vectorcraft", new=True)]),
 ("Adobe Premiere Pro", ["^adobe premiere"], "alternative", [o("Kdenlive", "org.kde.kdenlive", "Full video editor, easy to learn.", ["kdenlive"], "kdenlive"), o("Shotcut", "org.shotcut.Shotcut", "Simple, reliable video editor.", ["shotcut"], "shotcut"), o("DaVinci Resolve", None, "Hollywood-grade editor. Free download from Blackmagic.", url="https://www.blackmagicdesign.com/products/davinciresolve"), o("FilmCraft", None, "Brand-new free Premiere look-alike. Still young.", url="https://github.com/storytold/filmcraft", new=True)]),
 ("Adobe Lightroom", ["^adobe lightroom"], "alternative", [o("darktable", "org.darktable.Darktable", "Photo library and RAW editor.", ["darktable"], "darktable"), o("LightCraft", None, "Brand-new free Lightroom look-alike. Still young.", url="https://github.com/storytold/lightcraft", new=True)]),
 ("Adobe After Effects", ["^adobe after effects"], "alternative", [o("Natron", "fr.natron.Natron", "Visual effects and compositing.", ["natron"]), o("EffectCraft", None, "Brand-new free After Effects look-alike. Still young.", url="https://github.com/storytold/effectcraft", new=True)]),
 ("Adobe InDesign", ["^adobe indesign"], "alternative", [o("Scribus", "net.scribus.Scribus", "Page layout for flyers, magazines and books.", ["scribus"], "scribus"), o("DesignCraft", None, "Brand-new free InDesign look-alike. Still young.", url="https://github.com/storytold/designcraft", new=True)]),
 ("Adobe Acrobat", ["^adobe acrobat"], "alternative", [o("Okular", "org.kde.okular", "Read, fill in and sign PDFs.", ["okular"], "okular"), o("PDF Arranger", "com.github.jeromerobert.pdfarranger", "Merge, split and reorder PDF pages.", ["pdfarranger"]), o("PdfCraft", None, "Brand-new free Acrobat look-alike. Still young.", url="https://github.com/storytold/pdfcraft", new=True)]),
 ("Notepad++", ["^notepad\\+\\+"], "alternative", [o("Kate", "org.kde.kate", "Powerful text editor with tabs, like Notepad++.", ["kate"], "kate"), o("Notepadqq", "com.notepadqq.Notepadqq", "Made to look like Notepad++.", ["notepadqq"])]),
 ("iTunes", ["^itunes$"], "alternative", [o("Strawberry", "org.strawberrymusicplayer.strawberry", "Music library player, great for big collections.", ["strawberry"]), o("Rhythmbox", "org.gnome.Rhythmbox3", "Simple music player.", ["rhythmbox"])]),
 ("7-Zip", ["^7-zip"], "alternative", [o("PeaZip", "io.github.peazip.PeaZip", "Opens zip, 7z, rar and more.", ["peazip"])]),
 ("WinRAR", ["^winrar"], "alternative", [o("PeaZip", "io.github.peazip.PeaZip", "Opens zip, 7z, rar and more.", ["peazip"])]),
 ("KeePass", ["^keepass"], "alternative", [o("KeePassXC", "org.keepassxc.KeePassXC", "Opens your KeePass password files.", ["keepassxc"], "keepassxc")]),
 ("Paint.NET", ["^paint\\.net"], "alternative", [o("Pinta", "com.github.PintaProject.Pinta", "Simple image editor that looks like Paint.NET.", ["pinta"], "pinta")]),
 ("Epic Games Launcher", ["^epic games launcher"], "alternative", [o("Heroic Games Launcher", "com.heroicgameslauncher.hgl", "Plays your Epic and GOG games on Linux.", ["heroic"])]),
 ("Dropbox", ["^dropbox"], "none", []),
 ("Google Drive", ["^google drive"], "none", []),
 ("Battle.net", ["^battle\\.net"], "wine", [o("Lutris", "net.lutris.Lutris", "Runs Battle.net through Wine.", ["lutris"])]),
]
CATS = {'Google Chrome': 'Web browser', 'Mozilla Firefox': 'Web browser', 'Microsoft Edge': 'Web browser', 'Brave': 'Web browser', 'Opera': 'Web browser', 'Vivaldi': 'Web browser', 'Mozilla Thunderbird': 'Email', 'Microsoft Outlook': 'Email', 'Spotify': 'Music streaming', 'Discord': 'Chat', 'Steam': 'Games', 'VLC media player': 'Video player', 'Zoom': 'Video calls', 'Slack': 'Chat', 'Signal': 'Chat', 'Telegram Desktop': 'Chat', 'OBS Studio': 'Screen recording', 'Audacity': 'Audio editing', 'Blender': '3D', 'GIMP': 'Photo editing', 'Visual Studio Code': 'Coding', 'Obsidian': 'Notes', 'Bitwarden': 'Passwords', 'Microsoft Office': 'Office', 'Microsoft Teams': 'Video calls', 'Microsoft OneDrive': 'Cloud storage', 'Adobe Photoshop': 'Photo editing', 'Adobe Illustrator': 'Drawing and design', 'Adobe Premiere Pro': 'Video editing', 'Adobe Lightroom': 'Photo library', 'Adobe After Effects': 'Visual effects', 'Adobe InDesign': 'Page layout', 'Adobe Acrobat': 'PDF', 'Notepad++': 'Text editor', 'iTunes': 'Music player', '7-Zip': 'Zip files', 'WinRAR': 'Zip files', 'KeePass': 'Passwords', 'Paint.NET': 'Photo editing', 'Epic Games Launcher': 'Games', 'Battle.net': 'Games', 'Dropbox': 'Cloud storage', 'Google Drive': 'Cloud storage'}
out = {"version": 3,
       "notes": "status: none = no Linux alternative we recommend; same = the same app exists on Linux; alternative = a different app does the same job; wine = only runs through Wine. The first option is the recommended pick.",
       "apps": [{"windows": w, "patterns": p, "status": s, "category": CATS[w], "linux": opts} for w, p, s, opts in apps]}
open('src/landfall/data/app_map.json', 'w').write(json.dumps(out, indent=1) + "\n")
ids = sorted({x["flatpak"] for a in out["apps"] for x in a["linux"] if "flatpak" in x})
print(len(out["apps"]), "apps,", len(ids), "flatpak ids")

