import test from 'node:test';
import assert from 'node:assert/strict';
import {notarizeApp, notarizeDmg} from './signing-workflow.mjs';

test('staples and validates the app before it can enter a distribution ZIP', () => {
 const calls=[];
 const run=(command,args)=>{calls.push([command,...args]);return command==='xcrun'&&args[0]==='notarytool'?JSON.stringify({status:'Accepted',id:'submission'}):'';};
 notarizeApp({app:'/output/PixelMend.app',archive:'/output/notary.zip',profile:'keychain-profile',run});
 assert.deepEqual(calls,[
  ['codesign','--verify','--deep','--strict','/output/PixelMend.app'],
  ['ditto','-c','-k','--keepParent','/output/PixelMend.app','/output/notary.zip'],
  ['xcrun','notarytool','submit','/output/notary.zip','--keychain-profile','keychain-profile','--wait','--output-format','json'],
  ['xcrun','stapler','staple','/output/PixelMend.app'],
  ['xcrun','stapler','validate','/output/PixelMend.app'],
  ['spctl','--assess','--type','execute','--verbose=2','/output/PixelMend.app'],
 ]);
});
test('a rejected notarization never staples or reports acceptance',()=>{
 const calls=[];
 assert.throws(()=>notarizeDmg({artifact:'/output/app.dmg',profile:'profile',run:(command,args)=>{calls.push(args);return JSON.stringify({status:'Invalid',id:'rejected'});}}),/Invalid/);
 assert.equal(calls.length,1);
});
test('a malformed notarization response stops distribution',()=>{
 assert.throws(()=>notarizeDmg({artifact:'/output/app.dmg',profile:'profile',run:()=>'{'}),/notarization response/);
});
