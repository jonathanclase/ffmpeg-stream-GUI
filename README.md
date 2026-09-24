# ffmpeg-stream-GUI

*Just what the world needed, another GUI for ffmpeg...*

A Python/Tkinter UI for merging audio, video, and subtitle streams from multiple files using ffmpeg, with per-stream metadata and sync offsets.

---

## User Scenarios

**Embedded Commentary**: Kylie has a downloaded copy of Rian Johnson's in-theater commentary for *Knives Out* (2019), and a digital copy of the movie that she has purchased. She wants to embed the commentary so that she can play the it in sync with the movie. She uses the ffmpeg-stream-GUI to open both files. She adds a title to the commentary track so she can distinguish it from the main audio track. The tracks do not sync up perfectly -- the movie lags behind the commentary audio by about three seconds. To correct this, she sets the commentary `Offset` value to 3.0. She uses the `Fifteen-minute test` option to confirm the sync, and then creates the full-length file once she has verified. She watches the video on her iPhone using Infuse, picking the commentary track when desired.

**Multiple Languages**: Mark has two digital versions of *My Neighbor Totoro* (1988): one in the original Japanese, and one dubbed into his native English. He uses the ffmpeg-stream-GUI to open both files. He de-selects the video from one of them, leaving one video and two audio tracks. He adds titles and languages to both audio tracks to identify each version's language and the voice-dub actors in the English version. He knows the files are synchronized so he de-selects the `Fifteen-minute test` option. He generates a single video file container that includes both languages. He uses VLC to watch the video file and to select the language he wants when viewing it.

**Subtitles in a Container**: Darius watches content with subtitles. When using the Plex Roku client, he notes that pausing or seeking on videos can cause the subtitles to become de-synchronized. He wants to embed the subtitles into the video container directly so that he can avoid syncing issues. He uses ffmpeg-stream-GUI to open both the digital video file and the subtitles he has downloaded from *OpenSubtitles*. He generates the file with a `Fifteen-minute test` option, and confirms that the subtitles are in sync. He creates the full version of the file and re-adds it to his Plex collection.

**Reaction Tracks**: Ash has a RiffTrax audio file for *Santa Claus Conquers the Martians* (1964) and a digital copy created from a DVD. They want to listen to the RiffTrax alongside the film. They use ffmpeg-stream-GUI to open both the digital video file and the RiffTrax audio file. They also open a copy of the film's subtitles downloaded from *OpenSubtitles*. They add a title to the original audio stream and to the RiffTrax audio stream to distinguish the two tracks from each other. They generate a video file with the `Fifteen-minute test` option to confirm how the tracks match. The RiffTrax commentary is out-of-sync with the movie, having about a four-second delay. Ash sets the `Offset` values of the video, original audio, and subtitle streams to 4.0 seconds and generates another file with the `Fifteen-minute test` option. Upon viewing, the timing does not quite match. Ash updates the `Offset` values to 3.5 seconds for the three streams and generates another version with the `Fifteen-minute test` option checked. Satisfied with the synchronicity of this version, Ash creates a full version of the file, re-adds it to their Jellyfish library, and views it using a Jellyfish client for Android.



---
## Requirements

- Python 3.10 or later
- `tkinter`
    - On Ubuntu/Mint/Debian: `tkinter` may not bundled with Python on Debian-based systems. Install it before proceeding: ```sudo apt install python3-tk```
    - On Fedora/RHEL: `sudo dnf install python3-tkinter`  
    - On macOS and Windows, `tkinter` should be included with the standard Python installer from python.org
- `ffprobe`
    - `ffprobe` and `ffmpeg` will be fetched and installed automatically if need be, via the `static-ffmpeg` package, which is a dependency for the application
    - *While `ffmpeg` is technically not required to run ffmpeg-stream-GUI, it is required to make use of the resulting commands*
---
## Installation

#### Using `pipx` (Recommended)

```bash
pipx install git+https://github.com/jonathanclase/ffmpeg-stream-GUI.git
```

Or from a local clone:

```bash
git clone https://github.com/jonathanclase/ffmpeg-stream-GUI.git
cd ffmpeg-stream-GUI
pipx install .
```


**To install `pipx`:**

<table>
<th>Operating System</th><th>Run</th>
<tr><td>Windows</td><td>

```bash
pip install pipx
pipx ensurepath
```
</td></tr>
<tr><td>macOS (with Homebrew)</td><td>

```bash
brew install pipx
pipx ensurepath
```
</td></tr>
<tr><td>macOS (without Homebrew)</td><td>

```bash
pip install pipx
pipx ensurepath
```
</td></tr>

<tr><td>Ubuntu/Mint/Debian</td><td>

```bash
sudo apt install pipx
pipx ensurepath
```
</td></tr>

<tr><td>Fedora/RHEL</td><td>

```bash
sudo dnf install pipx
pipx ensurepath
```
</td></tr>
</table>

*`pipx ensurepath` adds to the PATH environment variable, if necessary*

#### Using `pip`

Run:

```bash
pip install git+https://github.com/jonathanclase/ffmpeg-stream-GUI.git
```

Or from a local clone:

```bash
git clone https://github.com/jonathanclase/ffmpeg-stream-GUI.git
cd ffmpeg-stream-GUI
pip install .
```

#### Upgrading

Run one of the following:

```bash
pipx install --force git+https://github.com/jonathanclase/ffmpeg-stream-GUI.git
```

```bash
pip install --force-reinstall git+https://github.com/jonathanclase/ffmpeg-stream-GUI.git
```

Or from a local clone:

```bash
git clone https://github.com/jonathanclase/ffmpeg-stream-GUI.git
cd ffmpeg-stream-GUI
pipx install --force .
```

```bash
git clone https://github.com/jonathanclase/ffmpeg-stream-GUI.git
cd ffmpeg-stream-GUI
pip install --force-reinstall .
```

#### Uninstalling

Run `pipx uninstall streamgui` or `pip uninstall streamgui`

The `static-ffmpeg` package and its downloaded ffmpeg/ffprobe binaries may not be removed automatically. To remove them, run `pip uninstall static-ffmpeg`

---

## Usage

### Running the app

After installation, launch by running:

```bash
streamgui
```

Upon first launch, `static-ffmpeg` will download the ffmpeg/ffprobe binaries for your platform if required.

### Using the app

[See the user-guide](docs/user-guide.md)

---

## Product Roadmap

***Goal:** To create a tool that allows for merging of multiple files, including foreign language audio, subtitle(s), commentary audio, and reaction tracks, into a single output file, with configurable parameters to ensure alignment and metadata for the tracks*

#### 🟪 ${\color{purple}\textsf{Completed}}$
- ~~Disallow multi-line commands if not supported by the host OS~~
    - ~~Goal: Improve the cross-platform compatibility of the **tool**~~
- ~~Explore the viability of using a better file selector~~
    - ~~Goal: Improve the ability to work with **multiple files**~~
- ~~Add outpit file naming~~
- ~~Goal: Add title parameter for the **output file** as a **configurable parameter**~~
- ~~Fixed issue with strikethrough on unchecked streams to improve visibility of **configurable parameters**~~
- ~~Change the default sizing for the top frame to fix an issue with visibility of the **configurable paramters**~~
- ~~Added Container title and language metadata as **configurable parameters** for the **output file**~~
- ~~Handle scenarios where existing metadata is set to blank~~

#### 🟩 ${\color{green}\textsf{Now}}$


#### 🟦 ${\color{blue}\textsf{Next}}$
- Explore a mechanism to limit language drop-downs
    - Goal: Improve usability of the **configurable parameters** for the **foreign language audio** values
    - Determine where to store and maintain language settings
    - Determine the default set of languages to include
    - Create a UI for maintaining the language options
    - Keep all UI elements in sync when changes are made

#### 🟧 ${\color{orange}\textsf{Later}}$

- Explore the viability of adding drag-and-drop functionality from the file system
    - Goal: Improve the ability to work with **multiple files**

---

## License

MIT — see [LICENSE](LICENSE)
