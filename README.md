# WelfareON

학생회 복지물품의 대여, 반납, 재고와 근무 기록을 한곳에서 관리하는 Windows 기반 로컬 운영 시스템입니다.

현재 배포 버전은 **v1.0.17**입니다.

## 주요 기능

- 학생 및 학생회비 납부 상태 관리
- 근무자·관리자 계정과 근무 시간 관리
- 비품 개별 번호 및 소모품 수량 관리
- 물품 대여·반납과 고장·분실 상태 처리
- 연체 횟수에 따른 블랙리스트 자동 적용
- 학생·물품·근무자 XLSX 데이터 가져오기
- 데이터 변경 전 자동 백업 및 수동 전체 백업
- 당일 운영 현황 Google Sheets 동기화
- 라이트 모드와 다크 모드 지원
- Django 서버와 내부 WebView를 제어하는 Windows 런처

## 기술 구성

- Python 3.12
- Django 5
- SQLite
- pywebview
- openpyxl
- Google Sheets API
- Tkinter / PyInstaller

## 프로젝트 구조

```text
.
├─ app/
│  ├─ accounts/       # 로그인, 권한, 근무 기록
│  ├─ dashboard/      # 대시보드, 설정, Google Sheets 연동
│  ├─ items/          # 물품, 카테고리, 학생·근무자 DB 관리
│  ├─ rentals/        # 대여, 반납, 연체 처리
│  ├─ students/       # 학생 및 대여 자격 모델
│  ├─ templates/      # Django 템플릿
│  └─ static/         # CSS와 JavaScript
├─ assets/            # 로고와 런처 아이콘
├─ docs/              # 설치·연동 문서와 XLSX 양식
├─ WelfareOn_Launcher.pyw
└─ build_launcher.bat
```

## 실행 환경

- Windows 10 또는 Windows 11
- Python 3.12.x
- Microsoft Edge WebView2 Runtime
- Google Sheets 연동 시 Google Cloud 서비스 계정

## 런처로 실행

1. 저장소를 내려받거나 릴리스 압축 파일을 해제합니다.
2. Python 3.12가 설치되어 있는지 확인합니다.
3. `build_launcher.bat`을 실행해 런처를 빌드합니다.
4. 생성된 `dist/복지온_Launcher.exe`를 실행합니다.
5. 최초 실행 화면에서 학과(부)와 관리자 계정을 설정합니다.
6. Google Sheets 연동은 필요하지 않으면 건너뛸 수 있습니다.

런처 빌드 과정에서 PyInstaller와 pywebview 등 필요한 패키지를 설치하므로 인터넷 연결이 필요할 수 있습니다.

## Django 개발 서버 실행

```powershell
cd app
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

실행 후 `http://127.0.0.1:8000/`으로 접속합니다.

## 테스트

```powershell
cd app
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

## 데이터 및 보안 주의사항

다음 파일은 운영 데이터 또는 인증정보를 포함할 수 있어 Git에 커밋하지 않습니다.

- `app/db.sqlite3`
- `app/auth/admin.csv`
- `app/auth/google_sheets.json`
- `app/credentials/`
- `app/backups/`
- `launcher_config.json`

서비스 계정 JSON, 실제 학생·근무자 명단, 운영 DB를 공개 저장소나 이슈에 첨부하지 마세요.

## 문서

- `docs/설치가이드.txt`
- `docs/구글시트_연동가이드.txt`
- `docs/업데이트_기록.md`
- `CHANGELOG.md`
- `RELEASE_NOTES_v1.0.17.txt`

## 문의

문의사항은 아래 이메일로 연락해주세요.


`threetrue03@gmail.com`
