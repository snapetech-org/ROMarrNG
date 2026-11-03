#!/usr/bin/env python3
from pathlib import Path
import collections,hashlib,json
E=Path(__file__).resolve().parent
BASE='d1698b94781c3c84e91faf03c75e8c308dc39c34'
TREE='3f42d41fe4bbb8edd921ff161e8298ca66038a91'
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
cfm=json.loads((E/'candidate-free-input/manifest.json').read_text())
xm=json.loads((E/'cross-audit/manifest.json').read_text())
pins=json.loads((E/'candidate-free-input/catalog-file-pins.json').read_text())
assert (cfm['head'],cfm['tree'])==(BASE,TREE)
assert (xm['head'],xm['tree'])==(BASE,TREE)
cells=rows(E/'candidate-free-input/current-target-cells.jsonl')
ledger=rows(E/'cross-audit/resolution-ledger.jsonl')
assert len(cells)==len(ledger)==240
idx=lambda rs:{(r['position'],r['locale']):r for r in rs}
ci,li=idx(cells),idx(ledger)
assert ci.keys()==li.keys()
allplan=[];changes=[]
dispositions=collections.Counter();resolutions=collections.Counter()
for key in sorted(ci):
 c,l=ci[key],li[key]
 assert l['sourceId']==c['sourceId'] and l['source']==c['source']
 assert l['sourceSha256']==c['sourceSha256'] and l['currentTarget']==c['currentTarget']
 assert l['currentTargetSha256']==c['currentTargetSha256']
 assert l['callerContextSha256']==c['callerContextSha256']
 assert l['selectedTargetSha256']==hashlib.sha256(l['selectedTarget'].encode()).hexdigest()
 checks=l['tokenAndMarkupChecks']
 assert checks['placeholderMultisetPreserved'] and checks['numberSequencePreserved']
 assert checks['protectedLiteralsPreserved'] and checks['noUnexpectedMarkup'] and checks['callerMarkupBoundaryPreserved']
 disp=l['selectedDisposition'];dispositions[disp]+=1
 resolutions[l['resolution']]+=1
 assert disp in ('accept-current','correction','refinement')
 assert c['catalogPath']=='romarr/ui-labels.json'
 assert c['catalogTranslationHash']
 assert l['selectedTarget']==c['currentTarget'] if disp=='accept-current' else l['selectedTarget']!=c['currentTarget']
 row={'position':c['position'],'locale':c['locale'],'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],'catalogPath':c['catalogPath'],'catalogTranslationHash':c['catalogTranslationHash'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'selectedTarget':l['selectedTarget'],'selectedTargetSha256':l['selectedTargetSha256'],'selectedDisposition':disp,'resolution':l['resolution'],'callerContextAmbiguous':l['callerContextAmbiguous'],'translationStatus':c['translationStatus']}
 row['changed']=row['selectedTarget']!=row['currentTarget']
 allplan.append(row)
 if row['changed']: changes.append(row)
assert dispositions==collections.Counter({'accept-current':125,'correction':75,'refinement':40}),dispositions
assert resolutions==collections.Counter({'agreement':74,'primary_selected':154,'blind_selected':12}),resolutions
assert len(changes)==115
assert pins['catalogSha256']=='e1201ad91db764caaabf12bac3682341d9ad7a1282e4c90b059863e3e1aa7ebc'
assert len({x['sourceId'] for x in cells})==20
assert sum(x['callerContextAmbiguous'] for x in allplan)==12
doc={'schemaVersion':1,'repository':'snapetech-org/romarrng','pullRequest':70,'branch':'task/localization-translation-review-20261030','baseHead':BASE,'baseTree':TREE,'reviewedCells':240,'decisionCounts':dict(sorted(dispositions.items())),'crossAuditResolutionCounts':dict(sorted(resolutions.items())),'changedCells':115,'catalogPath':'romarr/ui-labels.json','catalogFileSha256':pins['catalogSha256'],'updates':changes,'allCellReadbackPlan':allplan,'priorHoldsExpected':288,'newHolds':0}
(E/'apply-plan.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':True,'cells':240,'decisions':dict(dispositions),'resolutions':dict(resolutions),'updates':len(changes),'ambiguousRank368Cells':12},indent=2))
