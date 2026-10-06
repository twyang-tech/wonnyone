import json
from pathlib import Path


def load_config(path=None):
    path = Path(path) if path else Path(__file__).resolve().parent.parent / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    for key in ('games', 'languages', 'image_resolutions', 'video_resolutions'):
        values = config.get(key)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
            raise ValueError(f'설정 오류: {key}는 비어 있지 않은 문자열 목록이어야 합니다.')
        if len(set(values)) != len(values):
            raise ValueError(f'설정 오류: {key}에 중복 값이 있습니다.')
    return config
