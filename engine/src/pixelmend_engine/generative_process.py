"""Own, bound and reap a single local model child. No model imports or network."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import signal
import stat
import subprocess
import threading
import time
import psutil

from .model_manager import ModelManagerError

MAX_LINE=65536
KILL_SIGNAL=getattr(signal,'SIGKILL',9)
MESSAGES={
    'runtime_unavailable':'Yerel çalışma paketi kurulu değil.',
    'runtime_crashed':'Yerel model süreci kapandı. Komutu yeniden deneyin.',
    'output_invalid':'Model çıktısı doğrulanamadı; kaynak fotoğraf korunuyor.',
    'timeout':'Model zaman sınırını aştı. Daha kısa bir komut veya düşük kaynak profilini deneyin.',
    'invalid_prompt':'Komut boş olamaz ve en fazla 1000 karakter içerebilir.',
    'invalid_translation':'Komut çevrilemedi. Yeniden yazın veya İngilizce karşılığını girin.',
    'prompt_token_limit':'Komut modelin metin sınırını aşıyor. Komutu kısaltın.',
    'model_not_installed':'Gerekli model paketi kurulu değil.',
    'unsupported_platform':'Bu özellik macOS 15+, Apple Silicon ve en az 16 GB bellek gerektirir.',
    'unsupported_runtime':'Yerel çalışma paketi uyumlu değil; doğrulanmış paketi yeniden kurun.',
}


class RuntimeErrorCode(ModelManagerError):
    def __init__(self,code):
        super().__init__(code,MESSAGES.get(code,MESSAGES['output_invalid']))


def _unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError()
        value[key]=item
    return value


class RuntimeOwner:
    def __init__(self,executable,*,cooperative_seconds=2,terminate_seconds=.75):
        self.executable=Path(executable) if executable else None
        self.cooperative_seconds=cooperative_seconds;self.terminate_seconds=terminate_seconds
        self._condition=threading.Condition();self._process=None;self._closed=False
        self._shutdown=threading.Event()

    @property
    def active_pid(self):
        with self._condition:return self._process.pid if self._process is not None else None

    @staticmethod
    def _signal(process,sig):
        try:
            if os.name=='nt':process.kill() if sig==KILL_SIGNAL else process.terminate()
            else:os.killpg(process.pid,sig)
        except ProcessLookupError:pass

    def _stop(self,process,write_lock):
        def cooperative():
            try:
                with write_lock:
                    process.stdin.write(b'{"event":"cancel"}\n');process.stdin.flush()
            except (BrokenPipeError,OSError,ValueError):pass
        sender=threading.Thread(target=cooperative,daemon=True);sender.start()
        try:process.wait(timeout=self.cooperative_seconds)
        except subprocess.TimeoutExpired:
            self._signal(process,signal.SIGTERM)
            try:process.wait(timeout=self.terminate_seconds)
            except subprocess.TimeoutExpired:
                self._signal(process,KILL_SIGNAL);process.wait(timeout=self.terminate_seconds)
        # Helpers inherit our dedicated process group; they cannot outlive the job.
        if os.name!='nt':self._signal(process,KILL_SIGNAL)
        sender.join(timeout=.1)

    def run(self,request,cancel,on_event,*,timeout=300):
        payload=(json.dumps(request,ensure_ascii=False,allow_nan=False)+'\n').encode()
        if len(payload)>MAX_LINE:raise RuntimeErrorCode('prompt_token_limit')
        with self._condition:
            if self._closed or self._process is not None:raise RuntimeErrorCode('runtime_unavailable')
            if self.executable is None or self.executable.is_symlink() or not self.executable.is_file():
                raise RuntimeErrorCode('runtime_unavailable')
            if cancel.is_set():raise InterruptedError()
            env=os.environ.copy()
            env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                       DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false')
            try:
                process=subprocess.Popen([str(self.executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,env=env,start_new_session=os.name!='nt',bufsize=0)
            except OSError:raise RuntimeErrorCode('runtime_unavailable') from None
            self._process=process
        lines=queue.Queue(maxsize=16);bad=threading.Event();done=threading.Event()
        write_lock=threading.Lock();write_error=threading.Event();result=None;child_error=None
        started=time.monotonic();deadline=started+timeout
        peak_rss=0;phase='starting_process';phase_start=started;stage_seconds={};group_cleaned=False
        observed=psutil.Process(process.pid)
        def read_stdout():
            try:
                while True:
                    line=process.stdout.readline(MAX_LINE+1)
                    if not line:break
                    if len(line)>MAX_LINE or not line.endswith(b'\n'):bad.set();break
                    try:lines.put(line,timeout=.1)
                    except queue.Full:bad.set();break
            finally:done.set()
        def read_stderr():
            total=0
            while chunk:=process.stderr.read(4096):
                total+=len(chunk)
                # Drain without recording content. Bound malicious or broken output.
                if total>MAX_LINE:bad.set();return
        def write_request():
            try:
                with write_lock:
                    remaining=memoryview(payload)
                    while remaining:
                        count=process.stdin.write(remaining)
                        if not count:raise BrokenPipeError()
                        remaining=remaining[count:]
                    process.stdin.flush()
            except (OSError,ValueError):write_error.set()
        readers=[threading.Thread(target=read_stdout,daemon=True),threading.Thread(target=read_stderr,daemon=True)]
        writer=threading.Thread(target=write_request,daemon=True)
        for thread in readers+[writer]:thread.start()
        try:
            while process.poll() is None or not done.is_set() or not lines.empty():
                if process.poll() is not None and os.name!='nt' and not group_cleaned:
                    self._signal(process,KILL_SIGNAL);group_cleaned=True
                try:peak_rss=max(peak_rss,observed.memory_info().rss)
                except psutil.Error:pass
                if cancel.is_set() or self._shutdown.is_set():
                    self._stop(process,write_lock);raise InterruptedError()
                if time.monotonic()>=deadline:
                    self._stop(process,write_lock);raise RuntimeErrorCode('timeout')
                if bad.is_set():
                    self._stop(process,write_lock);raise RuntimeErrorCode('output_invalid')
                if write_error.is_set() and process.poll() is not None:
                    raise RuntimeErrorCode('runtime_crashed')
                try:line=lines.get(timeout=.025)
                except queue.Empty:continue
                try:
                    event=json.loads(line,object_pairs_hook=_unique)
                    if not isinstance(event,dict):raise ValueError()
                    kind=event.get('event')
                    if kind=='result':
                        if result is not None or child_error is not None:raise ValueError()
                        result=event
                    elif kind=='error':
                        if child_error is not None or result is not None:raise ValueError()
                        code=event.get('code')
                        child_error='runtime_crashed' if code=='runtime_failed' else code if code in MESSAGES else 'output_invalid'
                    elif kind in {'stage','progress'} and result is None and child_error is None:
                        if kind=='stage' and event.get('stage') not in {'translating','loading_image_model','generating','releasing_resources'}:
                            raise ValueError()
                        if kind=='progress' and not (type(event.get('completed')) is int and type(event.get('total')) is int
                                and 0<=event['completed']<=event['total']<=4 and event['total']>0):raise ValueError()
                        if kind=='stage':
                            now=time.monotonic();stage_seconds[phase]=now-phase_start
                            phase=event['stage'];phase_start=now
                        on_event(event)
                    else:raise ValueError()
                except (ValueError,UnicodeError,TypeError):
                    raise RuntimeErrorCode('output_invalid') from None
            process.wait()
            if cancel.is_set() or self._shutdown.is_set():raise InterruptedError()
            if bad.is_set():raise RuntimeErrorCode('output_invalid')
            if child_error:raise RuntimeErrorCode(child_error)
            if process.returncode!=0 or result is None:raise RuntimeErrorCode('runtime_crashed')
            result['child_wall_seconds']=time.monotonic()-started
            stage_seconds[phase]=time.monotonic()-phase_start
            result['stage_seconds']=stage_seconds
            result['child_peak_rss_bytes']=peak_rss
            return result
        finally:
            if process.poll() is None:self._stop(process,write_lock)
            elif os.name!='nt':self._signal(process,KILL_SIGNAL)
            for stream in (process.stdin,process.stdout,process.stderr):
                try:stream.close()
                except OSError:pass
            for thread in readers+[writer]:thread.join(timeout=.1)
            with self._condition:
                if process.poll() is not None:self._process=None
                self._condition.notify_all()

    def probe(self,definition,model_dir,cancel):
        from .capabilities import generative_capabilities
        if not generative_capabilities(psutil.virtual_memory().total,self.executable is not None)['platform_supported']:
            raise RuntimeErrorCode('unsupported_platform')
        request={'operation':'probe','model_dir':str(model_dir),
                 'model_kind':'translation' if definition.runtime=='torch-cpu' else 'image'}
        result=self.run(request,cancel,lambda _:None,timeout=30)
        if result.get('metal') is not True or result.get('gpu_result')!=[2,4,6]:
            raise RuntimeErrorCode('output_invalid')
        if definition.runtime=='torch-cpu' and not result.get('translation_model_loaded'):
            raise RuntimeErrorCode('output_invalid')
        if definition.runtime=='mlx' and not result.get('image_model_loaded'):
            raise RuntimeErrorCode('output_invalid')
        return {'status':'passed','runtime':definition.runtime,'measured_at':datetime.now(timezone.utc).isoformat(),
                'seconds':result['child_wall_seconds'],'child_peak_rss_bytes':result['child_peak_rss_bytes'],
                'mlx_peak_bytes':result.get('mlx_peak_bytes'),'stage_seconds':result['stage_seconds'],
                'versions':result.get('versions')}

    def close(self):
        with self._condition:
            self._closed=True;self._shutdown.set()
            deadline=time.monotonic()+5
            while self._process is not None:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise RuntimeErrorCode('runtime_crashed')
                self._condition.wait(min(.1,remaining))


def validate_output(session,expected_size):
    """Only a regular, private, bare RGB PNG at the owner-selected path is eligible."""
    from PIL import Image
    path=Path(session)/'output.png'
    try:
        info=path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077
                or info.st_nlink!=1 or not 0<info.st_size<=16*1024**2):
            raise ValueError()
        with Image.open(path) as image:
            if image.format!='PNG' or image.mode!='RGB' or image.size!=expected_size or image.info:
                raise ValueError()
            image.load()
            return image.copy()
    except (OSError,ValueError):raise RuntimeErrorCode('output_invalid') from None
