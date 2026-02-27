from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Puxa todas as rotas do nosso App principal
    path('', include('draftapp.urls')),
]

