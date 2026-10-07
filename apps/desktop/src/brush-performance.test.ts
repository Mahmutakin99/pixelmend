import {it,expect} from 'vitest';
import * as brush from './brush';
it('scales brush style without mapping a long stroke on pointer move',()=>{
 const points=Array.from({length:8000},(_,x)=>({x,y:1}));
 Object.defineProperty(points,'map',{value:()=>{throw new Error('whole stroke mapped');}});
 const stroke={id:'a',mode:'draw' as const,points,color:'#ff0000',opacity:.5,size:20,hardness:1};
 const scaled=brush.previewBrush(stroke,.5);
 expect(scaled.size).toBe(10);expect(scaled.points).toBe(points);
});
