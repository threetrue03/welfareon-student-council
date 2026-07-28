# -*- coding: utf-8 -*-
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .site_config import load_site_config


class ShiftAutoStartMiddleware:
    """로그인 유지 상태로 다시 접속해도 열린 근무 기록이 없으면 출근 기록을 생성한다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            from .models import ShiftRecord
            if not ShiftRecord.objects.filter(user=user, ended_at__isnull=True).exists():
                ShiftRecord.objects.create(user=user)
                try:
                    from dashboard.google_sheets import schedule_google_sheet_sync
                    schedule_google_sheet_sync('근무 시작')
                except Exception:
                    pass
        return self.get_response(request)


class CleanLoginRedirectMiddleware:
    """주소창에 /login/?next=/... 형태가 남지 않게 정리한다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in {'/login/', '/accounts/login/'} and request.GET.get('next'):
            return redirect('/login/')
        return self.get_response(request)


class SiteBrandingMiddleware(MiddlewareMixin):
    """하드코딩된 단체명 교체, 저작권/문의 고지, 비밀번호 한글 입력 차단 스크립트 주입."""

    def process_response(self, request, response):
        content_type = response.get('Content-Type', '')
        if not content_type.startswith('text/html'):
            return response
        if not hasattr(response, 'content'):
            return response
        try:
            html = response.content.decode(response.charset or 'utf-8')
        except Exception:
            return response

        config = load_site_config()
        organization = config.get('organization_name', '학과(부)명 학생회')
        contact = config.get('contact_email', 'threetrue03@gmail.com')
        instagram = config.get('instagram', '추후 공개 예정')
        owner = config.get('copyright_owner', '조세진')
        year = config.get('copyright_year', '2026')

        replacements = {
            'AI소프트웨어학부 학생회 학생회': organization,
            'AI소프트웨어학부 학생회': organization,
            '복지온 운영 단체': organization,
            'A:NSWER': organization,
        }
        for source, target in replacements.items():
            html = html.replace(source, target)

        html = html.replace('/accounts/login/?next=/', '/login/')
        html = html.replace('/accounts/login/', '/login/')

        inject = f'''
<script>
(function() {{
  function hasHangul(value) {{ return /[가-힣ㄱ-ㅎㅏ-ㅣ]/.test(value || ''); }}
  function cleanPassword(value) {{ return (value || '').split('').filter(function(ch) {{ return /^[!-~]$/.test(ch) && !hasHangul(ch); }}).join(''); }}
  function bindPassword(input) {{
    if (!input || input.dataset.welfarePasswordGuard === '1') return;
    input.dataset.welfarePasswordGuard = '1';
    input.setAttribute('inputmode', 'latin');
    input.setAttribute('autocomplete', input.getAttribute('autocomplete') || 'current-password');
    input.addEventListener('beforeinput', function(event) {{
      if (hasHangul(event.data)) event.preventDefault();
    }});
    input.addEventListener('input', function() {{
      var cleaned = cleanPassword(input.value);
      if (input.value !== cleaned) input.value = cleaned;
    }});
  }}
  function apply() {{ document.querySelectorAll('input[type="password"]').forEach(bindPassword); }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
  new MutationObserver(apply).observe(document.documentElement, {{childList: true, subtree: true}});
}})();
</script>
<div style="position:fixed;left:18px;bottom:8px;z-index:1;font-size:11px;color:#94a3b8;pointer-events:none;">
  © {year} {owner}. All rights reserved. · 문의: {contact} · Instagram: {instagram}
</div>
'''
        if '</body>' in html:
            html = html.replace('</body>', inject + '</body>')
        response.content = html.encode(response.charset or 'utf-8')
        response['Content-Length'] = str(len(response.content))
        return response
