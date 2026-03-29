import os

FILE_PATH = r"c:\mini-project\frontend\dashboard.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# CSS Color replacements
# Background
content = content.replace("background-color: #07090f;", "background-color: #f8fafc;")
# Cards
content = content.replace("background: #0e1220", "background: #ffffff")
# Borders
content = content.replace("rgba(255,255,255,0.07)", "rgba(0,0,0,0.06)")
content = content.replace("rgba(255,255,255,0.10)", "rgba(0,0,0,0.08)")
# Light transparent backgrounds matching white
content = content.replace("rgba(255,255,255,0.06)", "rgba(0,0,0,0.05)")

# Text Colors
content = content.replace("color: #e2e8f0", "color: #0f172a") # Primary text
content = content.replace("color: #64748b", "color: #64748b") # Keep muted same
content = content.replace("color:#e2e8f0", "color:#0f172a")
content = content.replace("color:#64748b", "color:#64748b")

# Metric container
content = content.replace("border-radius: 14px; padding: 16px 20px;", "border-radius: 14px; padding: 16px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);")

# Plotly Themes
content = content.replace('template="plotly_dark"', 'template="plotly_white"')
content = content.replace('paper_bgcolor="rgba(0,0,0,0)"', 'paper_bgcolor="rgba(0,0,0,0)"')
content = content.replace('plot_bgcolor="rgba(0,0,0,0)"', 'plot_bgcolor="rgba(0,0,0,0)"')
content = content.replace('font_color="#e2e8f0"', 'font_color="#0f172a"')
content = content.replace('font_color="#64748b"', 'font_color="#475569"')

# Grid colors
content = content.replace('gridcolor="rgba(255,255,255,0.06)"', 'gridcolor="rgba(0,0,0,0.05)"')

# Scenario Buttons specifically
content = content.replace('background: #0e1220 !important;', 'background: #f1f5f9 !important;')
content = content.replace('border-color: #3b82f6 !important;', 'border-color: #3b82f6 !important; background: #eff6ff !important;')

# Title text color fix
content = content.replace("<style>", "<style>\n    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #0f172a !important; }\n    div[data-testid=\"stMarkdownContainer\"] { color: #0f172a !important; }")

# Write back
with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Theme updated to White & Silver!")
