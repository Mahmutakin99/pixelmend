import {useEffect,useState,useSyncExternalStore} from 'react';
import {GenerativeSession} from './generative-session';
export function useGenerative(){
 const [session]=useState(()=>new GenerativeSession(window.pixelmend));
 const state=useSyncExternalStore(session.subscribe,session.getSnapshot);
 useEffect(()=>()=>{void session.close();},[session]);
 return {session,...state};
}
