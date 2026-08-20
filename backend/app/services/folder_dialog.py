from typing import Optional


def open_folder_dialog() -> Optional[str]:
    """
    Opens a native OS folder-browser dialog and returns the selected
    absolute path, or None if the user cancelled.

    Uses tkinter (stdlib) rather than a browser file picker because
    browsers deliberately withhold the real filesystem path from web
    pages for security - a <input type="file"> picker can't hand back
    something the backend can actually os.walk(). Since this backend
    runs locally on the same machine as the browser, popping a native
    dialog server-side is safe here and gives a real, usable path.
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # bring the dialog to the front

    try:
        selected = filedialog.askdirectory(title="Select a repository to index")
    finally:
        root.destroy()

    return selected or None