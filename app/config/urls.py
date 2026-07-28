from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path

from accounts import views as account_views


def health_view(request):
    return JsonResponse({"ok": True, "service": "WelfareON"})


@login_required
def home_view(request):
    return redirect('dashboard:home')


urlpatterns = [
    path('health/', health_view, name='health'),
    path('admin/', admin.site.urls),

    # 주소창 노출 최소화를 위한 짧은 진입 경로. 최종 배포 런처는 내부 WebView로 열어 주소창 자체를 표시하지 않습니다.
    path('login/', account_views.login_view, name='clean_login'),
    path('logout/', account_views.logout_view, name='clean_logout'),

    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('items/', include('items.urls')),
    path('rentals/', include('rentals.urls')),
    path('', home_view, name='home'),
]
