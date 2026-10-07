"""Serial denoise/decode workers; native tensors cannot span the process boundary."""
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import struct
import time

from .generative_process import RuntimeErrorCode, _unique


def validate_latents(session, dimensions):
    session=Path(session);path=session/'latents.safetensors'
    try:
        parent=session.lstat()
        if (not session.is_absolute() or not stat.S_ISDIR(parent.st_mode)
                or parent.st_uid!=os.getuid() or parent.st_mode&0o077):raise ValueError()
        width,height=dimensions
        if (type(width) is not int or type(height) is not int or min(width,height)<=0
                or max(width,height)>1024 or width*height>1024*768
                or width%16 or height%16):raise ValueError()
        shape=[1,128,height//16,width//16];payload_size=math.prod(shape)*2
        with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
            info=os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                    or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1
                    or not 8+payload_size<info.st_size<=8+4096+payload_size):raise ValueError()
            data=stream.read(8+4096+payload_size+1)
        if len(data)!=info.st_size:raise ValueError()
        length=struct.unpack('<Q',data[:8])[0]
        if not 0<length<=4096 or len(data)!=8+length+payload_size:raise ValueError()
        header=json.loads(data[8:8+length],object_pairs_hook=_unique)
        if isinstance(header,dict) and '__metadata__' in header:
            if header.pop('__metadata__') is not None:raise ValueError()
        if header!={'packed_latents':{'dtype':'BF16','shape':shape,'data_offsets':[0,payload_size]}}:raise ValueError()
        if any(type(value) is not int for value in header['packed_latents']['shape']+header['packed_latents']['data_offsets']):raise ValueError()
        import numpy as np
        values=np.frombuffer(data[8+length:],dtype='<u2')
        if np.any((values&0x7f80)==0x7f80):raise ValueError()
        return hashlib.sha256(data).hexdigest()
    except (OSError,ValueError,TypeError,struct.error):
        raise RuntimeErrorCode('output_invalid') from None


def run_image_pipeline(owner,request,cancel,on_event,*,timeout=300,memory_gate=None):
    started=time.monotonic();session=Path(request['session_dir']);latent=session/'latents.safetensors'
    if latent.exists() or latent.is_symlink():raise RuntimeErrorCode('output_invalid')
    phases=[]
    try:
        for phase in ('denoise','decode'):
            if cancel.is_set():raise InterruptedError()
            if memory_gate is not None:memory_gate.wait(cancel,on_event)
            remaining=timeout-(time.monotonic()-started) if timeout is not None else None
            if remaining is not None and remaining<=0:raise RuntimeErrorCode('timeout')
            child=request|{'image_phase':phase}
            if phase=='decode':child['latent_sha256']=validate_latents(session,(request['width'],request['height']))
            while True:
                available=memory_gate.resources()['available_memory_bytes'] if memory_gate is not None else 0
                try:
                    result=owner.run(child,cancel,on_event,timeout=remaining)
                    break
                except RuntimeErrorCode as error:
                    if error.code!='memory_exhausted' or memory_gate is None:raise
                    # Retry only this phase, after a real increase in free resources.
                    # A completed denoise checkpoint survives decode allocation failure.
                    if phase=='denoise':latent.unlink(missing_ok=True)
                    (session/'output.png').unlink(missing_ok=True)
                    recovered=memory_gate.resources()['available_memory_bytes']
                    # A return to the previously launchable baseline is enough.
                    # Never demand more RAM than was available before the failure.
                    minimum=min(available,recovered+256*1024**2)
                    memory_gate.wait(cancel,on_event,minimum_available=minimum,force_recovery=True)
            if owner.active_pid is not None:raise RuntimeErrorCode('runtime_crashed')
            if (result.get('image_phase')!=phase or any(result.get(key)!=request[key]
                    for key in ('seed','width','height'))):raise RuntimeErrorCode('output_invalid')
            if phases and result.get('versions')!=phases[0].get('versions'):raise RuntimeErrorCode('unsupported_runtime')
            phases.append(result)
        if cancel.is_set():raise InterruptedError()
        result=phases[-1].copy()
        result['elapsed_seconds']=time.monotonic()-started
        result['child_wall_seconds']=sum(row['child_wall_seconds'] for row in phases)
        result['stage_seconds']={phase+'_'+key:value for phase,row in zip(('denoise','decode'),phases)
                                 for key,value in row.get('stage_seconds',{}).items()}
        for key in ('child_peak_rss_bytes','child_peak_footprint_bytes','mlx_peak_bytes'):
            values=[row.get(key) for row in phases]
            result[key]=max(values) if all(value is not None for value in values) else None
        result['phase_resources']=[{key:row.get(key) for key in ('image_phase','child_wall_seconds',
            'child_peak_rss_bytes','child_peak_footprint_bytes','mlx_peak_bytes')} for row in phases]
        return result
    finally:
        latent.unlink(missing_ok=True)
