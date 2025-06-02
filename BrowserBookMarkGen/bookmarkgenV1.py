# 酷炫书签生成器 - 现代化网址导航
from bs4 import BeautifulSoup
import json
import base64

def generate_navigation_sections(input_html):
    soup = BeautifulSoup(input_html, "html.parser")
    categories_data = []
    
    # 遍历所有 H3 标签（代表分类名称）
    for h3 in soup.find_all("h3"):
        category = h3.get_text(strip=True)
        # 获取该分类对应的链接列表
        dl = h3.find_next_sibling("dl")
        if not dl:
            continue
            
        links = []
        # 遍历 <DL> 中的所有 <A> 标签
        for a in dl.find_all("a"):
            href = a.get("href")
            text = a.get_text(strip=True)
            if href and text:
                # 提取域名用于图标
                domain = extract_domain(href)
                links.append({
                    'url': href,
                    'title': text,
                    'domain': domain
                })
        
        if links:
            categories_data.append({
                'name': category,
                'links': links
            })
    
    return categories_data

def extract_domain(url):
    """提取域名用于生成图标"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除 www. 前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return 'default'

def generate_full_html(categories_data):
    # 将数据转换为 JSON 字符串，用于 JavaScript
    categories_json = json.dumps(categories_data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 酷炫网址导航</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            overflow-x: hidden;
        }}

        /* 动态背景粒子 */
        .particles {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
        }}

        .particle {{
            position: absolute;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 20s infinite linear;
        }}

        @keyframes float {{
            0% {{
                transform: translateY(100vh) rotate(0deg);
                opacity: 0;
            }}
            10% {{
                opacity: 1;
            }}
            90% {{
                opacity: 1;
            }}
            100% {{
                transform: translateY(-100px) rotate(360deg);
                opacity: 0;
            }}
        }}

        .container {{
            position: relative;
            z-index: 10;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* 头部样式 */
        .header {{
            text-align: center;
            margin-bottom: 40px;
            animation: slideDown 1s ease-out;
        }}

        .header h1 {{
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 800;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 3s ease-in-out infinite;
            margin-bottom: 10px;
            text-shadow: 0 0 30px rgba(255, 255, 255, 0.3);
        }}

        .header .subtitle {{
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 300;
        }}

        @keyframes gradientShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}

        @keyframes slideDown {{
            from {{
                opacity: 0;
                transform: translateY(-50px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        /* 搜索框样式 */
        .search-container {{
            position: relative;
            max-width: 600px;
            margin: 0 auto 40px;
            animation: fadeInUp 1s ease-out 0.3s both;
        }}

        .search-box {{
            position: relative;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 50px;
            padding: 5px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}

        .search-input {{
            width: 100%;
            padding: 15px 25px 15px 50px;
            font-size: 16px;
            border: none;
            background: transparent;
            color: white;
            outline: none;
            border-radius: 50px;
        }}

        .search-input::placeholder {{
            color: rgba(255, 255, 255, 0.6);
        }}

        .search-icon {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: rgba(255, 255, 255, 0.6);
            font-size: 18px;
        }}

        /* 统计信息 */
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 40px;
            animation: fadeInUp 1s ease-out 0.5s both;
        }}

        .stat-item {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            padding: 15px 25px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #4ecdc4;
        }}

        .stat-label {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }}

        /* 分类网格 */
        .categories-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            animation: fadeInUp 1s ease-out 0.7s both;
        }}

        .category-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 25px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .category-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            transition: left 0.5s;
        }}

        .category-card:hover::before {{
            left: 100%;
        }}

        .category-card:hover {{
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.4);
        }}

        .category-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}

        .category-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
            margin-right: 15px;
        }}

        .category-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: white;
            flex: 1;
        }}

        .category-count {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }}

        .links-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
        }}

        .link-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            text-decoration: none;
            color: white;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }}

        .link-item:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        }}

        .link-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            font-size: 16px;
        }}

        .link-title {{
            font-size: 0.85rem;
            text-align: center;
            line-height: 1.3;
            font-weight: 500;
        }}

        /* 响应式设计 */
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            .stats {{
                flex-direction: column;
                align-items: center;
                gap: 15px;
            }}
            
            .categories-grid {{
                grid-template-columns: 1fr;
            }}
            
            .links-grid {{
                grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            }}
        }}

        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        /* 隐藏元素 */
        .hidden {{
            display: none !important;
        }}

        /* 空状态 */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: rgba(255, 255, 255, 0.6);
        }}

        .empty-state i {{
            font-size: 4rem;
            margin-bottom: 20px;
            opacity: 0.5;
        }}
    </style>
</head>
<body>
    <div class="particles" id="particles"></div>
    
    <div class="container">
        <header class="header">
            <h1>🚀 酷炫导航</h1>
            <p class="subtitle">精心整理的网址收藏夹</p>
        </header>

        <div class="search-container">
            <div class="search-box">
                <i class="fas fa-search search-icon"></i>
                <input type="text" class="search-input" id="searchInput" placeholder="搜索网站名称或网址...">
            </div>
        </div>

        <div class="stats" id="stats">
            <div class="stat-item">
                <div class="stat-number" id="totalCategories">0</div>
                <div class="stat-label">分类</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="totalLinks">0</div>
                <div class="stat-label">网站</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="visibleLinks">0</div>
                <div class="stat-label">显示</div>
            </div>
        </div>

        <div class="categories-grid" id="categoriesContainer">
            <!-- 动态生成内容 -->
        </div>

        <div class="empty-state hidden" id="emptyState">
            <i class="fas fa-search"></i>
            <h3>未找到相关内容</h3>
            <p>尝试使用其他关键词搜索</p>
        </div>
    </div>

    <script>
        // 网站数据
        const categoriesData = {categories_json};

        // 图标映射
        const iconMap = {{
            'github': 'fab fa-github',
            'google': 'fab fa-google',
            'youtube': 'fab fa-youtube',
            'facebook': 'fab fa-facebook',
            'twitter': 'fab fa-twitter',
            'instagram': 'fab fa-instagram',
            'linkedin': 'fab fa-linkedin',
            'stackoverflow': 'fab fa-stack-overflow',
            'reddit': 'fab fa-reddit',
            'medium': 'fab fa-medium',
            'dev.to': 'fab fa-dev',
            'codepen': 'fab fa-codepen',
            'npm': 'fab fa-npm',
            'docker': 'fab fa-docker',
            'aws': 'fab fa-aws',
            'microsoft': 'fab fa-microsoft',
            'apple': 'fab fa-apple',
            'android': 'fab fa-android',
            'chrome': 'fab fa-chrome',
            'firefox': 'fab fa-firefox',
            'safari': 'fab fa-safari',
            'edge': 'fab fa-edge',
            'discord': 'fab fa-discord',
            'slack': 'fab fa-slack',
            'telegram': 'fab fa-telegram',
            'whatsapp': 'fab fa-whatsapp',
            'skype': 'fab fa-skype',
            'zoom': 'fas fa-video',
            'netflix': 'fas fa-film',
            'spotify': 'fab fa-spotify',
            'steam': 'fab fa-steam',
            'twitch': 'fab fa-twitch',
            'paypal': 'fab fa-paypal',
            'stripe': 'fab fa-stripe',
            'bitcoin': 'fab fa-bitcoin',
            'ethereum': 'fab fa-ethereum',
            'amazon': 'fab fa-amazon',
            'ebay': 'fab fa-ebay',
            'etsy': 'fab fa-etsy',
            'shopify': 'fab fa-shopify',
            'wordpress': 'fab fa-wordpress',
            'blogger': 'fab fa-blogger',
            'tumblr': 'fab fa-tumblr',
            'pinterest': 'fab fa-pinterest',
            'dribbble': 'fab fa-dribbble',
            'behance': 'fab fa-behance',
            'figma': 'fab fa-figma',
            'adobe': 'fab fa-adobe',
            'canva': 'fas fa-palette',
            'trello': 'fab fa-trello',
            'notion': 'fas fa-sticky-note',
            'dropbox': 'fab fa-dropbox',
            'onedrive': 'fab fa-microsoft',
            'drive': 'fab fa-google-drive',
            'icloud': 'fab fa-icloud'
        }};

        // 分类图标映射
        const categoryIcons = {{
            '搜索引擎': 'fas fa-search',
            '社交媒体': 'fas fa-users',
            '开发工具': 'fas fa-code',
            '设计工具': 'fas fa-palette',
            '学习资源': 'fas fa-graduation-cap',
            '娱乐': 'fas fa-gamepad',
            '购物': 'fas fa-shopping-cart',
            '新闻资讯': 'fas fa-newspaper',
            '工具软件': 'fas fa-tools',
            '云服务': 'fas fa-cloud',
            '金融理财': 'fas fa-coins',
            '视频音乐': 'fas fa-play-circle',
            '办公协作': 'fas fa-briefcase',
            '技术博客': 'fas fa-blog',
            '在线教育': 'fas fa-chalkboard-teacher',
            '图片素材': 'fas fa-images',
            '开源项目': 'fab fa-github-alt',
            '文档工具': 'fas fa-file-alt',
            '通讯工具': 'fas fa-comments',
            '数据分析': 'fas fa-chart-bar'
        }};

        // 获取网站图标
        function getWebsiteIcon(domain) {{
            const lowerDomain = domain.toLowerCase();
            for (const [key, icon] of Object.entries(iconMap)) {{
                if (lowerDomain.includes(key)) {{
                    return icon;
                }}
            }}
            return 'fas fa-globe';
        }}

        // 获取分类图标
        function getCategoryIcon(categoryName) {{
            for (const [key, icon] of Object.entries(categoryIcons)) {{
                if (categoryName.includes(key)) {{
                    return icon;
                }}
            }}
            return 'fas fa-folder';
        }}

        // 渲染分类
        function renderCategories(categories = categoriesData) {{
            const container = document.getElementById('categoriesContainer');
            const emptyState = document.getElementById('emptyState');
            
            if (categories.length === 0) {{
                container.innerHTML = '';
                emptyState.classList.remove('hidden');
                return;
            }}
            
            emptyState.classList.add('hidden');
            
            container.innerHTML = categories.map(category => `
                <div class="category-card" data-category="${{category.name}}">
                    <div class="category-header">
                        <div class="category-icon">
                            <i class="${{getCategoryIcon(category.name)}}"></i>
                        </div>
                        <h3 class="category-title">${{category.name}}</h3>
                        <span class="category-count">${{category.links.length}}</span>
                    </div>
                    <div class="links-grid">
                        ${{category.links.map(link => `
                            <a href="${{link.url}}" class="link-item" target="_blank" 
                               data-title="${{link.title.toLowerCase()}}" 
                               data-url="${{link.url.toLowerCase()}}">
                                <div class="link-icon">
                                    <i class="${{getWebsiteIcon(link.domain)}}"></i>
                                </div>
                                <span class="link-title">${{link.title}}</span>
                            </a>
                        `).join('')}}
                    </div>
                </div>
            `).join('');
        }}

        // 更新统计信息
        function updateStats(categories = categoriesData) {{
            const totalLinks = categories.reduce((sum, cat) => sum + cat.links.length, 0);
            const visibleLinks = document.querySelectorAll('.link-item:not(.hidden)').length;
            
            document.getElementById('totalCategories').textContent = categories.length;
            document.getElementById('totalLinks').textContent = totalLinks;
            document.getElementById('visibleLinks').textContent = visibleLinks;
        }}

        // 搜索功能
        function setupSearch() {{
            const searchInput = document.getElementById('searchInput');
            let searchTimeout;
            
            searchInput.addEventListener('input', (e) => {{
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {{
                    const query = e.target.value.toLowerCase().trim();
                    filterContent(query);
                }}, 300);
            }});
        }}

        // 过滤内容
        function filterContent(query) {{
            if (!query) {{
                // 显示所有内容
                document.querySelectorAll('.category-card').forEach(card => {{
                    card.classList.remove('hidden');
                    card.querySelectorAll('.link-item').forEach(link => {{
                        link.classList.remove('hidden');
                    }});
                }});
                updateStats();
                return;
            }}

            const categories = document.querySelectorAll('.category-card');
            let hasVisibleContent = false;

            categories.forEach(categoryCard => {{
                const links = categoryCard.querySelectorAll('.link-item');
                let hasVisibleLinks = false;

                links.forEach(link => {{
                    const title = link.dataset.title;
                    const url = link.dataset.url;
                    const categoryName = categoryCard.dataset.category.toLowerCase();

                    if (title.includes(query) || url.includes(query) || categoryName.includes(query)) {{
                        link.classList.remove('hidden');
                        hasVisibleLinks = true;
                        hasVisibleContent = true;
                    }} else {{
                        link.classList.add('hidden');
                    }}
                }});

                if (hasVisibleLinks) {{
                    categoryCard.classList.remove('hidden');
                }} else {{
                    categoryCard.classList.add('hidden');
                }}
            }});

            // 显示空状态
            const emptyState = document.getElementById('emptyState');
            if (hasVisibleContent) {{
                emptyState.classList.add('hidden');
            }} else {{
                emptyState.classList.remove('hidden');
            }}

            updateStats();
        }}

        // 创建粒子动画
        function createParticles() {{
            const particlesContainer = document.getElementById('particles');
            const particleCount = 50;

            for (let i = 0; i < particleCount; i++) {{
                const particle = document.createElement('div');
                particle.className = 'particle';
                
                const size = Math.random() * 4 + 2;
                const delay = Math.random() * 20;
                const duration = Math.random() * 10 + 15;
                
                particle.style.left = Math.random() * 100 + '%';
                particle.style.width = size + 'px';
                particle.style.height = size + 'px';
                particle.style.animationDelay = delay + 's';
                particle.style.animationDuration = duration + 's';
                
                particlesContainer.appendChild(particle);
            }}
        }}

        // 初始化
        document.addEventListener('DOMContentLoaded', () => {{
            renderCategories();
            updateStats();
            setupSearch();
            createParticles();
            
            // 添加入场动画
            setTimeout(() => {{
                document.querySelectorAll('.category-card').forEach((card, index) => {{
                    card.style.animationDelay = (index * 0.1) + 's';
                    card.classList.add('fadeInUp');
                }});
            }}, 1000);
        }});

        // 快捷键支持
        document.addEventListener('keydown', (e) => {{
            if (e.key === '/' && e.target.tagName !== 'INPUT') {{
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }}
            if (e.key === 'Escape') {{
                document.getElementById('searchInput').blur();
                document.getElementById('searchInput').value = '';
                filterContent('');
            }}
        }});
    </script>
</body>
</html>'''
    
    return html_template

def main():
    input_filename = "bookmarks_2025_6_2.html"
    output_filename = "navigation_output.html"

    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            input_html = f.read()
    except FileNotFoundError:
        print(f"❌ 文件 {input_filename} 未找到，请确保该文件在当前目录下。")
        return

    print("🚀 正在解析书签文件...")
    # 解析书签文件并生成各分类下的导航部分
    categories_data = generate_navigation_sections(input_html)
    
    if not categories_data:
        print("⚠️  未找到有效的书签数据")
        return
    
    print(f"📊 发现 {len(categories_data)} 个分类")
    total_links = sum(len(cat['links']) for cat in categories_data)
    print(f"🔗 共 {total_links} 个链接")
    
    print("🎨 生成酷炫导航页面...")
    # 生成完整的 HTML 页面
    full_html = generate_full_html(categories_data)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"✅ 酷炫导航页面已生成！")
    print(f"📁 文件保存位置: {output_filename}")
    print(f"🌟 功能亮点:")
    print(f"   • 炫酷渐变背景和粒子动画")
    print(f"   • 实时搜索过滤")
    print(f"   • 响应式网格布局")
    print(f"   • 网站图标自动识别")
    print(f"   • 悬停动画效果")
    print(f"   • 快捷键支持 (/ 搜索, Esc 清空)")

if __name__ == "__main__":
    main()