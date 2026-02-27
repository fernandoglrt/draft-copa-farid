import os
import django

# Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from draftapp.models import Draft, DraftOrder, FifaVersion


def setup_copa_farid():
    # =====================================================================
    # Lista atualizada com os 16 participantes da Copa Farid.
    # Os nomes estão formatados em letras minúsculas e sem espaços para
    # facilitar o login da galera.
    # =====================================================================
    nomes_dos_presidentes = [
        "thigo",
        "xande",
        "tuku",
        "lamba",
        "bonomi",
        "diego",
        "caio",
        "leo_reis",
        "enzo",
        "lopinho",  # Referente ao Lopinho (Rick)
        "felk",
        "nestor",
        "mello",
        "leo_fat",
        "fernando",
        "luis"
    ]

    senha_padrao = "copafarid123"  # Senha inicial para todos eles acessarem

    print("👑 Criando os Presidentes da Copa Farid (16 participantes)...")
    usuarios = []

    for nome in nomes_dos_presidentes:
        # get_or_create evita duplicar caso o usuário já exista
        user, created = User.objects.get_or_create(username=nome)
        if created:
            user.set_password(senha_padrao)
            user.save()
            print(f"  -> Usuário '{nome}' criado com sucesso.")
        else:
            print(f"  -> Usuário '{nome}' já existia no banco.")
        usuarios.append(user)

    print("\n🏆 Configurando a Sala do Draft...")
    version, _ = FifaVersion.objects.get_or_create(name='FIFA 14')

    draft, _ = Draft.objects.get_or_create(
        name='Draft Copa Farid - 1ª Edição',
        version=version
    )

    print("\n📋 Definindo a Ordem de Escolha Oficial...")
    DraftOrder.objects.filter(draft=draft).delete()

    for index, user in enumerate(usuarios):
        DraftOrder.objects.create(draft=draft, president=user, pick_order=index + 1)
        print(f"  -> Pick #{index + 1}: {user.username.upper()}")

    print("\n✅ TUDO PRONTO! A mesa do Draft está posta para os 16 presidentes.")
    print(f"🔑 A senha padrão da galera é: {senha_padrao}")


if __name__ == '__main__':
    setup_copa_farid()