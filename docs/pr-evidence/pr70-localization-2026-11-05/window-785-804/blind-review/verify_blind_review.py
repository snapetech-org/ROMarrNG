#!/usr/bin/env python3
"""Verify blind review using only its output and the sealed candidate-free packet."""
import collections,hashlib,json,pathlib,re,sys

HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'; TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'; WINDOW='W785-W804'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']
OUT=pathlib.Path(__file__).resolve().parent
def fail(x): print('FAIL:',x);sys.exit(1)
def need(x,m):
    if not x: fail(m)
def sha(x):
    if isinstance(x,str):x=x.encode('utf-8')
    return hashlib.sha256(x).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def sums(root):
    root=pathlib.Path(root);listed={}
    for ln in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not ln.strip():continue
        h,n=ln.split('  ',1);n=n.removeprefix('./');p=(root/n).resolve()
        need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p.read_bytes())==h and n not in listed,'checksum '+n)
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt'}
    need(set(listed)==actual,'checksum coverage '+str(root))
    return listed
def protected(s):
    out=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok:out.append(lit)
    return sorted(set(out))
def token_audit(source,target):
    sp,tp=PH.findall(source),PH.findall(target);sm,tm=TAG.findall(source),TAG.findall(target);sn,tn=NUM.findall(source),NUM.findall(target);sl=protected(source)
    return {'sourcePlaceholders':sp,'targetPlaceholders':tp,'placeholdersMatch':collections.Counter(sp)==collections.Counter(tp),'sourceMarkup':sm,'targetMarkup':tm,'markupMatches':collections.Counter(sm)==collections.Counter(tm),'sourceNumbers':sn,'targetNumbers':tn,'numbersMatch':collections.Counter(sn)==collections.Counter(tn),'sourceProtectedLiterals':sl,'missingProtectedLiterals':[x for x in sl if x not in target],'protectedLiteralsMatch':all(x in target for x in sl)}
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--candidate-free',required=True,type=pathlib.Path);cf=ap.parse_args().candidate_free.resolve();inp=cf/'input'
    need(sums(cf) is not None,'candidate-free outer checksums');need(sums(inp) is not None,'candidate-free input checksums');outfiles=sums(OUT)
    m=rj(inp/'manifest.json');need((m.get('head'),m.get('tree'),m.get('window'),m.get('cellCount'),m.get('callerBackedCells'),m.get('callerlessHashOnlyCells'))==(HEAD,TREE,WINDOW,240,192,48),'candidate-free exact pin/count')
    need(m.get('proposedTargetsIncluded') is False and m.get('reviewDecisionsIncluded') is False,'candidate-free contains decisions')
    pins=rj(OUT/'input-pins.json')
    pinned_dir=(OUT/pins.get('candidateFreeDirectory','')).resolve()
    need(pinned_dir==cf and (pins.get('head'),pins.get('tree'),pins.get('window'))==(HEAD,TREE,WINDOW),'input pin identity')
    for key,path in [('candidateFreeOuterChecksumListSha256',cf/'SHA256SUMS.txt'),('candidateFreeInputChecksumListSha256',inp/'SHA256SUMS.txt'),('candidateFreeManifestSha256',inp/'manifest.json'),('candidateFreeCellsSha256',inp/'candidate-free-cells.jsonl'),('candidateFreeSourceContextsSha256',inp/'source-contexts.jsonl'),('candidateFreePriorActiveHoldsSha256',inp/'prior-active-holds-hash-only.jsonl')]:need(pins.get(key)==sha(path.read_bytes()),'input pin hash '+key)
    need(pins.get('candidateFreeChecksumsVerified') is True and pins.get('candidateFreeReviewInputOnly') is True and pins.get('primaryOrOtherProposalPacketsInspected') is False and pins.get('blindReviewerDidNotInspectProductWorktree') is True,'review provenance')
    cfrows=rjl(inp/'candidate-free-cells.jsonl');ledger=rjl(OUT/'blind-review-ledger.jsonl');need((len(cfrows),len(ledger))==(240,240),'ledger rows')
    cfmap={(r['sourceId'],r['locale']):r for r in cfrows};need(len(cfmap)==240,'candidate-free cell duplicates')
    ctx={r['sourceId']:r for r in rjl(inp/'source-contexts.jsonl')}
    need([(r['catalogZeroBasedIndex'],r['locale']) for r in cfrows]==[(i,l) for i in range(785,805) for l in LOCALES],'candidate-free cell order')
    holds=[];hashes=[];dec=collections.Counter();seen=set();token_mismatch=collections.Counter()
    for r in ledger:
        key=(r['sourceId'],r['locale']);need(key in cfmap and key not in seen,'ledger key missing/duplicate');seen.add(key);c=cfmap[key]
        need(r.get('sourceId')==c['sourceId'] and r.get('sourceSha256')==c['sourceSha256'] and r.get('callerContextSha256')==c['callerContextSha256'],'ledger source/context binding')
        need(r.get('candidateFreeCellRecordSha256')==sha(canon(c)),'candidate-free cell fingerprint')
        if c.get('callerless'):
            holds.append(r);dec['hold-hash-only']+=1
            need(r.get('decision')=='hold-hash-only' and r.get('textOmitted') is True,'hold decision/status')
            need(not any(k in r for k in ('source','currentTarget','blindTarget','proposedTarget','proposedTargetSha256')),'callerless blind text leak')
            need(r.get('currentTargetSha256')==c['currentTargetSha256'] and r.get('rationale')=='No pinned production caller; preserve the callerless hash-only hold.','hold hash/rationale')
            need(c.get('sourceTextOmitted') is True and c.get('currentTargetTextOmitted') is True,'candidate-free callerless input text')
            continue
        need(r.get('decision') in ('accept-current','revise'),'caller-backed disposition')
        need(r.get('source')==c['source'] and r.get('currentTarget')==c['currentTarget'] and r.get('currentTargetSha256')==c['currentTargetSha256'],'caller-backed input text/hash')
        target=r.get('blindTarget');need(isinstance(target,str) and r.get('blindTargetSha256')==sha(target),'blind target hash')
        need(r.get('nativeSpeakerApproval') is False and r.get('confidence') in ('high','moderate','low'),'confidence/approval')
        actual=token_audit(c['source'],target);need(actual==r.get('tokenAudit'),'token audit content')
        for test,category in [('placeholdersMatch','placeholder'),('markupMatches','markup'),('numbersMatch','numeric'),('protectedLiteralsMatch','protectedLiteral')]:token_mismatch[category]+=not actual[test]
        if r['decision']=='accept-current':
            dec['accept-current']+=1;need(target==c['currentTarget'] and 'proposedTarget' not in r,'accept-current target')
        else:
            dec['revise']+=1;need(target==r.get('proposedTarget') and r.get('proposedTargetSha256')==sha(target),'proposal target/hash')
        need(r.get('blindTargetSha256')==r.get('currentTargetSha256') if r['decision']=='accept-current' else True,'accepted target hash equals current')
        hashes.append({'sourceId':r['sourceId'],'locale':r['locale'],'decision':r['decision'],'currentTargetSha256':r['currentTargetSha256'],'blindTargetSha256':r['blindTargetSha256'],'proposedTargetSha256':r.get('proposedTargetSha256')})
    need(len(seen)==240 and len(holds)==48 and dec['accept-current']+dec['revise']==192,'cell disposition totals')
    need(hashes==[{k:r.get(k) for k in ('sourceId','locale','decision','currentTargetSha256','blindTargetSha256','proposedTargetSha256')} for r in rjl(OUT/'independent-target-hashes.jsonl')],'target hash ledger crosscheck')
    new_hold_file=rjl(OUT/'current-window-holds-hash-only.jsonl');need(len(new_hold_file)==48,'current hold file count')
    for r in new_hold_file:need(not any(k in r for k in ('source','currentTarget','blindTarget','proposedTarget')),'current hold file text leak')
    need([(r['sourceId'],r['locale']) for r in new_hold_file]==[(r['sourceId'],r['locale']) for r in holds],'current hold file keys')
    prior=rjl(OUT/'prior-active-holds-hash-only.jsonl');need(len(prior)==1012 and len({(r['sourceId'],r['locale']) for r in prior})==1012,'prior hold lineage')
    need(sha((OUT/'prior-active-holds-hash-only.jsonl').read_bytes())==sha((inp/'prior-active-holds-hash-only.jsonl').read_bytes()),'prior hold file copied exactly')
    for r in prior:need(not any(k in r for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')),'prior hold text leak')
    summary=rj(OUT/'summary.json');need((summary.get('head'),summary.get('tree'),summary.get('window'),summary.get('cellCount'),summary.get('callerBackedCells'),summary.get('currentWindowHashOnlyHolds'),summary.get('priorActiveHashOnlyHolds'),summary.get('resultingActiveHashOnlyHolds'))==(HEAD,TREE,WINDOW,240,192,48,1012,1060),'summary pin/counts')
    need(summary.get('decisions',{}).get('accept-current')==dec['accept-current'] and summary.get('decisions',{}).get('revise')==dec['revise'] and summary.get('decisions',{}).get('hold')==48,'summary decision counts')
    need(not any(token_mismatch.values()),'selected target token mismatch')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':WINDOW,'cells':240,'callerBackedCells':192,'acceptCurrent':dec['accept-current'],'revised':dec['revise'],'currentHashOnlyHolds':len(holds),'priorHashOnlyHolds':len(prior),'resultingActiveHolds':len(prior)+len(holds),'exactTargetHashes':len(hashes),'tokenMismatches':dict(token_mismatch),'candidateFreeOuterAndInputChecksums':'PASS','blindOutputChecksums':'PASS','packetOnlyVerification':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
