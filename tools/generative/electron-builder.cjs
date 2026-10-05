// Separate alpha output; existing RC assets and installed applications are never replaced.
const path=require('node:path');
const root=path.resolve(__dirname,'../..'),desktop=require('../../apps/desktop/package.json');
module.exports={...desktop.build,
 directories:{...desktop.build.directories,output:path.join(root,'.local-notes/generative/releases',desktop.version)},
 dmg:{...desktop.build.dmg,sign:true},
 artifactName:'PixelMend-${version}-${arch}.${ext}',
 extraResources:[...desktop.build.extraResources,
  {from:path.join(root,'.local-notes/generative/dist/pixelmend-generative-runtime'),to:'generative-runtime'},
  {from:path.join(root,'THIRD_PARTY_NOTICES.md'),to:'THIRD_PARTY_NOTICES.md'},
 ],
 mac:{...desktop.build.mac,identity:process.env.CSC_NAME||null,hardenedRuntime:true,notarize:false,
  // osx-sign's binary heuristic mistakes emoji-heavy Python text for binary code.
  // These resources remain protected by the outer app seal; native code is signed.
  signIgnore:['/Contents/Resources/(?:generative-runtime|engine)/.*\\.(?:py|pyi|pyc|pyo|pyz|h|hpp|c|cc|cpp|json|txt|md|rst|safetensors|npy|npz|zip|a|cmake|html|css|js|svg|png|jpg|jpeg|gif|xml|yaml|yml|csv|map|dat|tiktoken)$'],
  entitlements:'build/entitlements.generative.plist',entitlementsInherit:'build/entitlements.generative.plist'},
};
