
# Advanced Slides Utilities - 中文文档

## 1. 简介

Advanced Slides Utilities 是一个带有图形用户界面 (GUI) 的 Python 应用程序，旨在处理 Microsoft PowerPoint 文件（`.pptx` 和 `.ppt`）。其主要功能包括：

*   通过修改幻灯片母版，为所有幻灯片应用统一的背景（白色或自定义图片）。
*   通过重新压缩演示文稿组件来优化文件大小。
*   处理单个或多个演示文稿文件作为输入。
*   直接接受输入文件或通过 ZIP 压缩包接受输入。
*   在处理前将旧版 `.ppt` 文件转换为现代 `.pptx` 格式（需要安装 LibreOffice/OpenOffice）。
*   当提供多个输入文件时，将处理后的文件打包成 ZIP 压缩包。

本文档将指导您完成环境设置、安装依赖项、运行应用程序、构建独立可执行文件，并简要概述代码结构。

## 2. 先决条件

在开始之前，请确保您已安装或具备以下条件：

1.  **Python:** 推荐使用 3.8 或更高版本。Python 是编写此应用程序的编程语言。
2.  **pip:** Python 包安装器。通常随 Python 安装包一起提供。
3.  **LibreOffice 或 OpenOffice (可选，但处理 `.ppt` 文件必需):** 如果您需要处理旧版 `.ppt` 文件，这是**必不可少**的。该应用程序使用 LibreOffice/OpenOffice 的命令行接口 (`soffice`) 将 `.ppt` 转换为 `.pptx` 后再进行处理。请参阅 2.1 节了解详细的设置说明，尤其是针对 Windows 系统。
4.  **源代码:** 您需要应用程序的 Python 脚本（`run.py` 或类似名称）以及相关的辅助文件（`requirements.txt`，如果使用，还需要 `.bat` 或 `.sh` 脚本）。

### 2.1 安装 LibreOffice 并配置 PATH (Windows)

如果您需要处理 `.ppt` 文件，请按照以下步骤安装 LibreOffice 并确保应用程序可以找到其命令行工具 (`soffice`)：

1.  **下载 LibreOffice:** 访问 LibreOffice 官方下载页面：[https://zh-cn.libreoffice.org/get-libreoffice/download-libreoffice/](https://zh-cn.libreoffice.org/get-libreoffice/download-libreoffice/)
2.  **安装 LibreOffice:** 运行下载的安装程序，并按照安装步骤进行操作。通常使用默认设置即可。
3.  **定位安装目录:** 安装完成后，找到 LibreOffice 安装文件夹中的 `program` 子目录。典型位置通常是：
    *   `C:\Program Files\LibreOffice\program`
    *   *注意：如果您在 64 位系统上安装了 32 位版本，它可能位于 `C:\Program Files (x86)\LibreOffice\program`。*
    此目录中的关键文件是 `soffice.exe`。
4.  **将目录添加到系统环境变量 PATH:** 您需要告诉 Windows 在哪里可以找到 `soffice.exe`。
    *   在 Windows 搜索栏中搜索“环境变量”，然后选择“编辑系统环境变量”。
    *   在打开的“系统属性”窗口中，单击“环境变量...”按钮（通常位于“高级”选项卡下）。
    *   在“环境变量”窗口中，查找“系统变量”（首选）或“用户变量”部分下的 `Path` 变量。选中 `Path`，然后单击“编辑...”。
    *   在“编辑环境变量”窗口中，单击“新建”。
    *   将 LibreOffice `program` 目录的完整路径（例如 `C:\Program Files\LibreOffice\program`）粘贴到新行中。
    *   在所有打开的对话框窗口上单击“确定”以保存更改。
5.  **验证:** 关闭所有当前打开的命令提示符 (Command Prompt) 或 PowerShell 窗口。打开一个*新的*窗口并输入：
    ```bash
    soffice --version
    
    如果 PATH 配置正确，您应该会看到打印出的 LibreOffice 版本信息。如果您收到类似“'soffice' 不是内部或外部命令...”的错误，请仔细检查您添加的路径，并确保您已重新打开命令提示符。一旦此命令可以正常工作，Python 脚本就应该能够找到并使用 LibreOffice 进行 `.ppt` 转换了。

## 3. 安装与设置

请按照以下步骤设置您的环境并安装必要的软件包。

### Step 3.1: 安装 Python

*   **下载:** 访问 Python 官方网站：[https://www.python.org/downloads/](https://www.python.org/downloads/)
*   **安装:** 下载适用于您操作系统（Windows, macOS, Linux）的安装程序。
*   **安装过程中 (重要!):**
    *   在 Windows 上，请务必在安装过程中勾选 **"Add Python X.Y to PATH"**（将 Python X.Y 添加到 PATH）复选框。这使得从命令行可以轻松访问 Python 和 pip。
*   **验证安装:** 打开您的终端或命令提示符，然后输入：
    ```bash
    python --version
    # 或者在某些系统上
    python3 --version
```
    您应该能看到已安装的 Python 版本号。同时验证 pip：
    ```bash
    pip --version
    # 或
    pip3 --version
```

### Step 3.2: 设置项目目录

1.  **获取代码:** 将应用程序的源代码文件（`run.py`, `requirements.txt`, `install_reqs*.bat`/`.sh`, `build_executable.bat`）下载或克隆到您计算机上的一个专用文件夹（例如 `C:\Tools\SlideUtils` 或 `/home/user/slide_utils`）。
2.  **导航到目录:** 打开您的终端或命令提示符，并切换到该目录。
    *   **Windows:**
        ```batch
        cd C:\Tools\SlideUtils
        ```
    *   **Linux/macOS:**
        ```bash
        cd /home/user/slide_utils
        ```

### Step 3.3: 使用 `requirements.txt` 安装依赖项

`requirements.txt` 文件列出了应用程序所需的 Python 库。

*   **选项 A: 直接 Pip 安装 (推荐)**
    确保您在终端中位于项目目录下，然后运行：
    ```bash
    pip install -r requirements.txt
    # 或者如果需要
    python -m pip install -r requirements.txt
    # 或
    python3 -m pip install -r requirements.txt
    ```
    此命令会读取 `requirements.txt` 文件，并安装指定版本的 `python-pptx` 和 `Pillow`（以及它们的依赖项）。

*   **选项 B: 使用提供的脚本 (`install_reqs_config_top.bat` / `install_reqs_config_top.sh`)**
    这些脚本可以自动执行安装过程，并允许预先配置 Python 路径和代理设置。
    1.  **配置:** 使用文本编辑器打开相应的脚本（Windows 使用 `.bat`，Linux/macOS 使用 `.sh`）。根据需要修改顶部的配置变量：
        *   `PYTHON_EXE_CONFIG`: 如果您不想使用 PATH 中找到的 Python，请在此处设置您的特定 `python.exe` 或 `python` 二进制文件的完整路径。留空则使用默认值。
        *   `PROXY_URL_CONFIG`: 如果需要，请设置您的代理 URL（例如 `http://user:pass@proxy.example.com:8080`）。如果不需要代理，请留空。
    2.  **运行:**
        *   **Windows:** 双击 `install_reqs_config_top.bat` 或从命令提示符运行它。
        *   **Linux/macOS:** 使脚本可执行 (`chmod +x install_reqs_config_top.sh`)，然后运行它 (`./install_reqs_config_top.sh`)。

### Step 3.4: 安装 PyInstaller (用于构建可执行文件)

PyInstaller 用于将 Python 脚本打包成独立的可执行文件（Windows 上是 `.exe`）。如果您只打算直接使用 Python 运行脚本，可以跳过此步骤。

使用 pip 安装 PyInstaller：
```bash
pip install pyinstaller
# 或
python -m pip install pyinstaller
# 或
python3 -m pip install pyinstaller
```

## 4. 运行应用程序 (从源代码)

安装好 Python 并满足依赖项后，您可以直接从源代码运行应用程序。

1.  **导航:** 打开您的终端或命令提示符，并导航到包含 `run.py` 的项目目录。
2.  **执行:** 使用 Python 运行脚本：
    ```bash
    python run.py
    # 或者如果您需要指定特定的 Python 安装：
    # /path/to/your/python run.py
    # 例如： C:\Python310\python.exe run.py
    ```
3.  **使用 GUI:** 应用程序窗口应该会出现。
    *   **选择输入:** 单击第 1 部分中的“浏览...”以选择一个或多个 `.ppt`/`.pptx` 文件，或包含这些文件的单个 `.zip` 压缩包。
    *   **选择输出:** 单击第 2 部分中的“浏览...”以选择输出目标。如果处理单个输入文件，这将是一个文件路径；如果处理多个文件或 ZIP 压缩包，这将是一个目录路径（在这种情况下，输出将是一个新的 ZIP 文件）。
    *   **背景选项 (可选):** 如果要应用自定义背景图片，请勾选第 3 部分中的复选框。单击“选择图片...”以选择一个 `.png` 或 `.jpg` 文件。如果未勾选，将应用纯白色背景。
    *   **处理:** 单击“处理幻灯片”按钮。
    *   **状态:** 观察底部的状态标签以获取进度更新、完成消息或错误信息。

## 5. 构建可执行文件 (`.exe`)

要创建一个独立的可执行文件，使其可以在其他没有安装 Python 或依赖项的机器上运行（但如果需要处理 `.ppt` 文件，目标机器上仍需安装 LibreOffice），请使用提供的批处理脚本和 PyInstaller。

1.  **确保 PyInstaller 已安装:** (请参阅步骤 3.4)。
2.  **配置构建脚本:**
    *   使用文本编辑器打开 `build_executable.bat` 脚本。
    *   检查并调整顶部“Configuration Section”中的变量：
        *   `PYTHON_SCRIPT`: 应为 `run.py`（或您的主脚本名称）。
        *   `OUTPUT_NAME`: 您想要的最终 `.exe` 文件的名称（例如 `AdvancedSlidesUtilities`）。
        *   `PYINSTALLER_EXE`: **请验证此路径是否正确指向您系统上的 `pyinstaller.exe` 位置。** 它可能位于 Python 安装目录的 `Scripts` 子目录中。如果 `pyinstaller` 在您的系统 PATH 中，您可以将其简化为 `set PYINSTALLER_EXE=pyinstaller.exe`。
        *   `PYINSTALLER_OPTIONS`: 包含 `--onefile`（创建单个 `.exe`）和 `--windowed`（运行时不显示控制台窗口）。您可以添加其他选项，例如 `--icon="path/to/your.ico"`。
3.  **运行构建脚本:**
    *   保存您对 `build_executable.bat` 的更改。
    *   确保您在命令提示符中位于项目目录下。
    *   执行脚本：`.\build_executable.bat`
4.  **查找可执行文件:**
    *   PyInstaller 将运行并在控制台中显示输出。这可能需要一些时间。
    *   如果成功，脚本将暂停并指示完成。
    *   您的独立可执行文件将位于新创建的 `dist` 子目录中（例如 `dist\AdvancedSlidesUtilities.exe`）。
5.  **分发:** 您现在可以将 `dist` 文件夹中的 `.exe` 文件复制到另一台 Windows 机器上运行。请记住，如果在目标机器上需要处理 `.ppt` 文件，则该机器上必须安装 LibreOffice 并且其 PATH 配置正确（参照 2.1 节）！

## 6. 代码概述

`run.py` 脚本包含了应用程序的核心逻辑。以下是高层次的分解：

*   **导入 (Imports):** 导入必要的库：
    *   `tkinter`: 用于 GUI 元素（窗口、按钮、标签等）。
    *   `pptx`: `python-pptx` 库，用于读写 `.pptx` 文件。
    *   `zipfile`: 用于处理 ZIP 压缩包（输入和输出）。
    *   `os`, `pathlib`: 用于文件和目录操作。
    *   `tempfile`: 用于在处理过程中创建临时目录。
    *   `subprocess`: 用于调用外部 `soffice` 命令进行 `.ppt` 转换。
    *   `shutil`: 用于帮助查找 `soffice` 可执行文件。
    *   `PIL (Pillow)`: 用于验证背景图片。
    *   `traceback`: 用于打印详细的错误信息。
    *   `time`: 用于计时操作。
*   **`AdvancedSlidesUtilitiesApp` 类:** 定义应用程序结构和行为的主类。
    *   **`__init__`:** 初始化主窗口、样式、变量，并创建所有 GUI 控件（标签、输入框、按钮）。它还在启动时调用 `find_soffice`。
    *   **`find_soffice`:** 尝试在系统 PATH 或常见安装位置查找 LibreOffice/OpenOffice 的 `soffice` 可执行文件。
    *   **`browse_input`, `browse_output`, `browse_bg_image`:** 处理文件/目录选择对话框的逻辑。
    *   **`toggle_bg_image`:** 根据复选框状态启用/禁用背景图片选择控件。
    *   **`set_background`:** 修改幻灯片母版的背景（应用白色填充或添加所选图片）。
    *   **`convert_ppt_to_pptx`:** 使用 `subprocess` 调用 `soffice` 将单个 `.ppt` 文件转换为 `.pptx` 到临时目录中。包含错误处理。
    *   **`optimize_pptx`:** 处理单个 `.pptx` 文件（原始的或转换后的）。它使用 `set_background` 应用背景更改，然后通过 `zipfile` 重新保存演示文稿，可能实现更好的压缩。
    *   **`process_slides`:** 由“处理幻灯片”按钮触发的主函数。它验证输入并将处理路由到 `process_presentation_files` 或 `process_zip_file`。它还处理 UI 的禁用/启用。
    *   **`process_presentation_files`:** 管理直接提供的单个或多个 `.ppt`/`.pptx` 文件的处理流程。它处理 `.ppt` 转换调用，为每个有效文件调用 `optimize_pptx`，并在成功处理多个文件后创建输出 ZIP。
    *   **`process_zip_file`:** 管理输入为 ZIP 文件时的处理流程。它提取相关的 `.ppt`/`.pptx` 文件，处理 `.ppt` 转换，为每个文件调用 `optimize_pptx`，并将成功的结果打包到一个新的输出 ZIP 压缩包中。
*   **主执行 (`if __name__ == "__main__":`)**: 创建 Tkinter 根窗口并启动 `AdvancedSlidesUtilitiesApp` GUI 事件循环。

## 7. 故障排除 / 注意事项

*   **`.ppt` 转换失败:** 最常见的原因是未安装 LibreOffice/OpenOffice，或者 `soffice` 命令不在系统的 PATH 环境变量中。**请仔细遵循 2.1 节中的步骤 (针对 Windows) 或确保 `soffice` 在 Linux/macOS 的 PATH 中。** 检查控制台输出以获取来自 `soffice` 的具体错误信息。
*   **Tkinter 未找到 (Linux):** 在某些 Linux 发行版上，Tkinter 需要通过系统包管理器单独安装（例如，在 Debian/Ubuntu 上运行 `sudo apt-get update && sudo apt-get install python3-tk`）。
*   **构建/运行错误:** 检查您运行脚本或构建过程的控制台窗口，以获取详细的错误消息。
*   **大文件:** 处理非常大的演示文稿或使用大型背景图片可能会消耗大量时间和内存。
*   **杀毒软件:** 有时，由 PyInstaller 创建的可执行文件可能会被杀毒软件标记（误报）。这是 PyInstaller 打包应用程序方式的一个已知问题。您可能需要在杀毒软件中创建例外。
*   **权限:** 确保脚本对输入文件/目录具有读取权限，并对输出位置和临时目录具有写入权限。

```