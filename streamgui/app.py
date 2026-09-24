import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass
import os, platform, shutil, subprocess

from streamgui.probe import probe_streams

_KDIALOG: str | None = shutil.which("kdialog")
_ZENITY: str | None = shutil.which("zenity")

_MEDIA_FILTER_KD = (
    "*.mkv *.mp4 *.m4v *.avi *.mov *.ts *.m2ts *.mts *.webm *.wmv *.flv "
    "*.mp3 *.aac *.flac *.ogg *.wav *.m4a *.opus *.ac3 *.dts "
    "*.srt *.ass *.ssa *.sub *.sup|Media files\n"
    "*.mkv *.mp4 *.m4v *.avi *.mov *.ts *.m2ts *.mts *.webm *.wmv *.flv|Video\n"
    "*.mp3 *.aac *.flac *.ogg *.wav *.m4a *.opus *.ac3 *.dts|Audio\n"
    "*.srt *.ass *.ssa *.sub *.sup|Subtitles\n"
    "*|All files"
)

_MEDIA_FILETYPES_TK: list[tuple[str, str]] = [
    ("Media files", "*.mkv *.mp4 *.m4v *.avi *.mov *.ts *.m2ts *.mts *.webm *.wmv *.flv "
                    "*.mp3 *.aac *.flac *.ogg *.wav *.m4a *.opus *.ac3 *.dts "
                    "*.srt *.ass *.ssa *.sub *.sup"),
    ("Video",       "*.mkv *.mp4 *.m4v *.avi *.mov *.ts *.m2ts *.mts *.webm *.wmv *.flv"),
    ("Audio",       "*.mp3 *.aac *.flac *.ogg *.wav *.m4a *.opus *.ac3 *.dts"),
    ("Subtitles",   "*.srt *.ass *.ssa *.sub *.sup"),
    ("All files",   "*"),
]

_CONTAINER_IID: str = "container"
_STREAM_DETAIL_LABELS: tuple[str, ...] = ("File", "Index", "Type", "Codec", "Duration")
_CONTAINER_DETAIL_LABELS: tuple[str, ...] = ("Output", "Inputs", "Format", "Streams", "Duration")


@dataclass
class StreamEntry:
    """Main stream class
    """
    path: str
    stream: dict
    fmt: dict
    checked: bool = True
    offset: str = "0.0"
    # NOTE: None means "unedited, keep the source tag"; "" is a deliberate blank that
    # must still be emitted when the source tag is populated.
    title: str | None = None
    lang: str | None = None
    input_idx: int | None = None


def _fmt_duration(seconds: str | None) -> str:
    """Format a duration in fractional seconds as H:MM:SS or M:SS.

    Args:
        seconds: Duration in fractional seconds as a string, or None (str | None).

    Returns:
        A formatted duration string like '1:23:45' or '23:45', or '' if None (str).
    """
    if not seconds:
        return ""
    s = float(seconds)
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02}:{sec:02}" if h else f"{m}:{sec:02}"


def stream_label(stream: dict, input_idx: int | None = None) -> str:
    """Return the treeview label for a stream: '{input_idx}:{stream_idx} {title_or_codec}'.

    When input_idx is None (stream's file is not in the ffmpeg command), the prefix is '–'.

    Args:
        stream: Raw ffprobe stream dict (dict).
        input_idx: 0-based ffmpeg -i index, or None if the stream's file is excluded (int | None).

    Returns:
        A formatted label string for display in the treeview (str).
    """
    stream_idx = stream.get("index", "?")
    description = stream.get("tags", {}).get("title") or stream.get("codec_type", "")
    return (f"{str(input_idx) if input_idx is not None else '–'}:"
        f"{stream_idx} {description}")


def compute_input_map(included: list[StreamEntry]) -> dict[tuple[str, str], int]:
    """Map each unique (path, offset) pair in `included` to its 0-based ffmpeg -i index.

    Insertion order determines index assignment, matching the order streams appear in
    the treeview. Only checked entries should be passed; unchecked entries are not inputs.

    Args:
        included: Checked StreamEntry objects in display order (list[StreamEntry]).

    Returns:
        A dict mapping (path, offset) pairs to their 0-based ffmpeg input index
        (dict[tuple[str, str], int]).
    """
    seen: dict[tuple[str, str], int] = {}
    for entry in included:
        key = (entry.path, entry.offset.strip())
        if key not in seen:
            seen[key] = len(seen)
    return seen

def get_line_continuation() -> str:
    """Return the appropriate line-continuation character based on what the OS can handle

    Returns:
        The appropriate separate a multi-part command (str)
    """
    os_name = platform.system()
    if os_name.lower() == 'windows':
        return " "
    return " \\\n    "

def build_command(included: list[StreamEntry], quick_test: bool,
                  output_title: str, overwrite: bool,
                  container_title: str | None = None,
                  container_lang: str | None = None) -> str:
    """Build the ffmpeg shell command string for the given checked stream entries.

    Args:
        included: Checked StreamEntry objects in display order (list[StreamEntry]).
        quick_test: If True, appends -to 15:00 to limit output to 15 minutes (bool).
        output_title: Base name for the output file, without extension (str).
        overwrite: If True, prepends -y to overwrite the output file without prompting (bool).
        container_title: Global title metadata for the output file, '' to blank it, or
            None to keep the first input's (str | None).
        container_lang: Global language metadata for the output file, '' to blank it, or
            None to keep the first input's (str | None).

    Returns:
        The full command as a backslash-continued multi-line string, or '' if included
        is empty (str).
    """
    if not included:
        return ""

    seen = compute_input_map(included)
    inputs = list(seen.keys())

    parts = ["ffmpeg"]
    for path, offset in inputs:
        o = offset.strip()
        if o and o not in ("0", "0.0"):
            parts.append(f"-itsoffset {o}")
        parts.append(f'-i "{os.path.normpath(path)}"')

    maps = ""
    for entry in included:
        key = (entry.path, entry.offset.strip())
        maps += f" -map {seen[key]}:{entry.stream.get('index', 0)}"
    parts.append(maps)
    parts.append("-c copy")

    for out_idx, entry in enumerate(included):
        tags = entry.stream.get("tags", {})
        if entry.title is not None and entry.title != tags.get("title", ""):
            parts.append(f'-metadata:s:{out_idx} title="{entry.title}"')
        if entry.lang is not None and entry.lang != tags.get("language", ""):
            parts.append(f'-metadata:s:{out_idx} language="{entry.lang}"')

    # NOTE: ffmpeg copies global metadata from input 0 by default, so container
    # tags are only emitted when they differ from the first input's format tags.
    fmt_tags = included[0].fmt.get("tags", {})
    if container_title is not None and container_title != fmt_tags.get("title", ""):
        parts.append(f'-metadata title="{container_title}"')
    if container_lang is not None and container_lang != fmt_tags.get("language", ""):
        parts.append(f'-metadata language="{container_lang}"')

    if quick_test:
        parts.append("-to 15:00")
    name = output_title.strip() or "output.mkv"
    if overwrite:
        parts.append("-y")
    parts.append(f'"{name}"')

    return get_line_continuation().join(parts)


class _SashLock:
    """Blocks drag on sash N of a vertical PanedWindow and keeps it pinned
    at `fixed_height` pixels below the sash
    """

    def __init__(self, paned: tk.PanedWindow, locked_sash: int, fixed_height: int) -> None:
        """Attach drag-blocking bindings to a PanedWindow sash.

        Args:
            paned: The PanedWindow widget to lock (tk.PanedWindow).
            locked_sash: 0-based index of the sash to pin (int).
            fixed_height: Pixel height to hold the pane at below the previous sash (int).
        """
        self._paned = paned
        self._locked = locked_sash
        self._height = fixed_height
        paned.bind("<Button-1>", self._on_press)
        paned.bind("<B1-Motion>", lambda e: paned.after_idle(self._enforce))
        paned.bind("<ButtonRelease-1>", lambda e: paned.after_idle(self._enforce))

    def _on_press(self, event: tk.Event) -> str | None:
        """Intercept mouse presses on the locked sash and suppress drag.

        Args:
            event: The Tkinter button-press event (tk.Event).

        Returns:
            'break' to cancel the event if the locked sash was clicked, else None (str | None).
        """
        try:
            _, sy = self._paned.sash_coord(self._locked)
            sash_w = self._paned.cget("sashwidth")
            if sy <= event.y <= sy + sash_w:
                return "break"
        except tk.TclError:
            pass

    def _enforce(self, _event: tk.Event | None = None) -> None:
        """Reposition the locked sash to its pinned height after any drag.

        Args:
            _event: Unused event argument passed by the after_idle callback (tk.Event | None).
        """
        try:
            _, s_prev_y = self._paned.sash_coord(self._locked - 1)
            s_cur_x, _ = self._paned.sash_coord(self._locked)
            sash_w = self._paned.cget("sashwidth")
            self._paned.sash_place(self._locked, s_cur_x, s_prev_y + sash_w + self._height)
        except tk.TclError:
            pass


class App(tk.Tk):
    def __init__(self) -> None:
        """Initialize the main application window and build all UI panels."""
        super().__init__()
        self.title("ffmpeg Stream Mapper")
        self.geometry("1000x800")

        self._last_dir: str = os.path.expanduser("~")
        self._loaded_paths: set[str] = set()
        self._stream_items: dict[str, StreamEntry] = {}
        self._current_item: str | None = None
        self._drag_item: str | None = None
        self._drag_hover: str | None = None
        self._quickTest = tk.BooleanVar()
        self._quickTest.set(True)
        self._outputTitle = tk.StringVar()
        self._outputTitle.set("output.mkv")
        self._outputOverwrite = tk.BooleanVar()
        self._outputOverwrite.set(True)
        # NOTE: None means "follow the first input's format tags"; '' blanks them
        self._containerTitle: str | None = None
        self._containerLang: str | None = None

        self._create_toolbar()
        self._create_main_pane()

    def _create_toolbar(self) -> None:
        """Build and pack the top toolbar with Open, Clear, and Reset buttons."""
        toolbar = tk.Frame(self, bd=1)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(toolbar, text="Open File", command=self._open_file).pack(side=tk.LEFT, padx=1, pady=1)
        tk.Button(toolbar, text="Clear All", command=self._clear_all).pack(side=tk.LEFT, padx=3, pady=1)
        tk.Button(toolbar, text="Reset Offsets", command=self._reset_offsets).pack(side=tk.LEFT, padx=3, pady=1)

    def _create_main_pane(self) -> None:
        """Build the outer PanedWindow containing the stream panes, command bar, and output text."""
        self._outer = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        self._outer.pack(fill=tk.BOTH, expand=True)

        top = tk.PanedWindow(self._outer, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self._outer.add(top, minsize=320)
        self._create_left_pane(top)
        self._create_right_pane(top)

        self._create_middle_panel(self._outer)

        self._create_bottom_pane(self._outer)

        _SashLock(self._outer, locked_sash=1, fixed_height=35)

    def _create_left_pane(self, parent: tk.PanedWindow) -> None:
        """Build the stream treeview panel and add it to parent.

        Args:
            parent: The PanedWindow to add this pane to (tk.PanedWindow).
        """
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=350)

        tk.Label(frame, text="Streams", font=("", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 0))

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        self._treeview = ttk.Treeview(frame, yscrollcommand=scrollbar.set, selectmode="browse", show="tree")
        scrollbar.config(command=self._treeview.yview)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._treeview.tag_configure("drop_target", background="lightblue")
        self._treeview.tag_configure("excluded", foreground="gray", font=("TkDefaultFont", 9, "overstrike"))
        self._treeview.insert("", tk.END, iid=_CONTAINER_IID, text="Container", open=True)
        self._treeview.bind("<<TreeviewSelect>>", self._on_select)
        # self._treeview.bind("<KeyPress-Delete>", self._on_delete)
            # NOTE: Commented out for now, as there is no simple way to re-add a stream deleted inadvertently
            #  The `Include` checkbox works just as well
        self._treeview.bind("<Button-1>", self._on_drag_start)
        self._treeview.bind("<B1-Motion>", self._on_drag_motion)
        self._treeview.bind("<ButtonRelease-1>", self._on_drag_release)

    def _create_right_pane(self, parent: tk.PanedWindow) -> None:
        """Build the stream detail and edit panel and add it to parent.

        Args:
            parent: The PanedWindow to add this pane to (tk.PanedWindow).
        """
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=500)

        tk.Label(frame, text="Stream Details", font=("", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 4))

        self._vars: dict[str, tk.StringVar] = {}
        # NOTE: row captions are swapped to _CONTAINER_DETAIL_LABELS when the Container
        # node is selected; self._vars stays keyed by the stream captions.
        self._detail_labels: dict[str, tk.Label] = {}
        for label in ("File", "Index", "Type", "Codec"):
            self._vars[label] = tk.StringVar()
            row = tk.Frame(frame)
            row.pack(fill=tk.X, padx=5, pady=1)
            self._detail_labels[label] = tk.Label(row, text=f"{label}:", width=10, anchor=tk.W)
            self._detail_labels[label].pack(side=tk.LEFT)
            tk.Label(row, textvariable=self._vars[label], anchor=tk.W, wraplength=600, justify=tk.LEFT).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        self._vars["Duration"] = tk.StringVar()
        row = tk.Frame(frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        self._detail_labels["Duration"] = tk.Label(row, text="Duration:", width=10, anchor=tk.W)
        self._detail_labels["Duration"].pack(side=tk.LEFT)
        tk.Label(row, textvariable=self._vars["Duration"], anchor=tk.W).pack(side=tk.LEFT)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=(8, 4))
        self._edit_fields: dict[str, tuple[tk.Variable, tk.Widget]] = {}

        check_var = tk.BooleanVar()
        checkbox = tk.Checkbutton(
            frame, text="Include stream", variable=check_var, command=self._on_check, state=tk.DISABLED
        )
        checkbox.pack(anchor=tk.W, padx=8)
        self._edit_fields["check"] = (check_var, checkbox)

        row = tk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text="Language:", width=10, anchor=tk.W).pack(side=tk.LEFT)
        lang_var = tk.StringVar()
        lang_entry = tk.Entry(row, width=3, textvariable=lang_var, state=tk.DISABLED)
        lang_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._edit_fields["lang"] = (lang_var, lang_entry)

        row = tk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text="Title:", width=10, anchor=tk.W).pack(side=tk.LEFT)
        title_var = tk.StringVar()
        title_entry = tk.Entry(row, textvariable=title_var, state=tk.DISABLED)
        title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._edit_fields["title"] = (title_var, title_entry)

        row = tk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text="Offset:", width=10, anchor=tk.W).pack(side=tk.LEFT)
        offset_var = tk.StringVar()
        offset_entry = tk.Entry(row, textvariable=offset_var, state=tk.DISABLED, width=12)
        offset_entry.pack(side=tk.LEFT)
        self._edit_fields["offset"] = (offset_var, offset_entry)

        lang_var.trace_add("write", self._on_lang_write)
        title_var.trace_add("write", self._on_title_write)
        offset_var.trace_add("write", self._on_offset_write)

    def _create_middle_panel(self, parent: tk.PanedWindow) -> None:
        """Build the command bar with Copy button, quick-test checkbox, and output options.

        Args:
            parent: The PanedWindow to add this panel to (tk.PanedWindow).
        """
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=35)

        row = tk.Frame(frame)
        row.pack(fill=tk.X, padx=4, pady=(4, 0))
        tk.Button(row, text="Copy", command=self._copy_command).pack(side=tk.LEFT, padx=4)
        tk.Label(row, text="FFmpeg Command", font=("", 10, "bold")).pack(side=tk.LEFT)
        tk.Checkbutton(
            row, text="Fifteen-minute test", variable=self._quickTest, command=self._update_command).pack(side=tk.LEFT, padx=25)
        tk.Checkbutton(
            row, text="Overwrite?", variable=self._outputOverwrite,
            command=self._update_command).pack(side=tk.RIGHT, padx=25)
        outputName = tk.Entry(row, textvariable=self._outputTitle, width=30, )
        outputName.pack(side=tk.RIGHT)
        tk.Label(row, text="Output Title:").pack(side=tk.RIGHT, padx=2)
        self._outputTitle.trace_add("write", self._update_command)

    def _create_bottom_pane(self, parent: tk.PanedWindow) -> None:
        """Build the scrollable command text output pane and add it to parent.

        Args:
            parent: The PanedWindow to add this pane to (tk.PanedWindow).
        """
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=60)

        scroll_x = tk.Scrollbar(frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame, orient=tk.VERTICAL)
        self._cmd_text = tk.Text(
            frame,
            state=tk.DISABLED,
            wrap=tk.NONE,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )
        scroll_y.config(command=self._cmd_text.yview)
        scroll_x.config(command=self._cmd_text.xview)

        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._cmd_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

    def _pick_files(self) -> tuple[str, ...]:
        """Open a native file chooser and return selected paths.

        Prefers kdialog (KDE) or zenity (GNOME/GTK) via subprocess when available;
        falls back to tkinter's filedialog on other desktops or platforms.

        Returns:
            A tuple of absolute file paths, or an empty tuple if cancelled
            (tuple[str, ...]).
        """
        if _KDIALOG:
            result = subprocess.run(
                [_KDIALOG, "--title", "Select Media Files",
                 "--getopenfilename", self._last_dir, _MEDIA_FILTER_KD,
                 "--multiple", "--separate-output"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                return ()
            return tuple(p for p in result.stdout.strip().split("\n") if p)

        if _ZENITY:
            result = subprocess.run(
                [_ZENITY, "--file-selection", "--multiple",
                 "--title=Select Media Files",
                 f"--filename={self._last_dir}/",
                 "--separator=\n",
                 "--file-filter=Media files | *.mkv *.mp4 *.m4v *.avi *.mov *.ts "
                 "*.m2ts *.mts *.webm *.wmv *.flv *.mp3 *.aac *.flac *.ogg *.wav "
                 "*.m4a *.opus *.ac3 *.dts *.srt *.ass *.ssa *.sub *.sup",
                 "--file-filter=All files | *"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                return ()
            return tuple(p for p in result.stdout.strip().split("\n") if p)

        return filedialog.askopenfilenames(
            title="Select Media Files",
            initialdir=self._last_dir,
            filetypes=_MEDIA_FILETYPES_TK,
        )

    def _open_file(self) -> None:
        """Open a file dialog, probe selected files, and add their streams to the treeview."""
        paths = self._pick_files()
        if not paths:
            return
        self._last_dir = os.path.dirname(paths[0])
        for path in paths:
            if path in self._loaded_paths:
                continue
            try:
                streams, fmt = probe_streams(path)
            except Exception as exc:
                messagebox.showerror("Probe failed", str(exc))
                continue
            self._loaded_paths.add(path)
            name = os.path.basename(path)
            file_item = self._treeview.insert(_CONTAINER_IID, tk.END, text=name, open=True)
            for stream in streams:
                item_id = self._treeview.insert(file_item, tk.END, text=stream_label(stream))
                self._stream_items[item_id] = StreamEntry(path=path, stream=stream, fmt=fmt)
        self._refresh()

    def _on_delete(self, event: tk.Event) -> None:
        """Remove the selected stream from the treeview and clean up its file node if empty.

        Args:
            event: The Tkinter key-press event that triggered deletion (tk.Event).
        """
        sel = self._treeview.selection()
        if not sel or sel[0] not in self._stream_items:
            return
        item_id = sel[0]
        parent_node = self._treeview.parent(item_id)
        entry = self._stream_items.pop(item_id)
        if not any(e.path == entry.path for e in self._stream_items.values()):
            self._loaded_paths.discard(entry.path)
        self._treeview.delete(item_id)
        if parent_node and not self._treeview.get_children(parent_node):
            self._treeview.delete(parent_node)
        if item_id == self._current_item:
            self._clear_info()
        self._refresh()

    def _clear_info(self) -> None:
        """Reset the detail panel to its empty, disabled state."""
        # NOTE: must come first — guards trace callbacks that check self._current_item
        self._current_item = None
        self._set_detail_labels(_STREAM_DETAIL_LABELS)
        for var in self._vars.values():
            var.set("")
        for var, widget in self._edit_fields.values():
            var.set(False if isinstance(var, tk.BooleanVar) else "")
            widget.config(state=tk.DISABLED)

    def _on_offset_write(self, *_: object) -> None:
        """Write the edited offset value back to the current stream entry and refresh.

        Args:
            *_: Tkinter trace callback arguments (ignored) (object).
        """
        if self._current_item in self._stream_items:
            self._stream_items[self._current_item].offset = self._edit_fields["offset"][0].get()
            self._refresh()
            self._load_stream_vars(self._stream_items[self._current_item])

    def _on_title_write(self, *_: object) -> None:
        """Write the edited title value back to the current stream or Container and update the command.

        Args:
            *_: Tkinter trace callback arguments (ignored) (object).
        """
        if self._current_item == _CONTAINER_IID:
            self._containerTitle = self._edit_fields["title"][0].get()
            self._update_command()
        elif self._current_item is not None:
            self._stream_items[self._current_item].title = self._edit_fields["title"][0].get()
            self._update_command()

    def _on_lang_write(self, *_: object) -> None:
        """Write the edited language value back to the current stream or Container and update the command.

        Args:
            *_: Tkinter trace callback arguments (ignored) (object).
        """
        if self._current_item == _CONTAINER_IID:
            self._containerLang = self._edit_fields["lang"][0].get()
            self._update_command()
        elif self._current_item is not None:
            self._stream_items[self._current_item].lang = self._edit_fields["lang"][0].get()
            self._update_command()

    def _set_detail_labels(self, captions: tuple[str, ...]) -> None:
        """Relabel the read-only detail rows, in _STREAM_DETAIL_LABELS order.

        Args:
            captions: One caption per detail row (tuple[str, ...]).
        """
        for key, caption in zip(_STREAM_DETAIL_LABELS, captions):
            self._detail_labels[key].config(text=f"{caption}:")

    def _container_tags(self) -> dict:
        """Return the format tags of the first included input, which ffmpeg copies by default.

        Returns:
            The first included entry's ffprobe format tags, or {} if none are included (dict).
        """
        included = self._get_included()
        return included[0].fmt.get("tags", {}) if included else {}

    def _load_container_vars(self) -> None:
        """Populate the read-only detail fields with a summary of the output container."""
        included = self._get_included()
        fmt = included[0].fmt if included else {}
        name = self._outputTitle.get().strip() or "output.mkv"
        self._set_detail_labels(_CONTAINER_DETAIL_LABELS)
        self._vars["File"].set(name)
        self._vars["Index"].set(f"{len(compute_input_map(included)):d}")
        self._vars["Type"].set(os.path.splitext(name)[1].lstrip(".").upper())
        self._vars["Codec"].set(f"{len(included):d}")
        self._vars["Duration"].set(_fmt_duration(fmt.get("duration")))

    def _load_stream_vars(self, entry: StreamEntry) -> None:
        """Populate the read-only detail fields from a StreamEntry.

        Args:
            entry: The StreamEntry whose metadata should be displayed (StreamEntry).
        """
        stream, fmt = entry.stream, entry.fmt
        duration = stream.get("duration") or fmt.get("duration")
        self._set_detail_labels(_STREAM_DETAIL_LABELS)
        self._vars["File"].set(entry.path)
        self._vars["Index"].set(f"{entry.input_idx} : {stream.get('index', '')}")
        self._vars["Type"].set(stream.get("codec_type", ""))
        self._vars["Codec"].set(stream.get("codec_name", ""))
        self._vars["Duration"].set(_fmt_duration(duration))

    def _on_select(self, _event: tk.Event) -> None:
        """Populate the detail panel when a stream item is selected in the treeview.

        Args:
            _event: The Tkinter treeview selection event (unused) (tk.Event).
        """
        sel = self._treeview.selection()
        if sel and sel[0] == _CONTAINER_IID:
            self._select_container()
            return
        if not sel or sel[0] not in self._stream_items:
            self._clear_info()
            return

        item_id = sel[0]
        # NOTE: set before loading vars so traces write to the right entry
        self._current_item = item_id
        entry = self._stream_items[item_id]
        tags = entry.stream.get("tags", {})

        self._load_stream_vars(entry)

        self._edit_fields["lang"][0].set(
            entry.lang if entry.lang is not None else tags.get("language", ""))
        self._edit_fields["title"][0].set(
            entry.title if entry.title is not None else tags.get("title", ""))
        self._edit_fields["offset"][0].set(entry.offset)
        self._edit_fields["check"][0].set(entry.checked)
        for _, widget in self._edit_fields.values():
            widget.config(state=tk.NORMAL)

    def _select_container(self) -> None:
        """Populate the detail panel for the Container node, enabling only Language and Title."""
        # NOTE: clear first so the traces fired while prefilling neither write into the
        # previously selected stream nor pin the Container to the current defaults.
        self._current_item = None
        tags = self._container_tags()
        self._load_container_vars()
        self._edit_fields["lang"][0].set(
            self._containerLang if self._containerLang is not None
            else tags.get("language", ""))
        self._edit_fields["title"][0].set(
            self._containerTitle if self._containerTitle is not None
            else tags.get("title", ""))
        self._edit_fields["offset"][0].set("")
        self._edit_fields["check"][0].set(False)
        for key, (_, widget) in self._edit_fields.items():
            widget.config(state=tk.NORMAL if key in ("lang", "title") else tk.DISABLED)
        self._current_item = _CONTAINER_IID

    def _on_check(self) -> None:
        """Toggle the checked state of the current stream entry and refresh the display."""
        if self._current_item in self._stream_items:
            included = self._edit_fields["check"][0].get()
            self._stream_items[self._current_item].checked = included
            tag = () if included else ("excluded",)
            self._treeview.item(self._current_item, tags=tag)
        self._refresh()

    def _on_drag_start(self, event: tk.Event) -> None:
        """Record the dragged stream item on mouse button press.

        Args:
            event: The Tkinter button-press event containing the click position (tk.Event).
        """
        item = self._treeview.identify_row(event.y)
        self._drag_item = item if (item and item in self._stream_items) else None
        self._drag_hover = None

    def _on_drag_motion(self, event: tk.Event) -> None:
        """Highlight the drop target as the dragged stream is moved over the treeview.

        Args:
            event: The Tkinter mouse-motion event containing the current position (tk.Event).
        """
        if self._drag_item is None:
            return
        target = self._treeview.identify_row(event.y)
        if target == self._drag_hover:
            return
        if self._drag_hover:
            self._restore_tag(self._drag_hover)
        self._drag_hover = target if (target and target != self._drag_item) else None
        if self._drag_hover:
            self._treeview.item(self._drag_hover, tags=("drop_target",))

    def _on_drag_release(self, event: tk.Event) -> None:
        """Complete the drag operation and reorder the stream to its drop position.

        Args:
            event: The Tkinter button-release event containing the drop position (tk.Event).
        """
        src_id = self._drag_item
        if src_id is None:
            return
        if self._drag_hover:
            self._restore_tag(self._drag_hover)
        self._drag_item = None
        self._drag_hover = None
        # NOTE: empty space and the Container node both mean "move to the end"; the
        # Container is always the first row, so nothing can be dropped above it.
        target = self._treeview.identify_row(event.y) or None
        if target == _CONTAINER_IID:
            target = None
        if target != src_id:
            self._reorder_stream(src_id, target)

    def _reorder_stream(self, src_id: str, dst_id: str | None) -> None:
        """Move a stream from its current position to the position of dst_id.

        Args:
            src_id: Treeview item ID of the stream being moved (str).
            dst_id: Treeview item ID of the drop target, or None to move to end (str | None).
        """
        ordered = self._get_ordered_ids()
        src_pos = ordered.index(src_id)

        if dst_id is None:
            dst_pos = len(ordered)
        elif dst_id in self._stream_items:
            dst_pos = ordered.index(dst_id)
        else:
            # NOTE: dropped on a file node — insert after its last stream child
            children = list(self._treeview.get_children(dst_id))
            dst_pos = ordered.index(children[-1]) + 1 if children else len(ordered)

        if src_pos == dst_pos:
            return
        ordered.pop(src_pos)
        if src_pos < dst_pos:
            dst_pos -= 1
        ordered.insert(dst_pos, src_id)
        self._rebuild_tree(ordered)
        self._refresh()

    def _rebuild_tree(self, ordered_ids: list[str]) -> None:
        """Reconstruct the treeview from scratch using the given ordered stream IDs.

        Args:
            ordered_ids: Stream item IDs in the desired display order (list[str]).
        """
        sel = self._treeview.selection()
        for item in self._treeview.get_children(_CONTAINER_IID):
            self._treeview.delete(item)
        prev_path = None
        file_node: str | None = None
        for item_id in ordered_ids:
            entry = self._stream_items[item_id]
            path, stream = entry.path, entry.stream
            if path != prev_path:
                file_node = self._treeview.insert(_CONTAINER_IID, tk.END, text=os.path.basename(path), open=True)
                prev_path = path
            self._treeview.insert(file_node, tk.END, text=stream_label(stream, entry.input_idx), iid=item_id)
        if sel and sel[0] in self._stream_items:
            self._treeview.selection_set(sel[0])
            self._treeview.see(sel[0])

    def _get_ordered_ids(self) -> list[str]:
        """Return stream item IDs in their current treeview display order.

        Returns:
            A flat list of stream item IDs ordered as they appear in the treeview (list[str]).
        """
        return [iid for file_item in self._treeview.get_children(_CONTAINER_IID)
                for iid in self._treeview.get_children(file_item)]

    def _get_included(self) -> list[StreamEntry]:
        """Return the checked stream entries in their current treeview display order.

        Returns:
            Checked StreamEntry objects in display order (list[StreamEntry]).
        """
        return [self._stream_items[iid] for iid in self._get_ordered_ids()
                if self._stream_items[iid].checked]

    def _restore_tag(self, iid: str) -> None:
        """Set an item's tags from its checked state, dropping any transient tag.

        No-ops for file container nodes, which have no checked state of their own.

        Args:
            iid: Treeview item ID of the item to restore (str).
        """
        entry = self._stream_items.get(iid)
        self._treeview.item(iid, tags=() if entry is None or entry.checked else ("excluded",))

    def _refresh_tags(self) -> None:
        """Reapply the 'excluded' tag to every stream item based on its checked state.

        # NOTE: Several operations (drag reorder rebuild, drop-target highlight
        # clearing) overwrite an item's tags wholesale, silently dropping the
        # 'excluded' strikethrough tag. Call this after any such operation.
        """
        for iid in self._get_ordered_ids():
            self._restore_tag(iid)

    def _refresh_stream_labels(self) -> None:
        """Update the treeview label text for every stream item using the current input indices."""
        for iid in self._get_ordered_ids():
            entry = self._stream_items[iid]
            self._treeview.item(iid, text=stream_label(entry.stream, entry.input_idx))

    def _refresh_state(self) -> None:
        """Recompute input_idx for all entries and refresh treeview labels."""
        ordered = self._get_ordered_ids()
        included = [self._stream_items[iid] for iid in ordered if self._stream_items[iid].checked]
        seen = compute_input_map(included)
        for iid in ordered:
            entry = self._stream_items[iid]
            entry.input_idx = seen.get((entry.path, entry.offset.strip()))
        self._refresh_stream_labels()

    def _update_command(self, *_: object) -> None:
        """Rebuild the ffmpeg command text widget.

        Args:
            *_: Optional Tkinter trace callback arguments (ignored) (object).
        """
        cmd = build_command(
            self._get_included(), self._quickTest.get(),
            self._outputTitle.get(), self._outputOverwrite.get(),
            self._containerTitle, self._containerLang
        )
        self._cmd_text.config(state=tk.NORMAL)
        self._cmd_text.delete("1.0", tk.END)
        if cmd:
            self._cmd_text.insert("1.0", cmd)
        self._cmd_text.config(state=tk.DISABLED)
        if self._current_item == _CONTAINER_IID:
            self._load_container_vars()

    def _refresh(self) -> None:
        """Recalculate variables and rebuild the command output."""
        self._refresh_state()
        self._refresh_tags()
        self._update_command()

    def _copy_command(self) -> None:
        """Copy the current command text to the system clipboard."""
        cmd = self._cmd_text.get("1.0", tk.END).strip()
        if cmd:
            self.clipboard_clear()
            self.clipboard_append(cmd)

    def _clear_all(self) -> None:
        """Reset the application to its initial empty state."""
        # NOTE: delete rows first — resetting _outputTitle fires a trace that walks the tree
        for item in self._treeview.get_children(_CONTAINER_IID):
            self._treeview.delete(item)
        self._loaded_paths.clear()
        self._stream_items.clear()
        self._drag_item = None
        self._drag_hover = None
        self._quickTest.set(True)
        self._outputTitle.set("output.mkv")
        self._outputOverwrite.set(True)
        self._containerTitle = None
        self._containerLang = None
        self._clear_info()
        self._update_command()

    def _reset_offsets(self) -> None:
        """Reset all stream offsets to 0.0 and refresh the display."""
        for entry in self._stream_items.values():
            entry.offset = "0.0"
        if self._current_item in self._stream_items:
            self._edit_fields["offset"][0].set("0.0")
        self._refresh()
