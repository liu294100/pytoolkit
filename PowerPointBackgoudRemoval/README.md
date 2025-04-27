
# Advanced Slides Utilities - Documentation

## 1. Introduction

Advanced Slides Utilities is a Python application with a graphical user interface (GUI) designed to process Microsoft PowerPoint files (`.pptx` and `.ppt`). Its main functions include:

*   Applying a uniform background (either white or a custom image) to all slides by modifying slide masters.
*   Potentially optimizing the file size by re-compressing the presentation components.
*   Handling single or multiple presentation files as input.
*   Accepting input files directly or via a ZIP archive.
*   Converting older `.ppt` files to the modern `.pptx` format before processing (requires LibreOffice/OpenOffice).
*   Packaging the processed files into a ZIP archive when multiple inputs are provided.

This document guides you through setting up the environment, installing dependencies, running the application, building a standalone executable, and provides a brief overview of the code structure.

## 2. Prerequisites

Before you begin, ensure you have the following installed or available:

1.  **Python:** Version 3.8 or newer is recommended. Python is the programming language the application is written in.
2.  **pip:** The Python package installer. It usually comes bundled with Python installations.
3.  **LibreOffice or OpenOffice (Optional but Required for `.ppt`):** This is **essential** if you need to process legacy `.ppt` files. The application uses the command-line interface (`soffice`) of LibreOffice/OpenOffice to convert `.ppt` to `.pptx` before processing. See section 2.1 for detailed setup instructions, especially for Windows.
4.  **Source Code:** You need the Python script (`run.py` or similar) and the associated helper files (`requirements.txt`, `.bat` scripts if using them).

### 2.1 Installing LibreOffice and Configuring PATH (Windows)

If you need to process `.ppt` files, follow these steps to install LibreOffice and ensure the application can find its command-line tool (`soffice`):

1.  **Download LibreOffice:** Go to the official LibreOffice download page: [https://www.libreoffice.org/download/download/](https://www.libreoffice.org/download/download/)
2.  **Install LibreOffice:** Run the downloaded installer and follow the installation steps. Default settings are usually sufficient.
3.  **Locate the Installation Directory:** After installation, find the `program` sub-directory within the LibreOffice installation folder. The typical location is:
    *   `C:\Program Files\LibreOffice\program`
    *   *Note: If you installed the 32-bit version on a 64-bit system, it might be in `C:\Program Files (x86)\LibreOffice\program`.*
    The key file within this directory is `soffice.exe`.
4.  **Add the Directory to System PATH:** You need to tell Windows where to find `soffice.exe`.
    *   Search for "Environment Variables" in the Windows search bar and select "Edit the system environment variables".
    *   In the "System Properties" window that opens, click the "Environment Variables..." button (usually under the "Advanced" tab).
    *   In the "Environment Variables" window, look for the `Path` variable under the "System variables" section (preferred) or "User variables". Select `Path` and click "Edit...".
    *   In the "Edit environment variable" window, click "New".
    *   Paste the full path to the LibreOffice `program` directory (e.g., `C:\Program Files\LibreOffice\program`) into the new line.
    *   Click "OK" on all open dialog windows to save the changes.
5.  **Verify:** Close any currently open Command Prompt or PowerShell windows. Open a *new* one and type:
    ```bash
    soffice --version
    
    If the PATH is configured correctly, you should see the LibreOffice version information printed. If you get an error like "'soffice' is not recognized...", double-check the path you added and ensure you've reopened the command prompt. Once this command works, the Python script should be able to find and use LibreOffice for `.ppt` conversion.

## 3. Installation and Setup

Follow these steps to set up your environment and install the necessary packages.

### Step 3.1: Install Python

*   **Download:** Go to the official Python website: [https://www.python.org/downloads/](https://www.python.org/downloads/)
*   **Install:** Download the installer for your operating system (Windows, macOS, Linux).
*   **During Installation (Important!):**
    *   On Windows, make sure to check the box that says **"Add Python X.Y to PATH"** during the installation process. This makes Python and pip easily accessible from the command line.
*   **Verify Installation:** Open your terminal or command prompt and type:
    ```bash
    python --version
    # or on some systems
    python3 --version
```
    You should see the installed Python version printed. Also verify pip:
    ```bash
    pip --version
    # or
    pip3 --version
```

### Step 3.2: Set Up Project Directory

1.  **Get the Code:** Download or clone the application's source code files (`run.py`, `requirements.txt`, `install_reqs*.bat`/`.sh`, `build_executable.bat`) into a dedicated folder on your computer (e.g., `C:\Tools\SlideUtils` or `/home/user/slide_utils`).
2.  **Navigate to Directory:** Open your terminal or command prompt and change to that directory.
    *   **Windows:**
        ```batch
        cd C:\Tools\SlideUtils
        ```
    *   **Linux/macOS:**
        ```bash
        cd /home/user/slide_utils
        ```

### Step 3.3: Install Dependencies using `requirements.txt`

The `requirements.txt` file lists the Python libraries needed by the application.

*   **Option A: Direct Pip Install (Recommended)**
    Ensure you are in the project directory in your terminal and run:
    ```bash
    pip install -r requirements.txt
    # or if needed
    python -m pip install -r requirements.txt
    # or
    python3 -m pip install -r requirements.txt
    ```
    This command reads the `requirements.txt` file and installs the specified versions of `python-pptx` and `Pillow` (and their dependencies).

*   **Option B: Using Provided Scripts (`install_reqs_config_top.bat` / `install_reqs_config_top.sh`)**
    These scripts automate the installation and allow pre-configuration of the Python path and proxy settings.
    1.  **Configure:** Open the appropriate script (`.bat` for Windows, `.sh` for Linux/macOS) in a text editor. Modify the configuration variables at the top as needed:
        *   `PYTHON_EXE_CONFIG`: Set the full path to your specific `python.exe` or `python` binary if you don't want to use the one found in the PATH. Leave empty to use the default.
        *   `PROXY_URL_CONFIG`: Set your proxy URL if required (e.g., `http://user:pass@proxy.example.com:8080`). Leave empty if no proxy is needed.
    2.  **Run:**
        *   **Windows:** Double-click `install_reqs_config_top.bat` or run it from the command prompt.
        *   **Linux/macOS:** Make the script executable (`chmod +x install_reqs_config_top.sh`) and then run it (`./install_reqs_config_top.sh`).

### Step 3.4: Install PyInstaller (for Building Executable)

PyInstaller is used to package the Python script into a standalone executable file (`.exe` on Windows). If you only plan to run the script directly using Python, you can skip this step.

Install PyInstaller using pip:
```bash
pip install pyinstaller
# or
python -m pip install pyinstaller
# or
python3 -m pip install pyinstaller
```

## 4. Running the Application (from Source)

Once Python is installed and the dependencies are met, you can run the application directly from the source code.

1.  **Navigate:** Open your terminal or command prompt and navigate to the project directory containing `run.py`.
2.  **Execute:** Run the script using Python:
    ```bash
    python run.py
    # Or if you need to specify a particular Python installation:
    # /path/to/your/python run.py
    # e.g., C:\Python310\python.exe run.py
    ```
3.  **Use the GUI:** The application window should appear.
    *   **Select Input:** Click "Browse..." in section 1 to select one or more `.ppt`/`.pptx` files, or a single `.zip` archive containing them.
    *   **Choose Output:** Click "Browse..." in section 2 to select the output destination. This will be a file path if processing a single input file, or a directory path if processing multiple files or a ZIP archive (the output will be a new ZIP file in this case).
    *   **Background Options (Optional):** Check the box in section 3 if you want to apply a custom background image. Click "Select Image..." to choose a `.png` or `.jpg` file. If unchecked, a solid white background will be applied.
    *   **Process:** Click the "Process Slides" button.
    *   **Status:** Monitor the status label at the bottom for progress updates and completion messages or errors.

## 5. Building the Executable (`.exe`)

To create a standalone executable that can be run on other machines without installing Python or dependencies (though LibreOffice is still needed on the target machine if processing `.ppt` files), use PyInstaller via the provided batch script.

1.  **Ensure PyInstaller is Installed:** (See Step 3.4).
2.  **Configure the Build Script:**
    *   Open the `build_executable.bat` script in a text editor.
    *   Review and adjust the variables in the "Configuration Section" at the top:
        *   `PYTHON_SCRIPT`: Should be `run.py` (or your main script name).
        *   `OUTPUT_NAME`: The desired name for your `.exe` file (e.g., `AdvancedSlidesUtilities`).
        *   `PYINSTALLER_EXE`: **Verify this path points correctly to your `pyinstaller.exe` location.** It might be in a `Scripts` subdirectory of your Python installation. If `pyinstaller` is in your system PATH, you can simplify this to `set PYINSTALLER_EXE=pyinstaller.exe`.
        *   `PYINSTALLER_OPTIONS`: Contains `--onefile` (creates a single `.exe`) and `--windowed` (runs without a console window). You can add other options like `--icon="path/to/your.ico"`.
3.  **Run the Build Script:**
    *   Save your changes to `build_executable.bat`.
    *   Make sure you are in the project directory in your command prompt.
    *   Execute the script: `.\build_executable.bat`
4.  **Find the Executable:**
    *   PyInstaller will run and show output in the console. This may take some time.
    *   If successful, the script will pause and indicate completion.
    *   Your standalone executable file will be located inside a newly created `dist` sub-directory (e.g., `dist\AdvancedSlidesUtilities.exe`).
5.  **Distribute:** You can now copy the `.exe` file from the `dist` folder to another Windows machine and run it. Remember the LibreOffice dependency (installed and PATH configured as per section 2.1) for `.ppt` files on the target machine!

## 6. Code Overview

The `run.py` script contains the core logic for the application. Here's a high-level breakdown:

*   **Imports:** Imports necessary libraries:
    *   `tkinter`: For the GUI elements (windows, buttons, labels, etc.).
    *   `pptx`: The `python-pptx` library for reading/writing `.pptx` files.
    *   `zipfile`: For handling ZIP archives (input and output).
    *   `os`, `pathlib`: For file and directory operations.
    *   `tempfile`: For creating temporary directories during processing.
    *   `subprocess`: To call the external `soffice` command for `.ppt` conversion.
    *   `shutil`: Used to help find the `soffice` executable.
    *   `PIL (Pillow)`: For validating background images.
    *   `traceback`: For printing detailed error information.
    *   `time`: For timing operations.
*   **`AdvancedSlidesUtilitiesApp` Class:** The main class that defines the application's structure and behavior.
    *   **`__init__`:** Initializes the main window, styles, variables, and creates all the GUI widgets (labels, entries, buttons). It also calls `find_soffice` on startup.
    *   **`find_soffice`:** Tries to locate the LibreOffice/OpenOffice `soffice` executable in the system PATH or common installation locations.
    *   **`browse_input`, `browse_output`, `browse_bg_image`:** Handle the logic for the file/directory selection dialogs.
    *   **`toggle_bg_image`:** Enables/disables the background image selection widgets based on the checkbox state.
    *   **`set_background`:** Modifies the background of a slide master (applies white fill or adds the selected image).
    *   **`convert_ppt_to_pptx`:** Uses `subprocess` to call `soffice` to convert a single `.ppt` file to `.pptx` in a temporary directory. Includes error handling.
    *   **`optimize_pptx`:** Processes a single `.pptx` file (either original or converted). It applies the background changes using `set_background` and then re-saves the presentation, potentially with better compression via `zipfile`.
    *   **`process_slides`:** The main function triggered by the "Process Slides" button. It validates inputs and routes the processing to either `process_presentation_files` or `process_zip_file`. It also handles UI disabling/enabling.
    *   **`process_presentation_files`:** Manages the workflow for processing one or more `.ppt`/`.pptx` files provided directly. It handles `.ppt` conversion calls, calls `optimize_pptx` for each valid file, and creates an output ZIP if multiple files were processed successfully.
    *   **`process_zip_file`:** Manages the workflow when the input is a ZIP file. It extracts relevant `.ppt`/`.pptx` files, handles `.ppt` conversion, calls `optimize_pptx` for each, and packages the successful results into a new output ZIP archive.
*   **Main Execution (`if __name__ == "__main__":`)**: Creates the Tkinter root window and starts the `AdvancedSlidesUtilitiesApp` GUI event loop.

## 7. Troubleshooting / Notes

*   **`.ppt` Conversion Fails:** The most common reason is that LibreOffice/OpenOffice is not installed, or the `soffice` command is not in the system's PATH environment variable. **Carefully follow the steps in Section 2.1 (for Windows) or ensure `soffice` is in the PATH on Linux/macOS.** Check the console output for specific errors from `soffice`.
*   **Tkinter Not Found (Linux):** On some Linux distributions, Tkinter needs to be installed separately via the system package manager (e.g., `sudo apt-get update && sudo apt-get install python3-tk` on Debian/Ubuntu).
*   **Errors During Build/Run:** Check the console window where you ran the script or the build process for detailed error messages.
*   **Large Files:** Processing very large presentations or using large background images can take significant time and memory.
*   **Antivirus:** Sometimes, executables created by PyInstaller might be flagged by antivirus software (false positive). This is a known issue with how PyInstaller bundles applications. You may need to create an exception in your antivirus program.
*   **Permissions:** Ensure the script has read permissions for input files/directories and write permissions for the output location and temporary directories.

```