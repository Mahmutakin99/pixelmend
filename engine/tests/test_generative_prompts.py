import threading
from pathlib import Path

import pytest

from pixelmend_engine.generative_prompts import PromptPreparer
from pixelmend_engine.generative_process import RuntimeErrorCode


class Owner:
    def __init__(self):self.requests=[];self.response={'english':'Add two white cats.'};self.active=False
    def run(self,request,cancel,progress,timeout):
        assert timeout==30 and not self.active
        self.requests.append(request);self.active=True
        progress({'event':'stage','stage':'translating'})
        self.active=False
        return self.response


def prepare(preparer,prompt='İki beyaz kedi ekle.',language='tr',override=None,revision='a'*40):
    return preparer.prepare(prompt,language,override,Path('/local/model'),revision,
                            threading.Event(),lambda _:None)


def test_revision_scoped_memory_cache_and_manual_english_bypass():
    owner=Owner();preparer=PromptPreparer(owner)
    first=prepare(preparer);assert first.english=='Add two white cats.' and not first.cached
    assert not owner.active
    second=prepare(preparer);assert second.cached and len(owner.requests)==1
    assert prepare(preparer,revision='b'*40).cached is False and len(owner.requests)==2
    override=prepare(preparer,override='Add one orange cat.')
    assert override.english=='Add one orange cat.' and len(owner.requests)==2
    direct=prepare(preparer,prompt='Add a cat.',language='en')
    assert direct.english=='Add a cat.' and len(owner.requests)==2
    preparer.clear();assert not prepare(preparer).cached and len(owner.requests)==3


@pytest.mark.parametrize('prompt',['','  ','ğ'*1001])
def test_source_limits_count_unicode_characters(prompt):
    owner=Owner();preparer=PromptPreparer(owner)
    with pytest.raises(RuntimeErrorCode) as error:prepare(preparer,prompt=prompt)
    assert error.value.code=='invalid_prompt' and owner.requests==[]
    assert prepare(preparer,prompt='🐈'*1000,language='en').english=='🐈'*1000


@pytest.mark.parametrize('response',[
    {'english':''},{'english':'İki beyaz kedi ekle.'},{'english':'<think>cat</think>'},
    {'english':'Here is the translation: Add cats.'},{'english':'Add cats.\nMore explanation.'},
    {'english':5},{},
])
def test_invalid_translations_are_not_cached_or_returned(response):
    owner=Owner();owner.response=response;preparer=PromptPreparer(owner)
    for _ in range(2):
        with pytest.raises(RuntimeErrorCode) as error:prepare(preparer)
        assert error.value.code=='invalid_translation'
    assert len(owner.requests)==2


def test_preparer_never_starts_another_process_on_translation_failure():
    owner=Owner()
    def failed(*_args,**_kwargs):raise RuntimeErrorCode('timeout')
    owner.run=failed;preparer=PromptPreparer(owner)
    with pytest.raises(RuntimeErrorCode) as error:prepare(preparer)
    assert error.value.code=='timeout'


def test_bounded_session_cache_and_cancelled_cache_hit():
    owner=Owner();preparer=PromptPreparer(owner,max_entries=2)
    for prompt in ['Bir kedi ekle.','İki kedi ekle.','Üç kedi ekle.']:prepare(preparer,prompt=prompt)
    assert not prepare(preparer,prompt='Bir kedi ekle.').cached
    cancel=threading.Event();cancel.set()
    with pytest.raises(InterruptedError):preparer.prepare('Bir kedi ekle.','tr',None,Path('/model'),
                                                       'a'*40,cancel,lambda _:None)
