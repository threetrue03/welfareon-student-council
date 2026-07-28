# -*- coding: utf-8 -*-
import sys
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.site_config import save_site_config, normalize_organization_name

ADMIN_HEADER = '관리자 학번'


class Command(BaseCommand):
    help = '복지온 최초 실행용 관리자 계정, 단체 정보, auth/admin.csv를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--organization-name', default='', help='학과(부) 명 또는 표시 이름')
        parser.add_argument('--name', required=True, help='관리자 이름')
        parser.add_argument('--student-id', required=True, help='관리자 학번')
        parser.add_argument('--password', default='', help='관리자 비밀번호')
        parser.add_argument('--password-stdin', action='store_true', help='관리자 비밀번호를 표준 입력으로 받습니다.')
        parser.add_argument('--contact-email', default='threetrue03@gmail.com', help='문의 이메일')

    def handle(self, *args, **options):
        organization_name = str(options.get('organization_name') or '').strip()
        name = str(options['name']).strip()
        student_id = str(options['student_id']).strip()
        password = str(options.get('password') or '')
        if options.get('password_stdin'):
            password = sys.stdin.readline().rstrip('\r\n')
        contact_email = str(options.get('contact_email') or 'threetrue03@gmail.com').strip()

        organization_name = normalize_organization_name(organization_name)
        if not name:
            raise CommandError('관리자 이름이 비어 있습니다.')
        if not student_id:
            raise CommandError('관리자 학번이 비어 있습니다.')
        if not password:
            raise CommandError('관리자 비밀번호가 비어 있습니다.')

        save_site_config(
            organization_name=organization_name,
            contact_email=contact_email,
            instagram='추후 공개 예정',
            copyright_owner='조세진',
            copyright_year='2026',
        )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            student_id=student_id,
            defaults={'name': name},
        )
        user.name = name
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        if hasattr(user, 'role'):
            try:
                user.role = 'admin'
            except Exception:
                pass
        if hasattr(user, 'visible_password'):
            try:
                user.visible_password = password
            except Exception:
                pass
        user.set_password(password)
        user.save()

        self._write_admin_csv(student_id)
        self.stdout.write(self.style.SUCCESS(('관리자 계정을 생성했습니다.' if created else '관리자 계정을 갱신했습니다.') + f' ({student_id})'))
        self.stdout.write(self.style.SUCCESS(f'학과(부) 명을 저장했습니다. ({organization_name})'))

    def _write_admin_csv(self, student_id):
        path = Path(settings.BASE_DIR) / 'auth' / 'admin.csv'
        path.parent.mkdir(parents=True, exist_ok=True)

        admin_ids = []
        if path.exists():
            for encoding in ('utf-8-sig', 'cp949'):
                try:
                    lines = path.read_text(encoding=encoding, errors='ignore').splitlines()
                    break
                except Exception:
                    lines = []
            for index, line in enumerate(lines):
                value = line.strip().split(',')[0].strip()
                if not value:
                    continue
                if index == 0 and value in {ADMIN_HEADER, 'student_id', 'admin_student_id'}:
                    continue
                if value not in admin_ids:
                    admin_ids.append(value)
        if student_id not in admin_ids:
            admin_ids.append(student_id)

        content = '\n'.join([ADMIN_HEADER, *admin_ids]) + '\n'
        try:
            path.write_text(content, encoding='utf-8-sig')
        except PermissionError as exc:
            raise CommandError(f'{path} 파일을 수정할 수 없습니다. 엑셀에서 열려 있으면 닫고 다시 실행해주세요.') from exc
