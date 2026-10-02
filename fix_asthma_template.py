with open('templates/asthma_result.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_metrics = '''        <div class="metric-box">
          <div class="metric-title">Peak Flow</div>
          <div class="metric-value">{{ result.input_data.Peak_Expiratory_Flow | int }} L/min</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">FeNO Level</div>
          <div class="metric-value">{{ result.input_data.FeNO_Level | int }} ppb</div>
        </div>'''

new_metrics = ''

content = content.replace(old_metrics, new_metrics)

with open('templates/asthma_result.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed missing metrics from asthma_result.html")
