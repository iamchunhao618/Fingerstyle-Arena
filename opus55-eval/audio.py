#!/usr/bin/env python3
"""Download the recorded YouTube sources and check decoded PCM identity."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parent


def sources():
    return json.loads((ROOT / 'audio-sources.json').read_text(encoding='utf-8'))['songs']


def inspect_audio(song, path=None):
    path = Path(path) if path else ROOT / song['target']
    result = {'task': song['task'], 'source_url': song['url'], 'exists': path.is_file(),
              'format_matches': False, 'duration_matches': False, 'pcm_matches': False}
    if not result['exists']:
        return result
    try:
        with wave.open(str(path), 'rb') as w:
            rate, channels, width, frames = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
            pcm = hashlib.sha256()
            for block in iter(lambda: w.readframes(65536), b''):
                pcm.update(block)
        result.update(sample_rate=rate, channels=channels, sample_width_bytes=width, frames=frames,
                      duration_seconds=frames / rate, pcm_sha256=pcm.hexdigest(),
                      format_matches=(rate, channels, width) == (song['sample_rate'], song['channels'], song['sample_width_bytes']),
                      duration_matches=abs(frames / rate - song['duration_seconds']) <= 0.1,
                      pcm_matches=pcm.hexdigest() == song['pcm_sha256'])
    except (wave.Error, EOFError, OSError) as exc:
        result['error'] = str(exc)
    return result


def usable(result, allow_variant=False):
    return result['format_matches'] and result['duration_matches'] and (result['pcm_matches'] or allow_variant)


def downloader():
    exe = shutil.which('yt-dlp')
    if exe:
        return [exe]
    if importlib.util.find_spec('yt_dlp'):
        return [sys.executable, '-m', 'yt_dlp']
    raise RuntimeError('Install yt-dlp first; see README.md.')


def download(song):
    target = ROOT / song['target']
    if target.exists():
        print(song['task'], 'already exists; checking without overwriting.', flush=True)
        return inspect_audio(song)
    ffmpeg = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Install FFmpeg or set FFMPEG to its executable path.')
    ytdlp = downloader()
    cache = ROOT / 'downloads' / song['task']
    cache.mkdir(parents=True, exist_ok=True)
    cmd = ytdlp + ['--ignore-config', '--no-playlist', '--no-progress', '--socket-timeout', '30',
                  '--retries', '2', '--no-overwrites', '-f', song['download_format_id'],
                  '--write-info-json', '-o', str(cache / 'source.%(ext)s'), song['url']]
    subprocess.run(cmd, check=True, timeout=900)
    info = json.loads((cache / 'source.info.json').read_text(encoding='utf-8'))
    if info.get('id') != song['video_id'] or str(info.get('format_id')) != song['download_format_id']:
        raise RuntimeError('Video ID or format differs from the recorded source; stopped.')
    native = cache / ('source.' + info['ext'])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('original.pending.wav')
    convert = [ffmpeg, '-nostdin', '-v', 'error', '-y', '-i', str(native), '-map', '0:a:0',
               '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', '-map_metadata', '-1', str(temporary)]
    subprocess.run(convert, check=True, timeout=300)
    result = inspect_audio(song, temporary)
    if not result['format_matches'] or not result['duration_matches']:
        raise RuntimeError('Downloaded audio format or duration differs; kept original.pending.wav for review.')
    temporary.replace(target)
    provenance = {'task': song['task'], 'url': song['url'], 'downloaded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'video_id': info['id'], 'title': info.get('title'), 'channel': info.get('channel'),
                  'format_id': info['format_id'], 'acodec': info.get('acodec'),
                  'yt_dlp_version': subprocess.check_output(ytdlp + ['--version'], text=True, encoding='utf-8').strip(),
                  'ffmpeg_version': subprocess.check_output([ffmpeg, '-version'], text=True, encoding='utf-8').splitlines()[0],
                  'audio_check': result}
    (cache / 'download-record.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    songs = sources()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['list', 'download', 'check'])
    p.add_argument('--tasks', nargs='+', choices=[s['task'] for s in songs])
    args = p.parse_args()
    selected = [s for s in songs if not args.tasks or s['task'] in args.tasks]
    if args.action == 'list':
        for song in selected:
            print(song['task'], song['source_title'], song['url'])
        return
    results = []
    for song in selected:
        try:
            result = download(song) if args.action == 'download' else inspect_audio(song)
        except Exception as exc:
            result = {'task': song['task'], 'format_matches': False, 'duration_matches': False, 'pcm_matches': False, 'error': str(exc)}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    (ROOT / 'audio-check.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not all(usable(r) for r in results):
        print('Audio identity not confirmed for all selected tasks. See README.md; no fallback source was used.', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
