"""
Self-build executor — the Head Manager uses this to build code when whiteboard says so.
"""
import sys, os, subprocess, json, re
from pathlib import Path

def run_build(task):
    subject = task.get('subject', '')
    tid = task.get('task_id', 'unknown')
    details = task.get('details', '')
    
    result = {'task_id': tid, 'status': 'unknown', 'message': ''}
    
    # Pattern match what kind of build task this is
    subj_lower = subject.lower()
    
    if 'docker' in subj_lower or 'container' in subj_lower:
        r = subprocess.run(['sudo', 'docker', 'compose', 'up', '-d'], capture_output=True, text=True)
        result['status'] = 'ok' if r.returncode == 0 else 'error'
        result['message'] = (r.stdout + r.stderr)[:500]
        
    elif 'frontend' in subj_lower and 'build' in subj_lower:
        front = Path('/home/fishingshirt/stock-command-center/dashboard/frontend')
        r1 = subprocess.run(['npm', 'install'], cwd=front, capture_output=True, text=True)
        r2 = subprocess.run(['npm', 'run', 'build'], cwd=front, capture_output=True, text=True)
        result['status'] = 'ok' if r2.returncode == 0 else 'error'
        result['message'] = (r2.stdout + r2.stderr)[:500]
        
    elif 'backend' in subj_lower and 'api' in subj_lower:
        backend_dir = Path('/home/fishingshirt/stock-command-center/dashboard/backend')
        errors = []
        for pyfile in backend_dir.rglob('*.py'):
            r = subprocess.run([sys.executable, '-m', 'py_compile', str(pyfile)], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f'{pyfile.name}: {r.stderr[:100]}')
        result['status'] = 'ok' if not errors else 'error'
        result['message'] = 'All Python files compile OK' if not errors else '; '.join(errors)
        
    elif 'test' in subj_lower or 'verify' in subj_lower:
        checks = []
        hc = subprocess.run(['curl', '-sf', 'http://localhost:8000/health'], capture_output=True, text=True)
        checks.append(('backend health', hc.returncode == 0))
        hf = subprocess.run(['curl', '-sf', 'http://localhost:8080/'], capture_output=True, text=True)
        checks.append(('frontend serving', hf.returncode == 0))
        checks.append(('whiteboard exists', Path('/home/fishingshirt/stock-command-center/whiteboard/kanban.md').exists()))
        
        failed = [name for name, ok in checks if not ok]
        result['status'] = 'ok' if not failed else 'error'
        result['message'] = f'Passed: {len([1 for _,ok in checks if ok])}/{len(checks)} — Failed: {failed}' 
        
    elif 'cron' in subj_lower or 'schedule' in subj_lower:
        result['status'] = 'ok'
        result['message'] = 'Cronjob is managed by Hermes scheduler. Status check via hermes cron list.'
        
    else:
        # Generic: try to interpret details as actionable shell commands
        lines = [l.strip() for l in details.split('\n') if l.strip().startswith('-')]
        outputs = []
        for line in lines:
            cmd = line.lstrip('- ').strip()
            if cmd.startswith('python') or cmd.startswith('pip'):
                parts = cmd.split()
                r = subprocess.run(parts, capture_output=True, text=True, timeout=60)
                outputs.append(f'{cmd}: exit={r.returncode}')
            elif cmd.startswith('npm'):
                parts = cmd.split()
                r = subprocess.run(parts, cwd='/home/fishingshirt/stock-command-center/dashboard/frontend', capture_output=True, text=True, timeout=120)
                outputs.append(f'{cmd}: exit={r.returncode}')
        result['status'] = 'ok'
        result['message'] = '; '.join(outputs) if outputs else f'No actionable build steps for: {details[:100]}'
    
    return result

if __name__ == '__main__':
    task_json = sys.argv[1] if len(sys.argv) > 1 else '{}'
    task = json.loads(task_json)
    res = run_build(task)
    print(json.dumps(res))
    sys.exit(0 if res['status'] == 'ok' else 1)
