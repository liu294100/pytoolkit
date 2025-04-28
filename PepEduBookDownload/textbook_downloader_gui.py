import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import requests
import re
import os
import img2pdf
import threading
import time
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError # <--- 新增导入

# --- Core Logic Functions ---

# get_textbook_info 函数保持不变...
def get_textbook_info(url):
    # ... (之前的代码)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15) # Increased timeout
        response.raise_for_status()
        # Try decoding with utf-8 first, fallback to detected encoding or ignore errors
        try:
            html = response.content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                 html = response.content.decode(response.apparent_encoding)
            except Exception:
                 html = response.content.decode('utf-8', errors='ignore')


        title_match = re.findall(r'<title>(.+?)</title>', html, re.S)
        title = "textbook"
        if title_match:
            raw_title = title_match[0].strip()
            title = re.sub(r'[\\/*?:"<>|]', '_', raw_title).strip()
            if not title: title = "textbook"

        page_count_match = re.findall(r'BookInfo\.getPageCount\s*=\s*function\s*\(\s*\)\s*{\s*return\s*(\d+);', html)
        page_count = int(page_count_match[0]) if page_count_match else None

        if page_count is None:
             img_matches = re.findall(r'files/mobile/(\d+)\.jpg', html)
             if img_matches:
                 page_count = max(int(p) for p in img_matches)
             else:
                 # Try another common pattern
                 page_count_match_alt = re.findall(r'pageCount\s*[:=]\s*(\d+)', html, re.IGNORECASE)
                 if page_count_match_alt:
                     page_count = int(page_count_match_alt[0])
                 else:
                    page_count = 10 # Last resort default

        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        book_id = path_parts[0] if path_parts else None

        if not book_id:
             # Try finding bookId in script tags as fallback
             book_id_match = re.search(r'bookId\s*[:=]\s*["\']?(\d+)["\']?', html, re.IGNORECASE)
             if book_id_match:
                 book_id = book_id_match.group(1)
             else:
                raise Exception("无法从URL或页面内容中提取教材ID")

        return title, page_count, book_id
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        if "无法获取教材信息" not in str(e) and "无法从URL中提取教材ID" not in str(e):
             raise Exception(f"解析教材信息时出错: {str(e)}")
        else:
             raise e


# 下载教材并转换为PDF (修改版)
def download_textbook_thread(root, url, save_path, progress_var, download_button, status_label):
    temp_dir = None # Initialize temp_dir
    valid_jpg_files = [] # Store paths of validated images
    conversion_successful = False # Flag to control cleanup
    error_occurred = False # Flag general errors

    try:
        root.after(0, status_label.config, {'text': "正在获取教材信息..."})
        title, page_count, book_id = get_textbook_info(url)
        sanitized_title = re.sub(r'[\\/*?:"<>|]', '_', title).strip()
        if not sanitized_title: sanitized_title = "textbook"

        root.after(0, status_label.config, {'text': f"《{title}》({page_count}页). 下载中..."})

        temp_dir = f"temp_{sanitized_title}_{int(time.time())}"
        os.makedirs(temp_dir, exist_ok=True)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                   'Referer': url} # Add Referer, sometimes helps

        skipped_pages = 0
        for page in range(1, page_count + 1):
            # Calculate expected progress point *before* potential skip
            progress_target = int(80 * page / page_count)

            jpg_url = f'https://book.pep.com.cn/{book_id}/files/mobile/{page}.jpg'
            jpg_path = os.path.join(temp_dir, f"{page:03d}.jpg") # Padded for sorting

            try:
                response = requests.get(jpg_url, headers=headers, timeout=20) # Longer timeout
                response.raise_for_status()

                # Basic check: Content-Type header
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' not in content_type:
                    print(f"警告: 第 {page} 页 URL {jpg_url} 返回的 Content-Type 不是图像 ({content_type}). 跳过.")
                    root.after(0, status_label.config, {'text': f"警告: 第 {page} 页内容非图像，已跳过"})
                    skipped_pages += 1
                    root.after(0, progress_var.set, progress_target) # Update progress anyway
                    continue # Skip to next page

                # Save the content
                with open(jpg_path, 'wb') as f:
                    f.write(response.content)

                # *** Image Validation Step ***
                try:
                    with Image.open(jpg_path) as img:
                        img.verify() # Check if Pillow can understand the file structure
                    # Optional: Deeper check by trying to load data
                    # with Image.open(jpg_path) as img:
                    #     img.load()
                    valid_jpg_files.append(jpg_path) # Add to list only if valid
                    # Update status for successful download
                    root.after(0, status_label.config, {'text': f"已下载: {page}/{page_count}"})

                except (UnidentifiedImageError, SyntaxError) as img_err: # Catch Pillow errors
                    print(f"警告: 下载的文件 {jpg_path} 不是有效的图像格式 ({img_err}). 跳过此页.")
                    root.after(0, status_label.config, {'text': f"警告: 第 {page} 页文件无效，已跳过"})
                    skipped_pages += 1
                    try:
                        os.remove(jpg_path) # Clean up invalid file
                    except OSError: pass
                except Exception as img_val_err: # Catch other potential errors during validation
                    print(f"警告: 验证文件 {jpg_path} 时发生未知错误: {img_val_err}. 跳过此页.")
                    root.after(0, status_label.config, {'text': f"警告: 第 {page} 页验证失败，已跳过"})
                    skipped_pages += 1
                    try:
                        os.remove(jpg_path) # Clean up invalid file
                    except OSError: pass
                # *** End Validation Step ***

                # Update progress bar
                root.after(0, progress_var.set, progress_target)

                # time.sleep(0.1) # Consider a slightly longer delay if needed

            except requests.exceptions.RequestException as req_err:
                print(f"警告: 无法下载第 {page} 页 ({jpg_url}): {req_err}")
                root.after(0, status_label.config, {'text': f"警告: 跳过第 {page} 页 (下载失败)"})
                skipped_pages += 1
                root.after(0, progress_var.set, progress_target) # Update progress anyway


        if not valid_jpg_files:
            raise Exception(f"未能成功下载并验证任何有效页面。共尝试 {page_count} 页，跳过 {skipped_pages} 页。")

        root.after(0, status_label.config, {'text': f"下载完成 ({page_count - skipped_pages}/{page_count} 页). 正在转换为PDF..."})
        root.after(0, progress_var.set, 85)

        try:
            # Sort validated files numerically before conversion
            valid_jpg_files.sort()
            print(f"准备转换以下 {len(valid_jpg_files)} 个有效文件到PDF: {valid_jpg_files}")
            with open(save_path, 'wb') as f:
                # Use Pillow engine explicitly if needed, default usually works
                # f.write(img2pdf.convert(valid_jpg_files, producer="MyDownloader", engine=img2pdf.Engine.pillow))
                f.write(img2pdf.convert(valid_jpg_files))
            conversion_successful = True # Mark conversion as successful for cleanup logic
        except Exception as pdf_err:
             # Keep temp files if PDF conversion fails
             print(f"传递给 img2pdf 的有效文件列表: {valid_jpg_files}")
             raise Exception(f"转换为PDF时出错: {pdf_err}.\n请检查临时文件夹中的图像文件:\n{temp_dir}")

        root.after(0, progress_var.set, 100)
        root.after(0, status_label.config, {'text': "PDF转换完成。"})

        # --- Success ---
        final_msg = f"教材《{title}》({page_count - skipped_pages}页)\n已成功保存为:\n{save_path}"
        if skipped_pages > 0:
            final_msg += f"\n(注意: 跳过了 {skipped_pages} 个无效或无法下载的页面)"
        root.after(0, lambda: messagebox.showinfo("成功", final_msg))
        root.after(0, status_label.config, {'text': "完成！"})

    except Exception as e:
        error_occurred = True # Mark that an error happened
        error_message = f"发生错误:\n{str(e)}"
        print(f"错误详情: {e}")
        # Schedule error message box in the main thread
        root.after(0, lambda: messagebox.showerror("错误", error_message))
        root.after(0, status_label.config, {'text': "操作失败"})

    finally:
        # --- Cleanup ---
        if temp_dir and os.path.exists(temp_dir):
            if conversion_successful: # If PDF was made successfully, clean up fully
                try:
                    print(f"操作成功，清理临时文件: {temp_dir}")
                    for jpg in valid_jpg_files: # Use the list of validated files
                        if os.path.exists(jpg):
                             try: os.remove(jpg)
                             except OSError: pass # Ignore minor error during cleanup
                    # Attempt to remove any remaining unexpected files/folders if needed
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True) # More robust removal
                    print("临时文件清理完成。")
                except Exception as clean_err:
                    print(f"警告: 清理临时文件时发生错误: {clean_err}")
            elif error_occurred: # If an error occurred (not specific to PDF conversion fail)
                 # Optionally keep the folder if download partially succeeded but failed later
                 # Or decide to clean up based on where the error happened
                 # For simplicity now, we'll keep it if the error wasn't a PDF conversion error
                 # But we already handled the PDF conversion error case above.
                 # So this 'elif error_occurred' might primarily catch get_info errors or download loop errors
                 # where some files *might* exist. Let's keep it for inspection.
                 print(f"发生错误，临时文件保留在: {temp_dir} 以供检查。")
            # If the error *was* a PDF conversion failure, the specific except block already handled it by raising
            # and the folder is implicitly kept because conversion_successful is False.

        # --- Always Re-enable Button and Reset Progress ---
        root.after(0, download_button.config, {'state': tk.NORMAL})
        root.after(1500, progress_var.set, 0)
        if not error_occurred and conversion_successful:
             root.after(5000, status_label.config, {'text': '准备就绪'})
        else:
            # Keep error status longer or change to specific message
            root.after(5000, status_label.config, {'text': '操作结束（有错误或警告）'})


# --- Tkinter GUI Setup (create_gui function remains the same) ---
def create_gui():
    root = tk.Tk()
    root.title("教材下载器 (Tkinter版)")
    # ... (rest of the GUI setup code is identical to the previous version) ...
    # --- Variables ---
    url_var = tk.StringVar()
    save_path_var = tk.StringVar()
    progress_var = tk.IntVar()
    status_var = tk.StringVar(value="准备就绪")

    # --- Widgets ---
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)

    ttk.Label(main_frame, text="教材URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    url_entry = ttk.Entry(main_frame, textvariable=url_var, width=50)
    url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

    ttk.Label(main_frame, text="另存为:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    save_path_entry = ttk.Entry(main_frame, textvariable=save_path_var, width=40, state='readonly')
    save_path_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    browse_button = ttk.Button(main_frame, text="浏览...", command=lambda: select_save_path(url_var, save_path_var)) # Pass url_var
    browse_button.grid(row=1, column=2, sticky=tk.E, padx=5, pady=5)

    progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate', variable=progress_var)
    progress_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=10)

    status_label = ttk.Label(main_frame, textvariable=status_var, anchor=tk.W)
    status_label.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2)

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=4, column=0, columnspan=3, pady=10)

    download_button = ttk.Button(button_frame, text="下载并转换为PDF",
                                command=lambda: start_download(root, url_var, save_path_var, progress_var, download_button, status_label))
    download_button.pack(side=tk.LEFT, padx=10)

    exit_button = ttk.Button(button_frame, text="退出", command=root.quit)
    exit_button.pack(side=tk.LEFT, padx=10)

    # --- GUI Helper Functions ---
    def select_save_path(url_var, path_var): # Accept url_var
        suggested_name = "downloaded_textbook.pdf"
        # Try to get title *without* blocking the GUI for too long. Maybe fetch info async later?
        # For now, keep it simple: Use a default or maybe parse URL path crudely.
        try:
             current_url = url_var.get()
             if current_url:
                 # Quick, potentially inaccurate parse from URL path for suggestion
                 path_part = urlparse(current_url).path.strip('/').split('/')
                 if len(path_part) > 0 and path_part[-1]: # Use last part if exists
                     suggested_name = f"{re.sub(r'[\\/*?:\"<>|]', '_', path_part[-1])}.pdf"
                 elif len(path_part) > 0 and path_part[0]: # Use first part if last is empty
                      suggested_name = f"{re.sub(r'[\\/*?:\"<>|]', '_', path_part[0])}.pdf"

                 # The previous attempt to call get_textbook_info here could block the GUI. Avoid it.
                 # title, _, _ = get_textbook_info(current_url) ... (Removed)
        except Exception as e:
            print(f"自动建议文件名时出错: {e}") # Log error, don't bother user

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")],
            initialfile=suggested_name,
            title="选择PDF保存位置"
        )
        if file_path:
            # Ensure it ends with .pdf
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            path_var.set(file_path)


    def start_download(root, url_var, save_path_var, progress_var, download_button, status_label):
        url = url_var.get()
        save_path = save_path_var.get()

        if not url or not save_path:
            messagebox.showwarning("输入缺失", "请输入教材URL并选择保存路径。")
            return

        # Path already ensured to end with .pdf by select_save_path if selected via dialog
        # If manually entered, this check is still useful, but we'll rely on the dialog logic primarily
        if not save_path.lower().endswith('.pdf'):
             save_path += '.pdf'
             save_path_var.set(save_path) # Update display

        download_button.config(state=tk.DISABLED)
        progress_var.set(0)
        status_label.config(text="准备开始下载...")

        thread = threading.Thread(target=download_textbook_thread,
                                  args=(root, url, save_path, progress_var, download_button, status_label),
                                  daemon=True)
        thread.start()

    url_entry.focus_set()
    root.mainloop()


# --- Main Execution ---
if __name__ == "__main__":
    create_gui()