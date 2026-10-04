"""
URL configuration for arohan_mocktest project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Customize admin headers
admin.site.site_header = "Arohan Academy English School"
admin.site.site_title = "Arohan Academy Admin"
admin.site.index_title = "Mock Test Examination Management Center"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
