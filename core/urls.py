from django.contrib import admin
from django.urls import path, include
from draftapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Puxa todas as rotas do nosso App principal
    path('', include('draftapp.urls')),
    path('draft/<int:draft_id>/teams/', views.teams_view, name='teams_view'),
]

