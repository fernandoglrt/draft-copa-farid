from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Se a pessoa acessar só "localhost:8000", redireciona para o login
    path('', lambda request: redirect('login', permanent=False)),

    # Telas de Login e Logout
    path('login/', auth_views.LoginView.as_view(template_name='draftapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Rotas da Sala do Draft
    path('draft/<int:draft_id>/', views.draft_room, name='draft_room'),
    path('draft/<int:draft_id>/scout/', views.scout_players, name='scout_players'),
]