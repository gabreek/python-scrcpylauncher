# Scrcpy Launcher

A simple and lightweight scrcpy GUI compatible with Winlator (bionic) shortcuts.

This tool provides a user-friendly graphical interface to manage and launch `scrcpy` instances with custom settings for both standard Android apps and Winlator games.

## ✨ Features

* **Tabbed Interface:** Separate, organized tabs for Android Apps, Winlator Games, and Scrcpy configuration.
* **Android App Launcher:**
    * Automatically lists all installed applications on your device.
    * Scrapes app icons from the Google Play Store.
    * Supports custom icons via drag-and-drop.
    * Save specific `scrcpy` settings for each app.
* **Winlator Game Launcher:**
    * Automatically discovers game shortcuts (`.desktop` files) from your Winlator installation. (You need export shortcut to frontend in winlator app)
    * **Automatic Icon Extraction:** Fetches and caches game icons directly from the game's `.exe` file.
    * Supports custom game icons via drag-and-drop.
    * Save specific `scrcpy` settings for each game, perfect for custom resolutions and performance tuning.
* **Advanced Scrcpy Configuration:** A dedicated tab to tweak all major `scrcpy` settings, including resolution, bitrate, codecs, and more. All settings are saved automatically. (First release requires you to open the program with the phone to be connected via usb to populate codecs lists)
* **Custom Window Icons:** The `scrcpy` window will automatically use the game's or app's icon, providing a native look and feel.

---

## 🚧 To-Do / Future Features

- [ ] Finish options GUI (you can use custom options commands).
- [ ] Multiple windows audio management.
- [ ] Full support for ADB over WiFi.
- [ ] Multi-device management interface.
- [ ] ... any other ideas are welcome!

---

## 🚀 Installation

This application is designed for Linux systems.

### 1. System Dependencies

First, ensure you have `adb` and `scrcpy` installed and available in your system's PATH.

```bash
# On Debian/Ubuntu based systems
sudo apt update
sudo apt install adb scrcpy
```

### 2. Clone the Repository

```bash
git clone https://github.com/gabreek/python-scrcpylauncher.git
cd python-scrcpylauncher
```

### 3. Set Up Python Environment

It is highly recommended to use a Python virtual environment.

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install the required Python packages
pip install -r requirements.txt
```

---

## 🏃‍♀️ How to Run

A convenience script `run.sh` is provided to automatically activate the virtual environment and start the application.

1.  **Make the script executable (only needs to be done once):**
    ```bash
    chmod +x run.sh
    ```

2.  **Run the application:**
    ```bash
    ./run.sh
    ```

---

## 🎨 Custom Icons

One of the key features is the ability to easily customize icons for your apps and games.

* **Android Apps:** If you don't like the icon scraped from the Play Store, simply drag and drop your preferred image file (`.png`, `.jpg`, etc.) directly onto the existing icon in the "Apps" tab.
* **Winlator Games:** If the icon extracted from the `.exe` is incorrect or missing, just drag and drop your game's poster or icon onto the placeholder in the "Winlator" tab.

The new icon will be automatically resized, converted to `.png`, and cached for future use.
