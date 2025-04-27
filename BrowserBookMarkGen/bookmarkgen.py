#书签生成器  书签生成网址导航
from bs4 import BeautifulSoup

def generate_navigation_sections(input_html):
    soup = BeautifulSoup(input_html, "html.parser")
    navigation_sections = ""
    # 遍历所有 H3 标签（代表分类名称）
    for h3 in soup.find_all("h3"):
        category = h3.get_text(strip=True)
        # 获取该分类对应的链接列表，通常位于后续的 <DL> 标签中
        dl = h3.find_next_sibling("dl")
        if not dl:
            continue
        links_html = ""
        # 遍历 <DL> 中的所有 <A> 标签
        for a in dl.find_all("a"):
            href = a.get("href")
            text = a.get_text(strip=True)
            links_html += f'    <a href="{href}" class="link-item" target="_blank">{text}</a>\n'
        # 生成当前分类的 HTML 部分
        section = (
            f'<div class="category" data-category="{category}">\n'
            f'  <h2>{category}</h2>\n'
            f'  <div class="links">\n{links_html}  </div>\n'
            f'</div>\n'
        )
        navigation_sections += section
    return navigation_sections

def generate_full_html(navigation_sections):
    # HTML 模板，包含动态 CSS 效果和搜索框功能
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>网址导航</title>
  <style>
    /* 基础样式 */
    body {{
      margin: 0;
      padding: 20px;
      font-family: "微软雅黑", Arial, sans-serif;
      background: #f7f9fc;
      color: #333;
    }}
    h1 {{
      text-align: center;
      margin-bottom: 20px;
      font-size: 36px;
      color: #007BFF;
    }}
    /* 搜索框样式 */
    .search-box {{
      width: 100%;
      max-width: 500px;
      margin: 0 auto 40px;
    }}
    .search-box input {{
      width: 100%;
      padding: 12px 20px;
      font-size: 16px;
      border: 2px solid #ccc;
      border-radius: 30px;
      outline: none;
      transition: border-color 0.3s;
    }}
    .search-box input:focus {{
      border-color: #007BFF;
    }}
    /* 分类样式 */
    .category {{
      margin-bottom: 40px;
    }}
    .category h2 {{
      background: linear-gradient(90deg, #007BFF, #00d4ff);
      color: #fff;
      padding: 10px 15px;
      border-radius: 5px;
      margin: 0 0 15px;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 15px;
    }}
    .link-item {{
      display: inline-block;
      background: #fff;
      padding: 10px 15px;
      border-radius: 5px;
      text-decoration: none;
      color: #333;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      transition: transform 0.3s, box-shadow 0.3s;
      animation: fadeIn 0.5s ease-in;
    }}
    .link-item:hover {{
      transform: translateY(-5px) scale(1.02);
      box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }}
    @keyframes fadeIn {{
      from {{
        opacity: 0;
        transform: translateY(10px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}
  </style>
</head>
<body>
  <h1>网址导航</h1>
  <div class="search-box">
    <input type="text" id="search" placeholder="搜索网址...">
  </div>
  <div id="navigation">
{navigation_sections}
  </div>
  <script>
    // 搜索功能：实时筛选链接（同时匹配名称和 URL）
    const searchInput = document.getElementById('search');
    searchInput.addEventListener('keyup', function() {{
      const query = this.value.toLowerCase();
      const linkItems = document.querySelectorAll('.link-item');
      linkItems.forEach(item => {{
        if(item.textContent.toLowerCase().includes(query) || item.href.toLowerCase().includes(query)) {{
          item.style.display = 'inline-block';
        }} else {{
          item.style.display = 'none';
        }}
      }});
    }});
  </script>
</body>
</html>
'''
    return html_template

if __name__ == "__main__":
    input_filename = "bookmarks_2025_3_16.html"
    output_filename = "navigation_output.html"

    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            input_html = f.read()
    except FileNotFoundError:
        print(f"文件 {input_filename} 未找到，请确保该文件在当前目录下。")
        exit(1)

    # 解析书签文件并生成各分类下的导航部分
    nav_sections = generate_navigation_sections(input_html)
    # 生成完整的 HTML 页面
    full_html = generate_full_html(nav_sections)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"导航页面已生成并保存到 {output_filename} 文件中。")
