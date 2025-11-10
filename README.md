# 🎬 Dual-Subtitle Embedder (English ↑ over Vietnamese ↓)

---

## 🧰 Features
- English above Vietnamese (both bottom-center)
- Drag & drop GUI using `tkinterdnd2`
- Compression modes: **Normal / Smaller / Smallest**
- Optional 720p downscale for smaller file sizes
- UTF-8 subtitle support
- Works on **Windows**, **Linux**, and **WSL (GUI)**

---

## 🪜 Installation

### 1️⃣ Requirements
- Python 3.8 or higher
- FFmpeg installed and available in PATH

### 2️⃣ Install Python dependencies
```bash
pip install tkinterdnd2
```

### 3️⃣ FFmpeg setup

#### 🪟 On Windows
1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract it to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH
4. Verify installation:
```bash
ffmpeg -version
```

#### 🐧 On Linux / WSL
```bash
sudo apt update
sudo apt install ffmpeg -y
ffmpeg -version
```

---

## 🚀 Usage

1. Place your script file (e.g., `dual_subtitle_embedder_python_ffmpeg.py`) and subtitles in the same directory.
2. Run the program:

**Windows:**
```bash
python dual_subtitle_embedder_python_ffmpeg.py
```

**WSL (with an X server):**
```bash
python3 dual_subtitle_embedder_python_ffmpeg.py
```

> ⚠️ Note: Drag-and-drop from Windows Explorer doesn’t work inside WSL. Use the Browse buttons or a Linux file manager like `pcmanfm`.

3. Drag in or browse for:
   - A video file (`.mp4`, `.mkv`, `.mov`, etc.)
   - An English `.srt` file
   - A Vietnamese `.srt` file
4. Choose a compression mode and optionally enable **Downscale to 720p**.
5. Click **Embed Subtitles**.

---

## 💾 Output

The program saves your new file in the output folder as:
```
<original_name>_dual_subbed.mp4
```

Example:
```
The_Family_Tree_of_Demons_dual_subbed.mp4
```

---

## 🧩 Troubleshooting

| Issue | Solution |
|--------|-----------|
| `FFmpeg not found` | Install FFmpeg and add it to PATH |
| Red “no-drop” cursor | Use native Windows Python or a Linux file manager |
| Encoding slow | Use “Smaller” mode, enable 720p downscale, or run in Windows |
| Subtitles not displaying correctly | Ensure `.srt` files are UTF-8 encoded |

---

## 🧾 License
Free for educational and personal use.  

