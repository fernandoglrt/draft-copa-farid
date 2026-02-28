import os
import django
import pandas as pd
from pathlib import Path

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from draftapp.models import Player, FifaVersion


def import_data():
    # PEGA A PASTA ONDE O SCRIPT ESTÁ (RAIZ DO PROJETO)
    BASE_DIR = Path(__file__).resolve().parent
    file_path = BASE_DIR / "base_jogadores.xlsx"

    print(f"⏳ Localizando arquivo em: {file_path}")

    if not file_path.exists():
        print(f"❌ ERRO: O arquivo 'base_jogadores.xlsx' não está na pasta {BASE_DIR}")
        return

    try:
        df = pd.read_excel(file_path)
        df = df.fillna(0)
        # Padroniza nomes das colunas para evitar erro de maiúscula/minúscula
        df.columns = [str(c).strip().lower() for c in df.columns]
    except Exception as e:
        print(f"❌ Erro ao ler o Excel: {e}")
        return

    version_name = 'FIFA 14'
    version, _ = FifaVersion.objects.get_or_create(name=version_name)

    # Limpa dados antigos da versão para evitar duplicidade
    Player.objects.filter(version=version).delete()

    players_to_create = []

    print("🚀 Mapeando jogadores e corrigindo atributos...")
    for index, row in df.iterrows():
        # BUSCA INTELIGENTE PELO NOME DA COLUNA (Evita o bug dos valores errados)
        player = Player(
            version=version,
            name=str(row.get('name', row.get('player_name', 'Desconhecido'))),
            position=str(row.get('best_position', row.get('position', 'NA'))),
            overall=int(row.get('overall', row.get('ovr', 0))),
            pace=int(row.get('pace', row.get('pac', 0))),
            shooting=int(row.get('shooting', row.get('sho', 0))),
            passing=int(row.get('passing', row.get('pas', 0))),
            dribbling=int(row.get('dribbling', row.get('dri', 0))),
            defending=int(row.get('defending', row.get('def', 0))),
            physical=int(row.get('physical', row.get('phy', 0)))
        )
        players_to_create.append(player)

    Player.objects.bulk_create(players_to_create, batch_size=1000)
    print(f"🏆 SUCESSO! {len(players_to_create)} jogadores importados corretamente!")


if __name__ == '__main__':
    import_data()