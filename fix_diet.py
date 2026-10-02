import re

with open('templates/diet.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the header using regex
old_header_pattern = r'<h2 class=\"diet-section-title\" id=\"diet-title\">\s*<i class=.bx bx-restaurant.><\/i>\s*<span id=\"diet-disease-name\">Diabetes<\/span>\s*Diet Plan\s*<\/h2>'
new_header = '''<h2 class=\"diet-section-title\" id=\"diet-title\">
          <button onclick=\"hideDiet()\" title=\"Go Back\" style=\"background:var(--color-primary-light);border:none;cursor:pointer;font-size:1.5rem;color:var(--color-primary);margin-right:15px;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:0.3s;\"><i class='bx bx-arrow-back'></i></button>
          <i class='bx bx-restaurant'></i> <span id=\"diet-disease-name\">Diabetes</span> Diet Plan
        </h2>'''

content = re.sub(old_header_pattern, new_header, content)

with open('templates/diet.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications done")
