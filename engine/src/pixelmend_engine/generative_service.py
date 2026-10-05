"""Local prompt/image pipeline and measured-profile admission. No model imports."""
from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import time

import numpy as np
from PIL import Image
import psutil

from .capabilities import generative_capabilities, _mac_sysctl
from .generative_edit import prepare_edit,composite_edit
from .generative_image_pipeline import run_image_pipeline
from .generative_process import RuntimeErrorCode,validate_output
from .generative_prompts import PromptPreparer,validate_user_prompt
from .model_manager import ModelManagerError
from .model_package import ModelPackageError
from .imageio import load_image
from .policy import POLICY
from .strokes import validate_strokes,StrokeValidationError

IMAGE_PACKAGE='flux2-klein-4b-mlx-q4'
TRANSLATION_PACKAGE='opus-mt-tc-big-tr-en-f16'
GIB=1024**3
SIZES={'low-resource':{'square':(512,512),'landscape':(640,480),'portrait':(480,640)},
       'balanced':{'square':(768,768),'landscape':(1024,768),'portrait':(768,1024)}}
RUNTIME_VERSIONS={'mflux':'0.21.0','mlx':'0.32.2','mlx-lm':'0.32.0'}


@dataclass(frozen=True,slots=True)
class GenerativeRequest:
    operation:str
    prompt:str
    prompt_language:str
    profile:str
    seed:int
    english_override:str|None=None
    aspect:str='square'
    asset_id:str|None=None
    selection_strokes:list|None=None
    paint_strokes:list|None=None

    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict):raise RuntimeErrorCode('invalid_request')
        operation=value.get('operation')
        common={'operation','prompt','prompt_language','profile','seed','english_override'}
        specific={'asset_id','selection_strokes','paint_strokes'} if operation=='text_edit' else {'aspect'}
        if not isinstance(operation,str) or operation not in {'text_edit','text_to_image'} or set(value)-common-specific:
            raise RuntimeErrorCode('invalid_request')
        prompt=validate_user_prompt(value.get('prompt'));language=value.get('prompt_language','tr')
        profile=value.get('profile');seed=value.get('seed',secrets.randbits(32))
        if (not isinstance(language,str) or language not in {'tr','en'}
                or not isinstance(profile,str) or profile not in SIZES
                or type(seed) is not int or not 0<=seed<2**32):
            raise RuntimeErrorCode('invalid_request')
        override=validate_user_prompt(value['english_override']) if 'english_override' in value else None
        if operation=='text_to_image':
            aspect=value.get('aspect','square')
            if not isinstance(aspect,str) or aspect not in SIZES[profile]:raise RuntimeErrorCode('invalid_request')
            return cls(operation,prompt,language,profile,seed,override,aspect)
        asset=value.get('asset_id');selection=value.get('selection_strokes');paint=value.get('paint_strokes')
        if (not isinstance(asset,str) or not re.fullmatch('[0-9a-f]{32}',asset)
                or not isinstance(selection,list) or not isinstance(paint,list)):
            raise RuntimeErrorCode('invalid_request')
        return cls(operation,prompt,language,profile,seed,override,'square',asset,deepcopy(selection),deepcopy(paint))

    @property
    def dimensions(self):return SIZES[self.profile][self.aspect]

    @property
    def needs_translation(self):return self.prompt_language=='tr' and self.english_override is None


class GenerativeService:
    def __init__(self,assets,packages,owner,*,session_parent,host_provider=None):
        self.assets=assets;self.packages=packages;self.owner=owner
        self.session_parent=session_parent;self.host_provider=host_provider or self._host
        self.prompts=PromptPreparer(owner)

    def _host(self):
        memory=psutil.virtual_memory();executable=self.owner.executable
        facts=generative_capabilities(memory.total,executable is not None and executable.is_file())
        parent=Path(self.session_parent() or tempfile.gettempdir())
        while not parent.exists():parent=parent.parent
        facts.update(hardware_class=_mac_sysctl('hw.model'),available_memory_bytes=memory.available,
                     disk_free_bytes=shutil.disk_usage(parent).free)
        return facts

    def required_packages(self,request):
        return (IMAGE_PACKAGE,TRANSLATION_PACKAGE) if request.needs_translation else (IMAGE_PACKAGE,)

    def _profile(self,request,host):
        definition=self.packages.catalog[IMAGE_PACKAGE]
        return next((p for p in definition.accepted_profiles if p['profile']==request.profile
                     and p['hardware_class']==host['hardware_class']),None)

    def preflight(self,request,*,result_bytes=0,result_budget=None,check_selection=True):
        width,height=request.dimensions
        report={'ready':False,'reason':None,'profile':request.profile,'width':width,'height':height,
                'runtime':'mlx','seed':request.seed}
        def reject(code):
            error=RuntimeErrorCode(code);report['reason']={'code':error.code,'message':str(error)};return report
        host=self.host_provider()
        if not host['platform_supported']:return reject('unsupported_platform')
        if not host['runtime_installed']:return reject('runtime_unavailable')
        profile=self._profile(request,host)
        if profile is None:return reject('profile_not_accepted')
        for id in self.required_packages(request):
            definition=self.packages.catalog[id]
            try:
                _,target,_=self.packages._paths(definition)
                if not target.is_dir():return reject('model_not_installed')
            except ModelPackageError:return reject('model_not_installed')
            view=next(v for v in self.packages.list_models()['models'] if v['id']==id)
            if view['state'] in {'waiting','downloading','installing','verifying','probing','cancelling','deleting'}:
                return reject('package_in_use')
        source=self.assets.get_image(request.asset_id) if request.asset_id else None
        pixels=source.width*source.height if source else width*height
        channels=4 if source is not None and source.alpha is not None else 3
        output_bytes=pixels*channels
        budget=POLICY.result_budget_bytes if result_budget is None else result_budget
        if output_bytes+result_bytes>budget:return reject('result_budget')
        count,capacity=self.assets.available_capacity
        # Worst-case PNG thumbnail is bounded at2048²; reserve an opaque asset slot.
        if count<1 or output_bytes+min(pixels,2048**2)*4+65536>capacity:return reject('asset_capacity')
        # Profile working memory is measured for a model child, never RSS+GPU.
        # Source storage is already in current available RAM. Account separately
        # for parent masks/paint retained during the child and source-size compose.
        retained=pixels*4 if source is not None and request.paint_strokes else pixels if source else 0
        model_required=math.ceil(profile['working_memory_bytes']*1.2)+retained
        compose_required=pixels*48 if source is not None else pixels*12
        required=max(model_required,compose_required)+2*GIB+64*1024**2
        report['required_available_memory_bytes']=required
        if host['available_memory_bytes']<required:return reject('memory_insufficient')
        if host['disk_free_bytes']<width*height*12+64*1024**2:return reject('disk_insufficient')
        if source is not None and check_selection:
            try:
                validate_strokes(request.selection_strokes,source.width,source.height)
                validate_strokes(request.paint_strokes,source.width,source.height)
                prepare_edit(source,request.selection_strokes,request.paint_strokes,request.profile)
            except StrokeValidationError:return reject('selection_invalid')
            except RuntimeErrorCode as error:return reject(error.code)
        report['ready']=True
        return report

    def ensure_ready(self,request,**kwargs):
        report=self.preflight(request,**kwargs)
        if not report['ready']:raise RuntimeErrorCode(report['reason']['code'])
        return report

    def reserve(self,request):
        reservations=[]
        try:
            for id in self.required_packages(request):reservations.append(self.packages.reserve(id))
            return reservations
        except BaseException:
            for reservation in reservations:reservation.release()
            raise

    def execute(self,request,reservations,cancel,on_event,*,result_bytes=0,result_budget=None):
        started=time.monotonic();timings={}
        self.ensure_ready(request,result_bytes=result_bytes,result_budget=result_budget,check_selection=False)
        if cancel.is_set():raise InterruptedError()
        on_event({'event':'stage','stage':'validating_models'})
        verify_started=time.monotonic()
        for reservation in reservations:reservation.verify(cancel)
        paths={r.id:r.path for r in reservations};timings['validating_models']=time.monotonic()-verify_started
        source=self.assets.get_image(request.asset_id) if request.asset_id else None
        plan=None
        if source is not None:
            on_event({'event':'stage','stage':'preparing_edit'});prepare_started=time.monotonic()
            plan=prepare_edit(source,request.selection_strokes,request.paint_strokes,request.profile)
            timings['preparing_edit']=time.monotonic()-prepare_started
        on_event({'event':'stage','stage':'preparing_prompt'})
        try:
            prepared=self.prompts.prepare(request.prompt,request.prompt_language,request.english_override,
                paths.get(TRANSLATION_PACKAGE),self.packages.catalog[TRANSLATION_PACKAGE].manifest.revision,
                cancel,on_event)
        finally:
            if TRANSLATION_PACKAGE in paths:self.packages._change(TRANSLATION_PACKAGE,loaded=False)
        timings['translation']=prepared.seconds
        if cancel.is_set():raise InterruptedError()
        # Recheck mutable resources after cold translation, before image loading.
        self.ensure_ready(request,result_bytes=result_bytes,result_budget=result_budget,check_selection=False)
        parent=Path(self.session_parent() or tempfile.gettempdir())
        parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        used_prompt=plan.model_prompt(prepared.english) if plan else prepared.english
        width,height=request.dimensions
        with tempfile.TemporaryDirectory(prefix='generative-',dir=parent) as temporary:
            session=Path(temporary);session.chmod(0o700)
            if plan is not None:
                with (session/'input.png').open('xb') as stream:
                    (session/'input.png').chmod(0o600);Image.fromarray(plan.input_rgb).save(stream,format='PNG')
            try:
                result=run_image_pipeline(self.owner,{'operation':'edit' if plan else 'generate','model_dir':str(paths[IMAGE_PACKAGE]),
                    'session_dir':str(session),'prompt':used_prompt,'seed':request.seed,'width':width,'height':height},
                    cancel,on_event,timeout=300)
                generated=validate_output(session,(width,height))
            finally:
                for id in paths:self.packages._change(id,loaded=False)
            if cancel.is_set():raise InterruptedError()
            on_event({'event':'stage','stage':'compositing'});compose_started=time.monotonic()
            if plan:output=composite_edit(plan,np.asarray(generated))
            else:
                buffer=BytesIO();generated.save(buffer,format='PNG');buffer.seek(0);output=load_image(buffer)
            timings['compositing']=time.monotonic()-compose_started
        if cancel.is_set():raise InterruptedError()
        timings.update({f'image_{key}':value for key,value in result.get('stage_seconds',{}).items()})
        image_definition=self.packages.catalog[IMAGE_PACKAGE]
        metadata={'algorithm':request.operation,'operation':request.operation,'runtime':'mlx','provider':None,
            'model_id':IMAGE_PACKAGE,'model_revision':image_definition.manifest.revision,
            'model_source_revision':image_definition.source_revision,'runtime_versions':RUNTIME_VERSIONS,
            'seed':request.seed,'profile':request.profile,'aspect':request.aspect,
            'original_prompt':request.prompt,'used_prompt':used_prompt,'translated_prompt':prepared.english,
            'prompt_language':request.prompt_language,'translation_cached':prepared.cached,
            'input_width':source.width if source else None,'input_height':source.height if source else None,
            'seconds':time.monotonic()-started,'stage_seconds':timings,
            'resources':{'child_peak_rss_bytes':result.get('child_peak_rss_bytes'),
                         'mlx_peak_bytes':result.get('mlx_peak_bytes'),
                         'child_peak_footprint_bytes':result.get('child_peak_footprint_bytes'),
                         'phase_resources':result.get('phase_resources')}}
        return output,metadata

    def close(self):self.prompts.clear()
