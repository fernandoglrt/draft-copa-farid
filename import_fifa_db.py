import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from draftapp.models import Player, FifaVersion


def import_data(file_path, version_name):
    print(f"⏳ Lendo o arquivo Excel: {file_path}...")

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo: {e}")
        return

    df = df.fillna(0)

    # Padroniza as colunas da sua planilha (tira espaços e deixa minúsculo)
    df.columns = [str(c).strip().lower() for c in df.columns]

    print("\n📊 COLUNAS DETECTADAS NA SUA PLANILHA:")
    print(list(df.columns))
    print("-" * 50)

    version, _ = FifaVersion.objects.get_or_create(name=version_name)

    print("🚀 Gerando jogadores na memória e corrigindo atributos...")
    players_to_create = []

    def safe_int(val):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    for index, row in df.iterrows():
        # Busca inteligente: Ele procura pela coluna 'name', se não achar tenta 'nome', etc.
        name = str(row.get('name', row.get('nome', row.get('player', 'Desconhecido'))))

        # Procura a posição
        position = str(row.get('best_position', row.get('position', row.get('team_position', 'NA'))))

        # Procura os atributos
        overall = safe_int(row.get('overall', row.get('ovr', 0)))
        pace = safe_int(row.get('pace', row.get('pac', 0)))
        shooting = safe_int(row.get('shooting', row.get('sho', 0)))
        passing = safe_int(row.get('passing', row.get('pas', 0)))
        dribbling = safe_int(row.get('dribbling', row.get('dri', 0)))
        defending = safe_int(row.get('defending', row.get('def', 0)))
        physical = safe_int(row.get('physical', row.get('phy', 0)))

        player = Player(
            version=version,
            name=name,
            position=position,
            overall=overall,
            pace=pace,
            shooting=shooting,
            passing=passing,
            dribbling=dribbling,
            defending=defending,
            physical=physical
        )
        players_to_create.append(player)

    print("💾 Gravando no banco de dados de uma só vez (Bulk Create)...")
    Player.objects.bulk_create(players_to_create, batch_size=1000)

    print(f"🏆 SUCESSO! {len(players_to_create)} jogadores importados com os valores REAIS!")


if __name__ == '__main__':
    ARQUIVO_EXCEL = r"C:\Users\ferna\OneDrive\Documentos\base_jogadores.xlsx"
    VERSAO_DO_GAME = 'FIFA 14'

    print("🧹 Deletando os jogadores bugados do banco de dados...")
    Player.objects.filter(version__name=VERSAO_DO_GAME).delete()

    import_data(ARQUIVO_EXCEL, VERSAO_DO_GAME)