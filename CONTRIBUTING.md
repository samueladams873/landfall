# Contributing to PenguinPort

Thanks for your interest! PenguinPort helps everyday people move from Windows to Linux
without losing their files, apps, or browser data — and without ever touching a terminal.
That goal shapes everything here: **if a change would make the app harder for a nervous,
non-technical Windows switcher, it probably doesn't belong.**

## Ways to help

- **Try it and report what breaks.** The most valuable thing right now is real-world testing.
  Open an issue with what you did, what you expected, and what happened.
- **Suggest Linux app matches.** Know a great Linux alternative to a popular Windows app?
  The app map lives in `src/landfall/data/app_map.json`.
- **Improve the wording.** Every on-screen sentence should be plain and friendly. If
  something reads as jargon, that's a bug.
- **Code.** Bug fixes and features are welcome — see below.

## Ground rules

- **No terminal on the Linux side, ever.** New switchers should never have to type a command.
- **Never offer Microsoft apps as Linux alternatives** (no Edge, no Office online).
- **Only ever read the Windows drive.** PenguinPort must never change, move, or delete anything
  on the source PC.
- **Keep it accessible.** Big buttons, plain words, clear steps.

## Setting up for development

```
git clone https://github.com/voidwhereprohibited/penguinport.git
cd penguinport
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run the app:

```
python run_landfall.py
```

Run the tests (please make sure they pass before opening a PR):

```
QT_QPA_PLATFORM=offscreen pytest -q
```

## Pull requests

1. Fork, branch, make your change.
2. Add or update a test if you changed behavior.
3. Make sure `pytest -q` passes.
4. Open the PR with a short description of *what* changed and *why*.

Small, focused PRs are easier to review and land faster. Thank you for helping people
land safely on Linux!
