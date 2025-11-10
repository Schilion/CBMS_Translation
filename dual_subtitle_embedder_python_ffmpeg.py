#!/usr/bin/env python3
"""
Dual-Subtitle Embedder (English above Vietnamese, both near bottom)
- Drag & drop GUI using tkinter + tkinterdnd2
- Burns two SRT subtitle files into a single MP4 output via FFmpeg
- Compression modes: Normal / Smaller / Smallest (+ optional 720p downscale)
"""

import os
import platform
import shutil
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
    TkBase = TkinterDnD.Tk
except Exception:
    DND_AVAILABLE = False
    TkBase = tk.Tk

APP_TITLE = "Dual-Subtitle Embedder (EN ↑ over VI)"

# ======= Subtitle style (tweak here) =======
DEFAULT_FONT = "Arial"
DEFAULT_FONTSIZE = 26
DEFAULT_OUTLINE = 2
DEFAULT_SHADOW = 1
# Default margins (pixels from bottom). Smaller = closer to the bottom border.
EN_MARGIN_V = 60   # English just above Vietnamese
VI_MARGIN_V = 24   # Vietnamese very near bottom

# ======= Helpers =======
VID_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".m4v"}


def ffmpeg_path_guess() -> str:
    """Find ffmpeg on PATH, or common Windows location."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    if platform.system() == "Windows":
        win_candidate = Path("C:/ffmpeg/bin/ffmpeg.exe")
        if win_candidate.exists():
            return str(win_candidate)
    raise FileNotFoundError("FFmpeg executable not found. Install it or add to PATH.")


def ffmpeg_escape_for_subtitles(path: str) -> str:
    p = path.replace("\\", "\\\\").replace(":", r"\:")
    p = p.replace("'", r"\'")
    return f"'{p}'"


def build_filter_complex(en_srt: str, vi_srt: str, downscale_720: bool, font_size: int, en_margin: int, vi_margin: int) -> str:
    style_common = f"FontName={DEFAULT_FONT},Fontsize={font_size},Outline={DEFAULT_OUTLINE},Shadow={DEFAULT_SHADOW}"
    en = ffmpeg_escape_for_subtitles(en_srt)
    vi = ffmpeg_escape_for_subtitles(vi_srt)

    p1 = (
        f"[0:v]subtitles={en}:charenc=UTF-8:force_style='Alignment=2,MarginV={en_margin},{style_common}'[v1]"
    )
    p2 = (
        f"[v1]subtitles={vi}:charenc=UTF-8:force_style='Alignment=2,MarginV={vi_margin},{style_common}'[v2]"
    )

    # Optional scale to 720p height preserving aspect (for size reduction)
    p3 = "[v2]scale=-2:720[vout]" if downscale_720 else "[v2]copy[vout]"  # copy is a no-op passthrough label
    # Build; if copy, just relabel via format filter to keep a legal chain
    if downscale_720:
        chain = f"{p1};{p2};{p3}"
    else:
        # replace copy with a trivial format to create vout
        chain = f"{p1};{p2};[v2]format=yuv420p[vout]"
    return chain


def build_encode_args(mode: str):
    """Return (video_codec_args, audio_codec_args) for a given compression mode."""
    mode = mode.lower()
    if mode == "smallest":
        return ["-c:v", "libx265", "-preset", "medium", "-crf", "28"], ["-c:a", "aac", "-b:a", "128k"]
    if mode == "smaller":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "24"], ["-c:a", "aac", "-b:a", "160k"]
    # normal
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "18"], ["-c:a", "aac", "-b:a", "192k"]


def run_ffmpeg(video: str, en_srt: str, vi_srt: str, out_path: str, mode: str, downscale_720: bool, font_size: int, en_margin: int, vi_margin: int, progress_cb=None) -> int:
    ffmpeg = ffmpeg_path_guess()
    filter_complex = build_filter_complex(en_srt, vi_srt, downscale_720, font_size, en_margin, vi_margin)
    v_args, a_args = build_encode_args(mode)

    cmd = [
        ffmpeg,
        "-y",
        "-i", video,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "0:a?",
        *v_args,
        *a_args,
        "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, bufsize=1)
    if progress_cb and proc.stderr is not None:
        for line in proc.stderr:
            if "time=" in line:
                try:
                    t = line.split("time=")[1].split()[0]
                    progress_cb(t)
                except Exception:
                    pass
    return proc.wait()


# ======= GUI =======
class App(TkBase):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x600")
        self.minsize(760, 560)

        self.video_path = tk.StringVar()
        self.en_srt_path = tk.StringVar()
        self.vi_srt_path = tk.StringVar()
        self.out_dir = tk.StringVar(value=str(Path.home()))
        self.status_text = tk.StringVar(value="Drop files or click Browse…")
        self.mode = tk.StringVar(value="Smaller")
        self.downscale = tk.BooleanVar(value=False)
        # UI-controlled subtitle parameters
        self.font_size_var = tk.IntVar(value=24)
        self.en_margin_var = tk.IntVar(value=60)
        self.vi_margin_var = tk.IntVar(value=24)

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # Drop zone (collective) — auto routes files
        if DND_AVAILABLE:
            dz = ttk.LabelFrame(main, text="Drag & Drop Zone (video + .srt files, or a folder for output)")
            dz.pack(fill=tk.X, pady=(0, 10))
            drop = ttk.Label(dz, text="Drop here: video + English/Vietnamese .srt (we auto-detect)\nDrop a folder to set the output directory.", anchor="center")
            drop.pack(fill=tk.X, padx=8, pady=8)
            drop.drop_target_register(DND_FILES)
            drop.dnd_bind("<<Drop>>", self._on_multi_drop)

        self._make_drop_row(main, "Video file", self.video_path, ("Video files", "*.mp4 *.mkv *.mov *.avi *.m4v"))
        self._make_drop_row(main, "English SRT (top, just above VI)", self.en_srt_path, ("SRT files", "*.srt"))
        self._make_drop_row(main, "Vietnamese SRT (bottom)", self.vi_srt_path, ("SRT files", "*.srt"))

        swap_row = ttk.Frame(main)
        swap_row.pack(fill=tk.X, pady=(4, 8))
        ttk.Button(swap_row, text="Swap EN ↔ VI", command=self._swap_srts).pack(side=tk.LEFT)

        out_row = ttk.Frame(main)
        out_row.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(out_row, text="Output folder").pack(anchor=tk.W)
        out_entry = ttk.Entry(out_row, textvariable=self.out_dir)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text="Browse…", command=self._choose_out_dir).pack(side=tk.LEFT, padx=6)
        if DND_AVAILABLE:
            out_entry.drop_target_register(DND_FILES)
            out_entry.dnd_bind("<<Drop>>", self._on_outdir_drop)

        # Compression settings
        opts = ttk.LabelFrame(main, text="Compression")
        opts.pack(fill=tk.X, pady=(8, 8))
        ttk.Label(opts, text="Mode:").pack(side=tk.LEFT, padx=(8, 6))
        mode_box = ttk.Combobox(opts, textvariable=self.mode, values=["Normal", "Smaller", "Smallest"], state="readonly", width=12)
        mode_box.pack(side=tk.LEFT)
        ttk.Checkbutton(opts, text="Downscale to 720p", variable=self.downscale).pack(side=tk.LEFT, padx=12)

        # Subtitle appearance
        subopts = ttk.LabelFrame(main, text="Subtitles Appearance")
        subopts.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(subopts, text="Font size:").pack(side=tk.LEFT, padx=(8, 6))
        tk.Spinbox(subopts, from_=14, to=64, textvariable=self.font_size_var, width=4).pack(side=tk.LEFT)
        ttk.Label(subopts, text="EN margin (px from bottom):").pack(side=tk.LEFT, padx=(12, 6))
        tk.Spinbox(subopts, from_=10, to=300, textvariable=self.en_margin_var, width=5).pack(side=tk.LEFT)
        ttk.Label(subopts, text="VI margin:").pack(side=tk.LEFT, padx=(12, 6))
        tk.Spinbox(subopts, from_=5, to=300, textvariable=self.vi_margin_var, width=5).pack(side=tk.LEFT)

        # Progress + Action
        action = ttk.Frame(main)
        action.pack(fill=tk.X, pady=(8, 4))
        self.progress = ttk.Progressbar(action, mode="indeterminate")
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        ttk.Button(action, text="Embed Subtitles", command=self._start).pack(side=tk.LEFT, padx=8)

        ttk.Label(main, textvariable=self.status_text, foreground="#444").pack(anchor=tk.W, pady=(6, 0))

    # ----- DnD helpers -----
    def _parse_dnd_list(self, data: str):
        items = []
        token = ''
        in_brace = False
        for ch in data:
            if ch == '{':
                in_brace = True
                token = ''
            elif ch == '}':
                in_brace = False
                items.append(token)
                token = ''
            elif ch == ' ' and not in_brace:
                if token:
                    items.append(token)
                    token = ''
            else:
                token += ch
        if token:
            items.append(token)
        return items

    def _on_multi_drop(self, event):
        paths = self._parse_dnd_list(event.data)
        for p in paths:
            p = p.strip()
            if not p:
                continue
            if os.path.isdir(p):
                self.out_dir.set(p)
                continue
            ext = Path(p).suffix.lower()
            if ext in VID_EXTS:
                self.video_path.set(p)
            elif ext == ".srt":
                # heuristic: if name hints VI, set to VI
                name = Path(p).name.lower()
                if any(k in name for k in ["vi", "viet", "vietnam"]):
                    self.vi_srt_path.set(p)
                elif not self.en_srt_path.get():
                    self.en_srt_path.set(p)
                else:
                    self.vi_srt_path.set(p)

    def _on_outdir_drop(self, event):
        paths = self._parse_dnd_list(event.data)
        if paths:
            p = paths[0]
            if os.path.isdir(p):
                self.out_dir.set(p)

    # ----- Standard pickers -----
    def _make_drop_row(self, parent, label, var, exts):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=6)
        ttk.Label(frame, text=label).pack(anchor=tk.W)
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame, text="Browse…", command=lambda: self._browse_file(var, exts)).pack(side=tk.LEFT, padx=6)
        if DND_AVAILABLE:
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind("<<Drop>>", lambda e, v=var: self._on_entry_drop(e, v))

    def _on_entry_drop(self, event, var):
        paths = self._parse_dnd_list(event.data)
        if paths:
            var.set(paths[0])

    def _browse_file(self, var, exts):
        fp = filedialog.askopenfilename(title="Select file", filetypes=[exts, ("All files", "*.*")])
        if fp:
            var.set(fp)

    def _choose_out_dir(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.out_dir.set(d)

    def _swap_srts(self):
        tmp = self.en_srt_path.get()
        self.en_srt_path.set(self.vi_srt_path.get())
        self.vi_srt_path.set(tmp)

    # ----- Run -----
    def _start(self):
        video = self.video_path.get().strip()
        en = self.en_srt_path.get().strip()
        vi = self.vi_srt_path.get().strip()
        out_dir = self.out_dir.get().strip()

        if not all(map(os.path.isfile, [video, en, vi])):
            messagebox.showerror("Missing file", "Please select a valid video and two SRT files.")
            return
        if not os.path.isdir(out_dir):
            messagebox.showerror("Missing folder", "Please choose a valid output folder.")
            return

        base = Path(video).stem
        out_path = str(Path(out_dir) / f"{base}_dual_subbed.mp4")

        self.status_text.set("Starting FFmpeg…")
        self.progress.start(12)
        threading.Thread(
            target=self._run_embed,
            args=(video, en, vi, out_path, self.mode.get(), self.downscale.get(), self.font_size_var.get(), self.en_margin_var.get(), self.vi_margin_var.get()),
            daemon=True,
        ).start()

    def _run_embed(self, video, en, vi, out_path, mode, downscale, font_size, en_margin, vi_margin):
        start = time.time()
        try:
            code = run_ffmpeg(video, en, vi, out_path, mode, downscale, font_size, en_margin, vi_margin, progress_cb=lambda ts: self.status_text.set(f"Encoding… time={ts}"))
        except Exception as e:
            self._finish(False, start, msg=str(e))
            return
        ok = (code == 0 and os.path.exists(out_path))
        self._finish(ok, start, out_path)

    def _finish(self, ok, start, out_path="", msg=""):
        self.progress.stop()
        if ok:
            dur = time.time() - start
            self.status_text.set(f"Done in {dur:.1f}s → {out_path}")
            messagebox.showinfo("Success", f"Created\n{out_path}")
        else:
            self.status_text.set(msg or "Failed.")
            messagebox.showerror("Error", msg or "Encoding failed.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
