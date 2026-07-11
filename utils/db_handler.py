import json
import os
import shutil
import logging

logger = logging.getLogger(__name__)

class DBHandler:
    @staticmethod
    def load_json(file_path: str, default_data=None):
        """
        JSON 파일을 로드합니다. 파일이 존재하지 않으면 default_data를 반환합니다.
        """
        if default_data is None:
            default_data = {}

        if not os.path.exists(file_path):
            return default_data

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"JSONDecodeError: {file_path} 파일이 손상되었습니다.")
            # 백업 파일이 있으면 복구 시도
            bak_path = f"{file_path}.bak"
            if os.path.exists(bak_path):
                logger.info(f"백업 파일({bak_path})에서 복구를 시도합니다.")
                try:
                    with open(bak_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"백업 복구 실패: {e}")
            return default_data
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return default_data

    @staticmethod
    def save_json(file_path: str, data):
        """
        데이터를 JSON 파일로 저장합니다. 
        저장 전 기존 파일을 .bak로 백업하며, 들여쓰기(indent=4)를 적용합니다.
        """
        # 디렉토리가 없으면 생성
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # 기존 파일이 있으면 백업
        if os.path.exists(file_path):
            bak_path = f"{file_path}.bak"
            try:
                shutil.copy2(file_path, bak_path)
            except Exception as e:
                logger.warning(f"백업 생성 실패 ({bak_path}): {e}")

        # 임시 파일로 먼저 쓴 후 교체(Atomic Write 흉내)
        tmp_path = f"{file_path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(tmp_path, file_path)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
