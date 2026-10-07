import {useEffect,useState,useRef,useCallback} from 'react';
import type {Capabilities,ModelView} from './models';
import {observeModels} from './model-observer';
import './bridge';
// Keep model observations alive across home/editor navigation; unmount owns the subscription.
export function useModels() {
 const [models,setModels]=useState<ModelView[]>([]);
 const [capabilities,setCapabilities]=useState<Capabilities>();
 const [error,setError]=useState('');
 const observer=useRef<ReturnType<typeof observeModels>|undefined>(undefined);
 const refresh=useCallback(async()=>{await observer.current?.refresh();},[]);
 useEffect(()=>{const current=observeModels(window.pixelmend,setModels,setCapabilities,setError);observer.current=current;void current.refresh();return()=>{current.close();if(observer.current===current)observer.current=undefined;};},[]);
 return {models,capabilities,error,refresh};
}
