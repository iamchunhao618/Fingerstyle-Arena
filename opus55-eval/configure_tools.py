#!/usr/bin/env python3
"""Configure files the operator downloaded. Never downloads or installs software."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_dependencies(root=ROOT):
    spec = json.loads((root / 'dependencies.json').read_text(encoding='utf-8'))
    vendor = root / 'tools/vendor'
    expected = {'tools/vendor/tuxguitar-1.6.6/' + n: h for n, h in spec['tuxguitar_jars'].items()}
    expected['tools/vendor/rhino-1.7.15.jar'] = spec['rhino']['sha256']
    for name, item in spec['fonts'].items():
        if name.endswith('.otf'):
            expected['tools/vendor/' + name] = item['sha256']
    for name in spec['verifier_jars']:
        expected['verifier/lib/' + name] = spec['rhino']['sha256'] if name.startswith('rhino-') else spec['tuxguitar_jars'][name]
    bad = [name for name, h in expected.items() if not (root / name).is_file() or digest(root / name) != h]
    state_path = vendor / 'dependency-state.json'
    if bad or not state_path.exists():
        raise RuntimeError('External software not configured/matched. Read README.md and run configure_tools.py. Missing or mismatched: ' + ', '.join(bad[:5]))
    state = json.loads(state_path.read_text(encoding='utf-8'))
    patch = vendor / 'tuxguitar-pdf-unicode.jar'
    if not patch.is_file() or digest(patch) != state['compiled_patch_sha256']:
        raise RuntimeError('PDF patch missing/changed; rerun configure_tools.py.')
    for name, h in spec['patch_sources'].items():
        if digest(root / 'patches/pdf-unicode' / name) != h:
            raise RuntimeError('PDF patch source changed: ' + name)
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tuxguitar', type=Path, required=True, help='Root of the unpacked official TuxGuitar 1.6.6 release')
    p.add_argument('--rhino', type=Path, required=True)
    p.add_argument('--font-regular', type=Path, required=True)
    p.add_argument('--font-bold', type=Path, required=True)
    p.add_argument('--javac', default=str(Path(os.environ['JAVA_HOME']) / 'bin' / ('javac.exe' if os.name == 'nt' else 'javac')) if os.environ.get('JAVA_HOME') else 'javac')
    args = p.parse_args()
    spec = json.loads((ROOT / 'dependencies.json').read_text(encoding='utf-8'))
    source = {}
    for path in args.tuxguitar.rglob('*.jar'):
        if path.name in spec['tuxguitar_jars'] and digest(path) == spec['tuxguitar_jars'][path.name]:
            source[path.name] = path
    missing = sorted(set(spec['tuxguitar_jars']) - set(source))
    if missing:
        raise RuntimeError('Required JARs absent or their hashes differ: ' + ', '.join(missing) + '. See exact release links and dependencies.json.')
    additional = {'rhino-1.7.15.jar': (args.rhino, spec['rhino']['sha256']),
                  'fonts/NotoSansCJKsc-Regular.otf': (args.font_regular, spec['fonts']['fonts/NotoSansCJKsc-Regular.otf']['sha256']),
                  'fonts/NotoSansCJKsc-Bold.otf': (args.font_bold, spec['fonts']['fonts/NotoSansCJKsc-Bold.otf']['sha256'])}
    for name, (path, h) in additional.items():
        if not path.is_file() or digest(path) != h:
            raise RuntimeError('Download/version mismatch: ' + name)
    vendor = ROOT / 'tools/vendor'
    (vendor / 'tuxguitar-1.6.6').mkdir(parents=True, exist_ok=True)
    for name, path in source.items():
        dest = vendor / 'tuxguitar-1.6.6' / name
        if path.resolve() != dest.resolve():
            shutil.copy2(path, dest)
    for name, (path, h) in additional.items():
        dest = vendor / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != dest.resolve():
            shutil.copy2(path, dest)
    lib = ROOT / 'verifier/lib'
    lib.mkdir(parents=True, exist_ok=True)
    for name in spec['verifier_jars']:
        path = vendor / name if name.startswith('rhino-') else vendor / 'tuxguitar-1.6.6' / name
        shutil.copy2(path, lib / name)
    sources = sorted((ROOT / 'patches/pdf-unicode').glob('*.java'))
    javac_version = subprocess.check_output([args.javac, '-version'], stderr=subprocess.STDOUT, text=True, encoding='utf-8').strip()
    with tempfile.TemporaryDirectory(prefix='guitar-pdf-build-') as d:
        out = Path(d)
        cp = os.pathsep.join(str(x.resolve()) for x in (vendor / 'tuxguitar-1.6.6').glob('*.jar'))
        subprocess.run([args.javac, '--release', '17', '-encoding', 'UTF-8', '-cp', cp, '-d', str(out), *map(str, sources)], check=True)
        patch = vendor / 'tuxguitar-pdf-unicode.jar'
        with zipfile.ZipFile(patch, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(out.rglob('*.class')):
                item = zipfile.ZipInfo(path.relative_to(out).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(item, path.read_bytes())
    state = {'configured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'tuxguitar_version': spec['tuxguitar_version'], 'javac': javac_version,
             'compiled_patch_sha256': digest(patch),
             'historical_patch_binary_matches': digest(patch) == spec['historical_patch_jar_sha256'],
             'dependency_manifest_sha256': digest(ROOT / 'dependencies.json')}
    (vendor / 'dependency-state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(check_dependencies(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
