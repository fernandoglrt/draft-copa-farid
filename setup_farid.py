import os

app_name = 'draftapp'
dirs = [
    f'{app_name}/templates/{app_name}',
    f'{app_name}/static/css',
    f'{app_name}/static/js',
]

files = [
    f'{app_name}/models.py',
    f'{app_name}/views.py',
    f'{app_name}/urls.py',
    f'{app_name}/templates/base.html',
    f'{app_name}/templates/{app_name}/draft_room.html',
    f'{app_name}/templates/{app_name}/scout.html',
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

for f in files:
    with open(f, 'w', encoding='utf-8') as file:
        file.write("")

print("🏆 Estrutura do 'Draft Online Copa Farid' criada! Copie os códigos abaixo.")