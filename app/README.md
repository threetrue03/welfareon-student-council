# 복지 프로그램 - 로그인/회원가입 기본 구현

Django + SQLite 기반의 복지 관리 프로그램 초기 버전입니다.
현재 포함된 기능은 회원가입, 로그인, 로그아웃, 로그인 후 홈 화면입니다.
Django 5.2.14 환경에서 `manage.py check`, `migrate`, `test`를 확인했습니다.

## 실행 방법

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

브라우저에서 접속:

```text
http://127.0.0.1:8000/
```

## 현재 계정 구조

- 이름
- 학번: 로그인 아이디
- 비밀번호: Django 방식으로 암호화 저장
- 권한: worker / admin 확장 가능

## 관리자 계정 생성

```bash
python manage.py createsuperuser
```

관리자 페이지:

```text
http://127.0.0.1:8000/admin/
```
