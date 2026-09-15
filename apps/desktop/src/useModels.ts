import {useEffect,useState} from 'react';
import type {Capabilities,ModelView} from './models';
import './bridge';
// Keep model observations alive across home/editor navigation; unmount owns the subscription.
export function useModels() {
  const [models,setModels]=useState<ModelView[]>([]);
  const [capabilities,setCapabilities]=useState<Capabilities>();
  const [error,setError]=useState('');
  const refresh=async()=>{
    try { const [snapshot,host]=await Promise.all([window.pixelmend.models(),window.pixelmend.capabilities()]);setModels(snapshot.models);setCapabilities(host);setError(''); }
    catch(error){setError(`Model bilgileri alınamadı: ${String(error)}`);}
  };
  useEffect(()=>{let live=true;const off=window.pixelmend.onModels(snapshot=>{if(live)setModels(snapshot.models);});void refresh();return()=>{live=false;off();};},[]);
  return {models,capabilities,error,refresh};
}
