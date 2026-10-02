#!/usr/bin/env python3
"""Portable native-host runner for Windows, macOS and Linux. Python 3.9+."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from audio import inspect_audio, sources, usable
from configure_tools import check_dependencies

ROOT = Path(__file__).resolve().parent
TASKS = sorted(p.name for p in (ROOT / 'tasks').iterdir() if (p / 'task.toml').exists())
SUFFIX = '\n本次为本机独立运行。请在当前工作目录完成任务，不读取其他实验目录、参考谱或其他模型的输出。\n'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, data):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def java_path():
    return os.environ.get('JAVA') or (str(Path(os.environ['JAVA_HOME']) / 'bin' / ('java.exe' if os.name == 'nt' else 'java'))
           if os.environ.get('JAVA_HOME') else shutil.which('java'))


def process_options(platform_name=None):
    return {'creationflags': 0x00000200} if (platform_name or os.name) == 'nt' else {'start_new_session': True}


def capture(command):
    p = subprocess.run(command, capture_output=True, text=True, timeout=30, encoding='utf-8')
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-2000:])
    return (p.stdout + p.stderr).strip()


def executable(agent):
    result = shutil.which('claude' if agent == 'claude-code' else 'codex')
    if not result:
        raise RuntimeError('Install and authenticate ' + agent + ' first.')
    return result


def command(args, exe, final):
    if args.agent == 'claude-code':
        return [exe, '-p', '--model', args.model, '--effort', args.effort,
                '--permission-mode', args.permission_mode,
                '--verbose', '--output-format', 'stream-json']
    return [exe, 'exec', '--model', args.model, '-c', 'model_reasoning_effort=' + args.effort,
            '--skip-git-repo-check', '--approve-for-me', '--json',
            '--output-last-message', str(final), '-']


def event_summary(path, agent):
    models, final, errors = set(), [], []
    completed = False
    usage = None
    for line in path.read_text(errors='replace', encoding='utf-8').splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if agent == 'claude-code':
            if e.get('type') == 'system' and e.get('model'):
                models.add(e['model'])
            if e.get('type') == 'assistant' and e.get('message', {}).get('model'):
                models.add(e['message']['model'])
            if e.get('type') == 'result':
                usage = e.get('usage')
                models.update(e.get('modelUsage', {}))
                if e.get('is_error') or e.get('subtype', 'success') != 'success':
                    errors.append(e.get('result', e.get('subtype', 'error')))
                else:
                    completed = True
                if isinstance(e.get('result'), str):
                    final.append(e['result'])
        else:
            if e.get('type') == 'turn.completed':
                completed, usage = True, e.get('usage')
            if e.get('type') == 'turn.failed':
                errors.append(str(e.get('error', 'turn.failed')))
            item = e.get('item', {})
            if item.get('type') == 'agent_message':
                final.append(item.get('text', ''))
    return {'completed_event': completed, 'observed_models': sorted(models),
            'reported_errors': errors, 'usage': usage}, '\n\n'.join(final)


def stop_group(proc):
    # Children inherit the process group unless the agent explicitly detaches them.
    if os.name == 'nt':
        if proc.poll() is None:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=30)
            proc.wait(timeout=10)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def verify(task, output, logs):
    check_dependencies()
    env = dict(os.environ, JAVA=java_path() or 'java')
    p = subprocess.run([sys.executable, str(ROOT / 'verifier/verify.py'),
                        '--output', str(output), '--logs', str(logs)],
                       env=env, capture_output=True, text=True, timeout=120, encoding='utf-8')
    logs.mkdir(parents=True, exist_ok=True)
    (logs / 'verifier.txt').write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode:
        raise RuntimeError('Verifier infrastructure error: ' + p.stderr[-1500:])
    return json.loads((logs / 'report.json').read_text(encoding='utf-8'))


def run_batch(args):
    toolchain = check_dependencies()
    audio_checks = {s['task']: inspect_audio(s) for s in sources() if s['task'] in args.tasks}
    bad = [task for task, result in audio_checks.items() if not usable(result, args.allow_audio_variant)]
    if bad:
        raise RuntimeError('Audio missing or not matched: ' + ', '.join(bad) + '. Run python3 audio.py download/check; see README.md.')
    exe = executable(args.agent) if not args.prepare_only else ('claude' if args.agent == 'claude-code' else 'codex')
    version = capture([exe, '--version']) if not args.prepare_only else 'not_probed'
    java = java_path()
    if not args.prepare_only:
        capture([java or 'java', '-version'])
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    batch = args.runs.resolve() / ('batch-' + stamp + '-' + uuid.uuid4().hex[:8])
    batch.mkdir(parents=True)
    state = {'schema_version': 1, 'status': 'prepared' if args.prepare_only else 'running',
             'created_at': now(), 'supervisor_pid': os.getpid(), 'agent': args.agent,
             'agent_version': version, 'model': args.model, 'reasoning_effort': args.effort,
             'max_concurrency': args.concurrency, 'timeout_sec': args.timeout,
             'platform': platform.platform(), 'python': platform.python_version(),
             'cpu_count': os.cpu_count(), 'execution': 'host', 'docker': False,
             'toolchain': toolchain, 'environment_notes': args.environment_notes,
             'permission_mode': args.permission_mode if args.agent == 'claude-code' else 'approve-for-me',
             'trials': [{'task': t, 'status': 'queued'} for t in args.tasks]}
    manifest = batch / 'batch.json'
    lock, stopping = threading.Lock(), threading.Event()
    active = {}

    def save():
        write_json(manifest, state)

    def on_signal(signum, frame):
        stopping.set()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    save()
    print('BATCH', batch, flush=True)

    def trial(row):
        task = ROOT / 'tasks' / row['task']
        run = batch / row['task']
        work = run / 'workspace'
        record = None
        proc = None
        if stopping.is_set():
            with lock:
                row['status'] = 'cancelled_before_start'
                save()
            return
        try:
            for d in [work / 'input', work / 'output', run / 'logs']:
                d.mkdir(parents=True)
            shutil.copy2(task / 'environment/original.wav', work / 'input/original.wav')
            shutil.copytree(ROOT / 'tools', work / 'tools')
            if java:
                write_json(work / 'tools/runtime.json', {'java': java})
            prompt = (task / 'instruction.md').read_text(encoding='utf-8').replace('/workspace/', work.as_posix() + '/') + SUFFIX
            if args.environment_notes:
                prompt += '\n本机软件与操作环境：' + args.environment_notes + '\n'
            (work / 'instruction.md').write_text(prompt, encoding='utf-8')
            cmd = command(args, exe, run / 'logs/final.txt')
            record = {k: state[k] for k in ['agent', 'agent_version', 'model', 'reasoning_effort',
                      'timeout_sec', 'platform', 'execution', 'docker', 'permission_mode', 'toolchain', 'environment_notes']}
            record.update(task=row['task'], task_version=re.search(r'^version\s*=\s*"([^"]+)"',
                (task / 'task.toml').read_text(encoding='utf-8'), re.M).group(1), created_at=now(), status='prepared',
                command=cmd, instruction_sha256=digest(task / 'instruction.md'),
                rendered_instruction_sha256=digest(work / 'instruction.md'),
                audio_sha256=digest(work / 'input/original.wav'),
                audio_identity=audio_checks[row['task']],
                audio_variant_allowed=args.allow_audio_variant,
                note='Fresh native folder; not filesystem read isolation. User CLI settings inherited. No quality judging.')
            write_json(run / 'run.json', record)
            with lock:
                row.update(status='prepared', run_dir=row['task'])
                save()
            if args.prepare_only:
                return
            with (work / 'instruction.md').open(encoding='utf-8') as stdin, (run / 'logs/events.jsonl').open('w', encoding='utf-8') as stdout, (run / 'logs/stderr.txt').open('w', encoding='utf-8') as stderr:
                proc = subprocess.Popen(cmd, cwd=work, stdin=stdin, stdout=stdout, stderr=stderr, **process_options())
                start = time.monotonic()
                record.update(status='running', started_at=now(), agent_pid=proc.pid)
                write_json(run / 'run.json', record)
                with lock:
                    active[row['task']] = proc
                    row.update(status='running', agent_pid=proc.pid)
                    save()
                print('START', row['task'], flush=True)
                while proc.poll() is None:
                    if stopping.is_set() or time.monotonic() - start >= args.timeout:
                        record['status'] = 'interrupted' if stopping.is_set() else 'timed_out'
                        stop_group(proc)
                        break
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                record['exit_code'] = proc.returncode
                record['elapsed_sec'] = round(time.monotonic() - start, 3)
            events, final = event_summary(run / 'logs/events.jsonl', args.agent)
            record.update(events)
            (run / 'logs/final.txt').write_text(final, encoding='utf-8')
            if record['status'] == 'running':
                record['status'] = 'process_completed' if proc.returncode == 0 and events['completed_event'] and not events['reported_errors'] else 'process_failed'
            record['finished_at'] = now()
            record['output_files'] = sorted(p.name for p in (work / 'output').iterdir())
            record['sole_gp_output'] = record['output_files'] == ['arrangement.gp']
            try:
                report = verify(row['task'], work / 'output', run / 'verification')
                record['parseable_score'] = report['parseable_score']
            except Exception as exc:
                record['verification_error'] = str(exc)
            gp = work / 'output/arrangement.gp'
            if gp.is_file() and not gp.is_symlink():
                record['score_sha256'] = digest(gp)
            # Preserve the original verifier result; output exclusivity is a separate check.
            write_json(run / 'run.json', record)
            with lock:
                row.update({k: record.get(k) for k in ['status', 'exit_code', 'parseable_score', 'sole_gp_output', 'elapsed_sec']})
                save()
        except Exception as exc:
            if proc and proc.poll() is None:
                stop_group(proc)
            if record:
                record.update(status='infrastructure_error', error=str(exc), finished_at=now())
                write_json(run / 'run.json', record)
            with lock:
                row.update(status='infrastructure_error', error=str(exc))
                save()
        finally:
            with lock:
                active.pop(row['task'], None)
            print('END', row['task'], row['status'], flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(trial, state['trials']))
    state.update(status='prepared' if args.prepare_only else ('interrupted' if stopping.is_set() else 'finished'), finished_at=now())
    save()
    print('BATCH', batch, state['status'], flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    for name in ['run', 'probe']:
        p = sub.add_parser(name)
        p.add_argument('--agent', choices=['claude-code', 'codex'], default='claude-code')
        p.add_argument('--model', default='claude-opus-5-5')
        p.add_argument('--effort', choices=['low', 'medium', 'high', 'xhigh', 'max'], default='high')
        p.add_argument('--permission-mode', choices=['auto', 'default', 'acceptEdits', 'dontAsk'], default='auto')
        if name == 'run':
            p.add_argument('--tasks', nargs='+', choices=TASKS, default=TASKS)
            p.add_argument('--concurrency', type=int, choices=[1, 2], default=2)
            p.add_argument('--timeout', type=int, default=3600)
            p.add_argument('--runs', type=Path, default=ROOT / 'runs')
            p.add_argument('--prepare-only', action='store_true')
            p.add_argument('--allow-audio-variant', action='store_true', help='Explicitly record nonidentical PCM as a variant; duration and format must still match.')
            p.add_argument('--environment-notes', default='', help='Record installed score editors and GUI tools; also passed to the agent.')
    p = sub.add_parser('doctor')
    p.add_argument('--agent', choices=['claude-code', 'codex'], default='claude-code')
    p = sub.add_parser('status'); p.add_argument('batch', type=Path)
    p = sub.add_parser('export'); p.add_argument('batch', type=Path); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('verify'); p.add_argument('--task', choices=TASKS, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--logs', type=Path, required=True)
    p = sub.add_parser('export-harbor'); p.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.action == 'run':
        if args.timeout <= 0 or len(set(args.tasks)) != len(args.tasks):
            ap.error('Timeout must be positive; tasks must be unique.')
        run_batch(args)
    elif args.action == 'doctor':
        checks = json.loads((ROOT / 'checksums.json').read_text(encoding='utf-8'))
        bad = [p for p, h in checks.items() if not (ROOT / p).is_file() or digest(ROOT / p) != h]
        print('Package integrity:', 'OK' if not bad else bad)
        print('External toolchain:', json.dumps(check_dependencies(), ensure_ascii=False))
        print('Python:', platform.python_version(), 'Host:', platform.platform())
        print('Java:', capture([java_path() or 'java', '-version']))
        print('Agent:', capture([executable(args.agent), '--version']))
        audio_checks = [inspect_audio(s) for s in sources()]
        print('Audio identity:', 'OK' if all(usable(r) for r in audio_checks) else 'MISSING / MISMATCH: run python3 audio.py download/check')
        if bad or not all(usable(r) for r in audio_checks):
            raise SystemExit(1)
    elif args.action == 'probe':
        exe = executable(args.agent)
        print('Agent:', capture([exe, '--version']))
        with tempfile.TemporaryDirectory(prefix='guitar-model-probe-') as d:
            path = Path(d)
            cmd = command(args, exe, path / 'final.txt')
            p = subprocess.run(cmd, cwd=path, input='Reply exactly OK. Do not use tools or read any files.', capture_output=True, text=True, timeout=300, encoding='utf-8')
            (path / 'events.jsonl').write_text(p.stdout, encoding='utf-8')
            summary, final = event_summary(path / 'events.jsonl', args.agent)
            print(json.dumps({'exit_code': p.returncode, **summary, 'final': final}, ensure_ascii=False, indent=2))
            if p.returncode or not summary['completed_event'] or summary['reported_errors']:
                print(p.stderr[-2000:]); raise SystemExit(1)
    elif args.action == 'status':
        s = json.loads((args.batch / 'batch.json').read_text(encoding='utf-8'))
        alive = False
        if s['status'] == 'running':
            if os.name == 'nt':
                query = "(Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(int(s['supervisor_pid'])) + "').CommandLine"
                cmd = ['powershell.exe', '-NoProfile', '-Command', query]
            else:
                cmd = ['ps', '-p', str(s['supervisor_pid']), '-o', 'command=']
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
            alive = p.returncode == 0 and 'run.py' in p.stdout
        print('Batch:', s['status'], 'Supervisor live:', alive if s['status'] == 'running' else 'not needed')
        if s['status'] == 'running' and not alive:
            print('INTERRUPTED: stored running states are stale; inspect logs before any retry.')
        for row in s['trials']:
            print(row['task'], row['status'], 'parseable=', row.get('parseable_score', '-'))
    elif args.action == 'verify':
        print(json.dumps(verify(args.task, args.output.resolve(), args.logs.resolve()), ensure_ascii=False, indent=2))
    elif args.action == 'export-harbor':
        check_dependencies()
        if not all(usable(inspect_audio(s)) for s in sources()):
            raise RuntimeError('Download and check all seven audio inputs first.')
        dest = args.output.resolve()
        dest.mkdir(parents=True, exist_ok=False)
        for task in TASKS:
            shutil.copytree(ROOT / 'tasks' / task, dest / task)
            shutil.copytree(ROOT / 'tools', dest / task / 'environment/tools')
            shutil.copytree(ROOT / 'verifier', dest / task / 'tests')
        print('Harbor task directories:', dest)
    elif args.action == 'export':
        batch = args.batch.resolve()
        state = json.loads((batch / 'batch.json').read_text(encoding='utf-8'))
        if state['status'] in ['running', 'prepared']:
            raise RuntimeError('Export only a finished or interrupted batch, after all writers stop.')
        if args.output.exists():
            raise RuntimeError('Export path already exists; choose a new name.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        files = [batch / 'batch.json']
        for row in state['trials']:
            run = batch / row['task']
            for name in ['run.json', 'workspace/output/arrangement.gp', 'logs/events.jsonl',
                         'logs/stderr.txt', 'logs/final.txt', 'verification/report.json',
                         'verification/reward.json', 'verification/verifier.txt']:
                f = run / name
                if f.is_file() and not f.is_symlink():
                    files.append(f)
        with zipfile.ZipFile(args.output, 'x', zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(batch).as_posix())
        print('Exported', args.output, 'SHA256', digest(args.output))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        raise SystemExit(1)
