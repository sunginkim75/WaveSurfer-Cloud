import os
import sys

def get_resource_path(relative_path):
    """
    IDE 환경과 PyInstaller EXE 환경 모두에서 리소스 파일의 절대 경로를 반환합니다.
    (V1.3.5) 외부(exe 파일 위치)의 파일을 우선적으로 찾고, 없으면 내장(_MEIPASS)을 참조합니다.
    """
    # 1단계: EXE 파일이 위치한 실제 폴더(외부) 우선 탐색
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        external_path = os.path.join(exe_dir, relative_path)
        if os.path.exists(external_path):
            return external_path
            
    # 2단계: 외부에서 못 찾았거나 IDE 환경인 경우
    try:
        # PyInstaller에 의해 생성된 임시 패키징 폴더 (_MEIPASS) 확인
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python (IDE) 환경인 경우 현재 파일의 부모 디렉토리 (프로젝트 루트)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def get_app_data_path(relative_path):
    """
    로그나 설정 파일처럼 실행 중 생성/변경되는 파일의 경로를 반환합니다.
    (EXE 파일이 위치한 실제 폴더 기준)
    """
    if getattr(sys, 'frozen', False):
        # EXE로 실행 중이면 EXE 파일이 있는 폴더 기준 (dist/WaveSurfer/)
        base_path = os.path.dirname(sys.executable)
    else:
        # IDE 환경이면 프로젝트 루트 기준
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    full_path = os.path.join(base_path, relative_path)
    
    # [v1.3.4 추가] 디렉토리가 없으면 자동 생성하여 FileNotFoundError 방지
    dir_path = os.path.dirname(full_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        
    return full_path
