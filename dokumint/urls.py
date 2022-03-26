from django.urls import path
from dokumint.views import Home,Validate,dashboard,checkMe
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('',Home,name='home'),
    path('validate/',Validate,name='Validate'),
    path('dashboard/<str:id>/',dashboard,name='dashboard'),
    path('generateImg/',checkMe,name='checkMe')
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)