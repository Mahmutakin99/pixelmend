// Separate alpha output; existing RC assets and installed applications are never replaced.
const path=require('node:path');
const root=path.resolve(__dirname,'../..'),desktop=require('../../apps/desktop/package.json');
module.exports={...desktop.build,
 directories:{...desktop.build.directories,output:path.join(root,'.local-notes/generative/releases',desktop.version)},
 artifactName:'PixelMend-${version}-${arch}.${ext}',
 extraResources:[...desktop.build.extraResources,
  {from:path.join(root,'.local-notes/generative/dist/pixelmend-generative-runtime'),to:'generative-runtime'},
  {from:path.join(root,'THIRD_PARTY_NOTICES.md'),to:'THIRD_PARTY_NOTICES.md'},
 ],
 mac:{...desktop.build.mac,identity:process.env.CSC_NAME||null,hardenedRuntime:true,notarize:false,
  entitlements:'build/entitlements.generative.plist',entitlementsInherit:'build/entitlements.generative.plist'},
};
