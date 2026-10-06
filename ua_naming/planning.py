"""Read-only preview planning; execution consumes the exact confirmed plan."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import os
import re
import tempfile
import shutil

from .media import inspect_media
from .naming import build_new_filename
from .image_io import save_image_with_options


@dataclass(frozen=True)
class Options:
    game: str = ''
    feature: str = ''
    language: str = ''
    date: str = ''
    cta: bool = False
    duration: bool = False
    aspect: str = ''
    output_format: str = '원본 유지'
    compression: str = '압축 안 함'
    keep_name: bool = False
    overwrite: bool = False
    output_dir: str = ''
    find: str = ''
    replace: str = ''


@dataclass
class PlannedFile:
    source: Path
    destination: Path
    media: object
    signature: tuple
    warnings: list = field(default_factory=list)


@dataclass
class Plan:
    options: Options
    files: list = field(default_factory=list)
    sets: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def path_key(path):
    # Windows destinations are case-insensitive even during Linux validation.
    return str(Path(path).resolve()).casefold()


def signature(path):
    s = path.stat()
    return s.st_size, s.st_mtime_ns


def valid_name(name):
    stem = name.split('.')[0].upper()
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ('COM', 'LPT') for i in range(1, 10)}
    return bool(name) and len(name) <= 255 and not re.search(r'[\\/:*?"<>|\x00-\x1f]', name) and not name.endswith((' ', '.')) and stem not in reserved


def destination_exists(path):
    if path.exists():
        return True
    if path.parent.exists():
        return any(p.name.casefold() == path.name.casefold() for p in path.parent.iterdir())
    return False


def build_plan(paths, options, config):
    plan = Plan(options)
    if not paths:
        plan.errors.append('파일을 선택해주세요.')
    if not options.keep_name:
        for label, value in [('게임', options.game), ('소재명', options.feature), ('언어', options.language)]:
            if not value.strip() or value == '직접입력':
                plan.errors.append(f'{label}을 입력해주세요.')
        try:
            if not re.fullmatch(r'\d{6}', options.date):
                raise ValueError()
            datetime.strptime(options.date, '%y%m%d')
        except ValueError:
            plan.errors.append('날짜는 실제 존재하는 YYMMDD 날짜여야 합니다.')
    if not options.overwrite and not options.output_dir.strip():
        plan.errors.append('저장 폴더를 지정해주세요.')
    groups = defaultdict(list)
    seen_sources = set()
    for path in paths:
        source = Path(path).resolve()
        if path_key(source) in seen_sources:
            continue
        seen_sources.add(path_key(source))
        media = inspect_media(source)
        if not source.is_file() or media.kind == '지원 안 함' or (media.kind == '이미지' and media.error):
            plan.errors.append(f'{source.name}: {media.error}')
            continue
        if options.keep_name:
            ext = source.suffix
            if media.kind == '이미지' and options.output_format != '원본 유지':
                ext = '.' + options.output_format.lower()
            name = source.stem + ext
        else:
            name = build_new_filename(str(source), options.game,
                options.feature + ('+CTA' if options.cta else ''), options.language,
                options.date, options.duration, options.aspect, options.output_format)[0]
        base, ext = os.path.splitext(name)
        if options.find:
            base = base.replace(options.find, options.replace)
        name = base + ext
        if not valid_name(name):
            plan.errors.append(f'{source.name}: Windows에서 사용할 수 없는 최종 파일명입니다: {name}')
            continue
        dest = (source.parent if options.overwrite else Path(options.output_dir).expanduser().resolve()) / name
        item = PlannedFile(source, dest, media, signature(source))
        if media.error:
            item.warnings.append(media.error)
        if media.kind == '이미지' and media.format.upper() != ('JPEG' if source.suffix.lower() in ('.jpg', '.jpeg') else source.suffix[1:].upper()):
            item.warnings.append('실제 이미지 형식과 확장자가 다릅니다.')
        plan.files.append(item)
        fmt = dest.suffix.lower() if media.kind == '이미지' else 'VID'
        if fmt == '.jpeg':
            fmt = '.jpg'
        # No resolution in this identity or in the destination directory.
        key = (options.game, options.feature, options.language, media.kind, options.cta, options.date, fmt)
        groups[key].append(item)
    destinations = Counter(path_key(f.destination) for f in plan.files)
    for item in plan.files:
        if destinations[path_key(item.destination)] > 1:
            plan.errors.append(f'선택 파일 간 최종 이름 충돌: {item.destination.name}')
        if item.destination != item.source and destination_exists(item.destination):
            plan.errors.append(f'기존 파일과 이름 충돌: {item.destination}')
        if item.destination == item.source and not options.overwrite:
            plan.errors.append(f'원본과 저장 위치가 같습니다. 원본 위치 처리 옵션을 확인하세요: {item.source.name}')
        plan.warnings.extend(f'{item.source.name}: {w}' for w in item.warnings)
    for key, items in groups.items():
        expected = config['image_resolutions' if key[3] == '이미지' else 'video_resolutions']
        counts = Counter(f.media.resolution for f in items)
        missing = [r for r in expected if r not in counts]
        duplicate = [r for r, count in counts.items() if count > 1]
        unexpected = [r for r in counts if r not in expected]
        label = ' / '.join(str(v) for v in key)
        problems = []
        for heading, values in [('누락', missing), ('중복', duplicate), ('예상 외', unexpected)]:
            if values:
                problems.append(f'{heading}: {", ".join(values)}')
        status = f'{key[3]} 세트 {"경고" if problems else "정상"}: {sum(r in counts for r in expected)} / {len(expected)}'
        plan.sets.append(label + '\n' + status + (' — ' + '; '.join(problems) if problems else ''))
        plan.warnings.extend(label + ' — ' + problem for problem in problems)
    return plan


def describe_plan(plan):
    lines = ['처리 방식: ' + ('원본 위치 처리 (변경 시 원본 제거)' if plan.options.overwrite else '복사본 저장 (원본 유지)'), '']
    for f in plan.files:
        lines.extend([f'원본: {f.source}', f'{f.media.kind} / {f.media.format} / {f.media.resolution}', f'최종: {f.destination}', ''])
    lines += ['소재 세트', *plan.sets]
    if plan.warnings:
        lines += ['', '경고 (확인 후 진행 가능)', *plan.warnings]
    if plan.errors:
        lines += ['', '실행 차단 (수정 필요)', *plan.errors]
    return '\n'.join(lines)


def execute_plan(plan):
    if plan.errors:
        raise ValueError('충돌 또는 입력 오류가 있는 계획은 실행할 수 없습니다.')
    # Check every source and target before making any changes.
    for item in plan.files:
        if signature(item.source) != item.signature:
            raise ValueError(f'Preview 이후 원본 변경: {item.source.name}')
        if item.destination != item.source and destination_exists(item.destination):
            raise FileExistsError(f'Preview 이후 대상 파일 생성: {item.destination}')
    results, errors = [], []
    for item in plan.files:
        temp = None
        reserved = False
        try:
            dest = item.destination
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix='.ua-', suffix=dest.suffix, dir=dest.parent)
            os.close(fd)
            temp = Path(temp_name)
            if item.media.kind == '영상':
                shutil.copy2(item.source, temp)
            else:
                save_image_with_options(str(item.source), str(temp), plan.options.output_format, plan.options.compression)
            if dest != item.source:
                # Exclusive reservation closes the create-after-preview race.
                with dest.open('xb'):
                    pass
                reserved = True
            os.replace(temp, dest)
            temp = None
            reserved = False
            if plan.options.overwrite and dest != item.source:
                item.source.unlink()
            results.append(dest.name)
        except Exception as exc:
            if reserved:
                item.destination.unlink(missing_ok=True)
            errors.append(f'{item.source.name}: {exc}')
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
    return results, errors
