from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pesquisa_ai.core.urls')),
    
] + static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
