from .permissions import is_admin_user
from .site_config import load_site_config


def welfare_permissions(request):
    return {
        'is_welfare_admin': is_admin_user(getattr(request, 'user', None)),
    }


def welfare_site_info(request):
    config = load_site_config()
    owner = config.get('copyright_owner', '조세진')
    year = config.get('copyright_year', '2026')
    return {
        'organization_name': config.get('organization_name', '학과(부)명 학생회'),
        'welfare_contact_email': config.get('contact_email', 'threetrue03@gmail.com'),
        'welfare_instagram': config.get('instagram', '추후 공개 예정'),
        'welfare_copyright': f'© {year} {owner}. All rights reserved.',
        'welfare_license_notice': '본 프로그램의 저작권은 조세진에게 있습니다. 무단 복제, 배포, 수정, 재판매를 금지합니다.',
    }
