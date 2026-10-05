import hashlib,json,struct,threading
from pathlib import Path
import pytest
from pixelmend_engine.generative_process import RuntimeErrorCode
from pixelmend_engine.generative_image_pipeline import run_image_pipeline,validate_latents


def write_latents(session,width=512,height=512):
    shape=[1,128,height//16,width//16];size=2*__import__('math').prod(shape)
    header=json.dumps({'packed_latents':{'dtype':'BF16','shape':shape,'data_offsets':[0,size]}}).encode()
    file=session/'latents.safetensors';file.write_bytes(struct.pack('<Q',len(header))+header+bytes(size));file.chmod(0o600)
    return file


def request(session):return {'operation':'generate','session_dir':str(session),'width':512,'height':512,'seed':7,'prompt':'synthetic'}


def test_phases_are_reaped_serial_and_memory_peaks_are_not_added(tmp_path):
    tmp_path.chmod(0o700);cancel=threading.Event()
    class Owner:
        active_pid=None
        def __init__(self):self.requests=[]
        def run(self,r,c,event,timeout):
            assert c is cancel and 0<timeout<=300
            self.requests.append(r)
            if r['image_phase']=='denoise':write_latents(tmp_path)
            else:
                assert len(self.requests)==2 and r['latent_sha256']==hashlib.sha256((tmp_path/'latents.safetensors').read_bytes()).hexdigest()
            return {'image_phase':r['image_phase'],'seed':7,'width':512,'height':512,'versions':{'mlx':'fixture'},'child_wall_seconds':1,'stage_seconds':{'generating':1},'child_peak_rss_bytes':3 if len(self.requests)==1 else 4,'child_peak_footprint_bytes':10 if len(self.requests)==1 else 7,'mlx_peak_bytes':6 if len(self.requests)==1 else 5}
    owner=Owner();result=run_image_pipeline(owner,request(tmp_path),cancel,lambda _:None)
    assert [r['image_phase'] for r in owner.requests]==['denoise','decode']
    assert result['child_peak_footprint_bytes']==10 and result['mlx_peak_bytes']==6
    assert result['stage_seconds']=={'denoise_generating':1,'decode_generating':1}
    assert not (tmp_path/'latents.safetensors').exists()


@pytest.mark.parametrize('kind',['symlink','size','dtype','shape','offset','shape_bool','offset_bool','nonfinite','duplicate','permissions'])
def test_latent_contract_rejects_unsafe_or_corrupt_data(tmp_path,kind):
    tmp_path.chmod(0o700);file=write_latents(tmp_path)
    if kind=='symlink':file.rename(tmp_path/'other');file.symlink_to(tmp_path/'other')
    elif kind=='size':file.write_bytes(file.read_bytes()+b'x')
    elif kind=='permissions':file.chmod(0o644)
    else:
        raw=file.read_bytes();length=struct.unpack('<Q',raw[:8])[0];header=json.loads(raw[8:8+length]);payload=raw[8+length:]
        if kind=='dtype':header['packed_latents']['dtype']='F32'
        if kind=='shape':header['packed_latents']['shape']=[1,128,31,32]
        if kind=='offset':header['packed_latents']['data_offsets'][0]=1
        if kind=='shape_bool':header['packed_latents']['shape'][0]=True
        if kind=='offset_bool':header['packed_latents']['data_offsets'][0]=False
        if kind=='nonfinite':payload=b'\x80\x7f'+payload[2:]
        encoded=json.dumps(header).encode()
        if kind=='duplicate':encoded=b'{"packed_latents":null,"packed_latents":'+json.dumps(header['packed_latents']).encode()+b'}'
        file.write_bytes(struct.pack('<Q',len(encoded))+encoded+payload)
    with pytest.raises(RuntimeErrorCode) as error:validate_latents(tmp_path,(512,512))
    assert error.value.code=='output_invalid'


def test_cancel_between_phases_prevents_decoder_and_cleans_latents(tmp_path):
    tmp_path.chmod(0o700);cancel=threading.Event()
    class Owner:
        active_pid=None
        calls=0
        def run(self,r,c,event,timeout):
            self.calls+=1;write_latents(tmp_path);cancel.set()
            return {'image_phase':'denoise','seed':7,'width':512,'height':512,'versions':{},'child_wall_seconds':1}
    owner=Owner()
    with pytest.raises(InterruptedError):run_image_pipeline(owner,request(tmp_path),cancel,lambda _:None)
    assert owner.calls==1 and not (tmp_path/'latents.safetensors').exists()


def test_one_deadline_covers_both_phases(tmp_path,monkeypatch):
    import pixelmend_engine.generative_image_pipeline as pipeline
    tmp_path.chmod(0o700);clock=[0.0];monkeypatch.setattr(pipeline.time,'monotonic',lambda:clock[0])
    class Owner:
        active_pid=None
        calls=0
        def run(self,r,c,event,timeout):
            self.calls+=1;assert timeout==300;write_latents(tmp_path);clock[0]=300
            return {'image_phase':'denoise','seed':7,'width':512,'height':512,'versions':{},'child_wall_seconds':300}
    owner=Owner()
    with pytest.raises(RuntimeErrorCode) as error:run_image_pipeline(owner,request(tmp_path),threading.Event(),lambda _:None)
    assert error.value.code=='timeout' and owner.calls==1
    assert not (tmp_path/'latents.safetensors').exists()


@pytest.mark.parametrize('kind',['invalid_latents','child_failed','wrong_seed','still_alive'])
def test_failed_denoise_never_starts_decoder(tmp_path,kind):
    tmp_path.chmod(0o700)
    class Owner:
        active_pid=None
        calls=0
        def run(self,r,c,event,timeout):
            self.calls+=1;file=write_latents(tmp_path)
            if kind=='invalid_latents':file.write_bytes(b'bad')
            if kind=='child_failed':raise RuntimeErrorCode('runtime_crashed')
            if kind=='still_alive':self.active_pid=42
            return {'image_phase':'denoise','seed':8 if kind=='wrong_seed' else 7,'width':512,'height':512,'versions':{},'child_wall_seconds':1}
    owner=Owner()
    with pytest.raises(RuntimeErrorCode):run_image_pipeline(owner,request(tmp_path),threading.Event(),lambda _:None)
    assert owner.calls==1 and not (tmp_path/'latents.safetensors').exists()


@pytest.mark.parametrize('missing_phase',['denoise','decode'])
def test_missing_phase_measurement_is_not_reported_as_complete_peak(tmp_path,missing_phase):
    tmp_path.chmod(0o700)
    class Owner:
        active_pid=None
        def run(self,r,c,event,timeout):
            if r['image_phase']=='denoise':write_latents(tmp_path)
            return {'image_phase':r['image_phase'],'seed':7,'width':512,'height':512,'versions':{},'child_wall_seconds':1,
                    'child_peak_footprint_bytes':None if r['image_phase']==missing_phase else 7,
                    'child_peak_rss_bytes':4,'mlx_peak_bytes':6}
    result=run_image_pipeline(Owner(),request(tmp_path),threading.Event(),lambda _:None)
    assert result['child_peak_footprint_bytes'] is None
    assert any(row['child_peak_footprint_bytes'] is None for row in result['phase_resources'])


@pytest.mark.parametrize('metadata',[None,{'prompt':'synthetic-private-content'}])
def test_native_null_metadata_is_accepted_but_content_metadata_is_rejected(tmp_path,metadata):
    tmp_path.chmod(0o700);file=write_latents(tmp_path);raw=file.read_bytes();length=struct.unpack('<Q',raw[:8])[0]
    header=json.loads(raw[8:8+length]);header['__metadata__']=metadata;encoded=json.dumps(header).encode()
    file.write_bytes(struct.pack('<Q',len(encoded))+encoded+raw[8+length:])
    if metadata is None:assert validate_latents(tmp_path,(512,512))==hashlib.sha256(file.read_bytes()).hexdigest()
    else:
        with pytest.raises(RuntimeErrorCode):validate_latents(tmp_path,(512,512))
