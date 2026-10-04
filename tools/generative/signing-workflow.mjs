/** The app must carry its ticket before creating the final ZIP for offline use. */
function submit(artifact,profile,run) {
 const output=run('xcrun',['notarytool','submit',artifact,'--keychain-profile',profile,'--wait','--output-format','json'],{capture:true});
 let response;try{response=JSON.parse(output);}catch{throw new Error('Invalid notarization response');}
 if(response.status!=='Accepted'||typeof response.id!=='string')throw new Error(`Notarization not accepted: ${response.status||'unknown'}`);
 return response.id;
}
export function notarizeApp({app,archive,profile,run}) {
 run('codesign',['--verify','--deep','--strict',app]);
 run('ditto',['-c','-k','--keepParent',app,archive]);
 const id=submit(archive,profile,run);
 run('xcrun',['stapler','staple',app]);
 run('xcrun',['stapler','validate',app]);
 run('spctl',['--assess','--type','execute','--verbose=2',app]);
 return id;
}
export function notarizeDmg({artifact,profile,run}) {
 const id=submit(artifact,profile,run);
 run('xcrun',['stapler','staple',artifact]);
 run('xcrun',['stapler','validate',artifact]);
 run('spctl',['--assess','--type','open','--context','context:primary-signature','--verbose=2',artifact]);
 return id;
}
