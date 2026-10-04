"""Prepare a bounded local prompt; translations are cached only in this session."""
from collections import OrderedDict
from dataclasses import dataclass
import re
import threading
import time

from .generative_process import RuntimeErrorCode


@dataclass(frozen=True,slots=True)
class PreparedPrompt:
    original: str
    english: str
    language: str
    cached: bool
    seconds: float


def validate_user_prompt(value):
    if not isinstance(value,str) or not value.strip() or len(value)>1000:
        raise RuntimeErrorCode('invalid_prompt')
    return value.strip()


def validate_translated_prompt(value,source):
    if (not isinstance(value,str) or not value.strip() or '\n' in value or '\r' in value
            or '<' in value or '>' in value or value.strip().casefold()==source.casefold()
            or re.match(r'^(here (?:is|are)|the (?:english )?translation|translation:|english:)',value,re.I)):
        raise RuntimeErrorCode('invalid_translation')
    return value.strip()


class PromptPreparer:
    def __init__(self,owner,*,max_entries=128):
        if type(max_entries) is not int or max_entries<1:raise ValueError('invalid cache bound')
        self.owner=owner;self.max_entries=max_entries;self._cache=OrderedDict();self._mutex=threading.Lock()

    def clear(self):
        with self._mutex:self._cache.clear()

    def prepare(self,prompt,language,english_override,model_dir,revision,cancel,on_event):
        started=time.monotonic();source=validate_user_prompt(prompt)
        if language not in {'tr','en'}:raise RuntimeErrorCode('invalid_prompt')
        if cancel.is_set():raise InterruptedError()
        if english_override is not None:
            return PreparedPrompt(source,validate_user_prompt(english_override),language,False,time.monotonic()-started)
        if language=='en':return PreparedPrompt(source,source,language,False,time.monotonic()-started)
        if model_dir is None or not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}',revision):
            raise RuntimeErrorCode('model_not_installed')
        key=(revision,source)
        with self._mutex:
            english=self._cache.pop(key,None)
            if english is not None:self._cache[key]=english
        if english is not None:return PreparedPrompt(source,english,language,True,time.monotonic()-started)
        result=self.owner.run({'operation':'translate','model_dir':str(model_dir),'prompt':source},
                              cancel,on_event,timeout=30)
        if cancel.is_set():raise InterruptedError()
        english=validate_translated_prompt(result.get('english'),source)
        with self._mutex:
            self._cache[key]=english
            while len(self._cache)>self.max_entries:self._cache.popitem(last=False)
        return PreparedPrompt(source,english,language,False,time.monotonic()-started)
