# murata


# Crawl Data 
Crawl videos (no sound), audios as well as description by powerful tools such as DrissionPage, yt-dlp.
<br><br>**Target**: By using Vector Semantics and Embedding, we aim to crawl data through keywords which are filtered to optimize productivity.





# Instruction
**File ffmpeg.exe a powerful, free, open-source multimedia framework used for handling audio, video, and other media files and streams.**<br><br>
**DrissionPage is a powerful, Python-based web automation tool that integrates the convenience of browser automation**<br><br>
**1**: 
In folder **youtube_tiktok_crawler**, there are 4 files to get links and crawl videos on TikTok, Youtube.<br>
**2**:Extract links videos into link_tiktok.txt <br>
**3**: In **crawler_tiktok.py**, starting crawling, similar to Youtube (using **yt-dlp**).<br><br>
**Note:** Three relevant files were included in folder **bin**.

## How to download ffmpeg.exe:
Since FFmpeg does not provide an official installer, you must download pre-compiled binaries for Windows.

1.  **Select a Source:** Navigate to a trusted source for FFmpeg builds, such as **Gyan**:
    * **Download Link:** [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2.  **Download the ZIP File:**
    * Scroll down to the **"Release builds"** section.
    * Download the latest version of the **ZIP** archive (usually the `-full` build for complete codec support).
    * *Example file name:* `ffmpeg-n4.4-latest-win64-gpl-full-4.4.zip`
### 2. Extract and Set up File Location

Choose a stable and accessible location for the FFmpeg folder.

1.  **Extract:** Right-click the downloaded ZIP file and extract its contents.
2.  **Place Folder:** Move the extracted FFmpeg folder to a location with a simple path, such as:
    * `C:\ffmpeg`
3.  **Verify:** The main executable file, `ffmpeg.exe`, must be located inside the `bin` subdirectory (e.g., `C:\ffmpeg\bin\ffmpeg.exe`).

### 3. Configure the System PATH Environment Variable

This crucial step allows you to execute the `ffmpeg` command from any terminal or Command Prompt window.

1.  **Copy the Path:** Copy the full path to the **`bin`** folder: **`C:\ffmpeg\bin`**.
2.  **Open Environment Variables:** Search the Windows Start menu for **"Edit the system environment variables"** and open the system properties.
3.  **Edit PATH:**
    * Click **"Environment Variables..."** at the bottom of the System Properties window.
    * Under **System variables**, select the **`Path`** variable and click **"Edit..."**.
    * Click **"New"** and paste the copied path (`C:\ffmpeg\bin`).
    * Click **OK** on all windows to save the changes.