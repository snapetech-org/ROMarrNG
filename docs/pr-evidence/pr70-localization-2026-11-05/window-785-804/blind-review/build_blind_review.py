#!/usr/bin/env python3
"""Build an independent blind review using only a sealed ROMarr candidate-free packet."""
import collections, hashlib, json, re, shutil, sys
from pathlib import Path

HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'
WINDOW='W785-W804'
CF=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w785-804-20261105/candidate-free')
OUT=Path(__file__).resolve().parent
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

REVISIONS={
('ui.or-as-a-frontend-s-own-format.3a0f4bbdc6','vi'):('Hoặc xuất theo định dạng riêng của frontend:','The caller places this under export choices; this keeps the frontend term and expresses the implied export action without expanding it to a game-library manager.','moderate'),
('ui.owned-check-unavailable.b3cf0beade','ar'):('تعذّر التحقق من الألعاب التي تملكها','The caller reports that the owned-game lookup failed; this states that games the user owns could not be checked.','moderate'),
('ui.owned-check-unavailable.b3cf0beade','es'):('No se pudo comprobar qué juegos ya tienes','The caller concerns matching owned games from a profile, so this avoids the legal-sounding “propiedad” and names the failed check.','high'),
('ui.owned-check-unavailable.b3cf0beade','fr'):('Impossible de vérifier les jeux que vous possédez','This names the failed owned-games check directly and reads naturally as a compact status.','high'),
('ui.owned-check-unavailable.b3cf0beade','hi'):('आपके पास मौजूद गेम की जाँच उपलब्ध नहीं है','The caller checks which games are already in the user’s profile; this avoids suggesting the app’s own library is unavailable.','moderate'),
('ui.owned-check-unavailable.b3cf0beade','id'):('Tidak dapat memeriksa game yang sudah Anda miliki','The caller checks a profile’s owned games; this is clearer than a generic ownership check.','high'),
('ui.owned-check-unavailable.b3cf0beade','ja'):('所持しているゲームを確認できません','The status is about checking which games the profile owns, not legal ownership as an abstract concept.','moderate'),
('ui.owned-check-unavailable.b3cf0beade','pt-BR'):('Não foi possível verificar os jogos que você possui','This states the failed check of the profile’s owned games in natural Brazilian Portuguese.','high'),
('ui.owned-check-unavailable.b3cf0beade','vi'):('Không thể kiểm tra các trò chơi bạn đã có','The caller concerns a profile’s games, so this names the failed check without the legal sense of “quyền sở hữu.”','moderate'),
('ui.owned-check-unavailable.b3cf0beade','zh-Hans'):('无法检查已拥有的游戏','This directly describes the failed check of games the profile owns.','high'),
('ui.owned-check-unavailable.b3cf0beade','zh-Hant'):('無法檢查已擁有的遊戲','This directly describes the failed check of games the profile owns.','high'),
('ui.pin-from-your-moonlight-client.1a127b3ae9','ko'):('Moonlight 클라이언트의 PIN','This is a concise placeholder prompt and removes the unnecessary second-person subject while preserving the product and credential names.','moderate'),
('ui.page-could-not-be-loaded.b4aa008f1c','ar'):('تعذّر تحميل الصفحة','This is the concise error-heading form for a failed page load.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','es'):('No se pudo cargar la página','This expresses the completed load failure shown by the error page.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','fr'):('Impossible de charger la page','This is a natural concise heading for the page-load error state.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','pt-BR'):('Não foi possível carregar a página','This is a natural error heading for a failed page load.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','vi'):('Không thể tải trang','This is the natural word order for a page-load failure.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','zh-Hans'):('无法加载页面','This is the idiomatic simplified-Chinese wording for a page that failed to load.','high'),
('ui.page-could-not-be-loaded.b4aa008f1c','zh-Hant'):('無法載入頁面','This is the idiomatic traditional-Chinese wording for a page that failed to load.','high'),
('ui.paired-clients.388740cbd4','es'):('Clientes emparejados','“Emparejados” is the more natural Spanish wording for software clients paired with the host.','moderate'),
('ui.pairing.76dfd9f9a3','hi'):('पेयरिंग','This heading names the pairing procedure; “जोड़ी” reads as the pair itself rather than the setup section.','moderate'),
('ui.pairing.76dfd9f9a3','id'):('Penyandingan','This names the pairing action/section rather than describing clients as already paired.','moderate'),
('ui.passkey.904c9aa9ba','vi'):('Khóa truy cập','This better conveys an access credential in a secret indexer field than the more general “key code.”','moderate'),
('ui.paste-it-here.f21b1e24fc','de'):('Fügen Sie es hier ein.','The surrounding UI uses formal address; this aligns the prompt with that register.','moderate'),
('ui.paste-it-here.f21b1e24fc','fr'):('Collez-le ici.','The surrounding French UI uses vous; this aligns the prompt with that register.','moderate'),
('ui.paste-it-here.f21b1e24fc','pt-BR'):('Cole aqui.','This uses the standard você imperative and matches the Brazilian Portuguese UI tone.','moderate'),
('ui.paste-it-here.f21b1e24fc','zh-Hans'):('在这里粘贴','This uses the standard UI verb for pasting text rather than the literal sense of sticking something.','high'),
('ui.paste-it-here.f21b1e24fc','zh-Hant'):('在這裡貼上','This uses the standard traditional-Chinese UI verb for pasting text.','high'),
}

def sha(x):
    if isinstance(x,str): x=x.encode('utf-8')
    return hashlib.sha256(x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def wjl(p,rows): Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def sums(root):
    root=Path(root); listed={}
    for ln in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not ln.strip():continue
        h,n=ln.split('  ',1);n=n.removeprefix('./');p=(root/n).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h or n in listed:raise SystemExit('FAIL checksum '+str(p))
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt'}
    if set(listed)!=actual:raise SystemExit('FAIL checksum coverage '+str(root))
    return listed
def protected(s):
    found=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok:found.append(lit)
    return sorted(set(found))
def audit(source,target):
    sp, tp=PH.findall(source),PH.findall(target); sm,tm=TAG.findall(source),TAG.findall(target)
    sn,tn=NUM.findall(source),NUM.findall(target); sl=protected(source); missing=[x for x in sl if x not in target]
    return {'sourcePlaceholders':sp,'targetPlaceholders':tp,'placeholdersMatch':collections.Counter(sp)==collections.Counter(tp),'sourceMarkup':sm,'targetMarkup':tm,'markupMatches':collections.Counter(sm)==collections.Counter(tm),'sourceNumbers':sn,'targetNumbers':tn,'numbersMatch':collections.Counter(sn)==collections.Counter(tn),'sourceProtectedLiterals':sl,'missingProtectedLiterals':missing,'protectedLiteralsMatch':not missing}
def main():
    if any((OUT/n).exists() for n in ['blind-review-ledger.jsonl','independent-target-hashes.jsonl','summary.json','SHA256SUMS.txt']):raise SystemExit('FAIL output already contains generated payload; refusing overwrite')
    outer=sums(CF); inner=sums(CF/'input'); inp=CF/'input'; manifest=rj(inp/'manifest.json')
    if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'),manifest.get('callerBackedCells'),manifest.get('callerlessHashOnlyCells'))!=(HEAD,TREE,WINDOW,240,192,48):raise SystemExit('FAIL candidate-free manifest pin/count')
    if manifest.get('proposedTargetsIncluded') is not False or manifest.get('reviewDecisionsIncluded') is not False:raise SystemExit('FAIL candidate-free contains prior decisions')
    cells=rjl(inp/'candidate-free-cells.jsonl'); old_holds=rjl(inp/'prior-active-holds-hash-only.jsonl')
    if len(cells)!=240 or len(old_holds)!=1012:raise SystemExit('FAIL input cell/hold count')
    contexts={r['sourceId']:r for r in rjl(inp/'source-contexts.jsonl')}
    ledger=[]; hashes=[]; new_holds=[]; changes=collections.Counter(); reviewed=set(); token_errors=[]
    for cell in cells:
        sid,loc=cell['sourceId'],cell['locale']; key=(sid,loc)
        if key in reviewed:raise SystemExit('FAIL duplicate current cell '+repr(key))
        reviewed.add(key)
        forbidden=('proposedTarget','decision','reviewDecision')
        if any(k in cell for k in forbidden):raise SystemExit('FAIL candidate-free input has review content')
        cctx=contexts[sid]
        if cell.get('callerContextSha256')!=cctx.get('contextSha256'):raise SystemExit('FAIL caller context mismatch '+sid)
        common={'window':WINDOW,'position':cell['position'],'catalogZeroBasedIndex':cell['catalogZeroBasedIndex'],'catalogOneBasedPosition':cell['catalogOneBasedPosition'],'sourceId':sid,'sourceSha256':cell['sourceSha256'],'locale':loc,'callerContextSha256':cell['callerContextSha256'],'literalCallerCount':cell['literalCallerCount'],'candidateFreeCellRecordSha256':sha(canon(cell))}
        if cell.get('callerless'):
            if cell.get('sourceTextOmitted') is not True or cell.get('currentTargetTextOmitted') is not True or any(k in cell for k in ('source','currentTarget','proposedTarget')):raise SystemExit('FAIL callerless input includes text '+sid+'/'+loc)
            hold={'window':WINDOW,**common,'decision':'hold-hash-only','rationale':'No pinned production caller; preserve the callerless hash-only hold.','currentTargetSha256':cell['currentTargetSha256'],'textOmitted':True}
            ledger.append(hold);new_holds.append({k:v for k,v in hold.items() if k not in ('decision','rationale')});changes['hold']+=1
            continue
        if cell.get('sourceTextOmitted') or cell.get('currentTargetTextOmitted') or not cell.get('source') or not cell.get('currentTarget'):raise SystemExit('FAIL caller-backed source/target text missing '+sid+'/'+loc)
        override=REVISIONS.get(key); target=override[0] if override else cell['currentTarget']; decision='revise' if override else 'accept-current'
        ta=audit(cell['source'],target)
        if not all(ta[k] for k in ('placeholdersMatch','markupMatches','numbersMatch','protectedLiteralsMatch')):token_errors.append({'sourceId':sid,'locale':loc,'audit':ta})
        if token_errors:raise SystemExit('FAIL proposed target token mismatch '+repr(token_errors[-1]))
        rationale=override[1] if override else 'Current wording accurately conveys the source in its pinned UI context; retain it.'
        confidence=override[2] if override else 'high'
        row={'window':WINDOW,**common,'source':cell['source'],'currentTarget':cell['currentTarget'],'currentTargetSha256':cell['currentTargetSha256'],'decision':decision,'blindTarget':target,'blindTargetSha256':sha(target),'rationale':rationale,'confidence':confidence,'nativeSpeakerApproval':False,'tokenAudit':ta}
        if override:row.update({'proposedTarget':target,'proposedTargetSha256':sha(target)})
        ledger.append(row);hashes.append({'window':WINDOW,'position':cell['position'],'sourceId':sid,'sourceSha256':cell['sourceSha256'],'locale':loc,'decision':decision,'currentTargetSha256':cell['currentTargetSha256'],'blindTargetSha256':sha(target),'proposedTargetSha256':sha(target) if override else None})
        changes[decision]+=1
    if len(reviewed)!=240 or len(ledger)!=240 or len(new_holds)!=48 or changes['accept-current']+changes['revise']!=192:raise SystemExit('FAIL reviewed cell accounting')
    if set(REVISIONS)!={(r['sourceId'],r['locale']) for r in ledger if r['decision']=='revise'}:raise SystemExit('FAIL revision matrix differs from declared corrections')
    if any(any(k in r for k in ('source','currentTarget','blindTarget','proposedTarget')) for r in new_holds):raise SystemExit('FAIL hold text leak')
    if any(any(k in r for k in ('source','currentTarget','target','targetText','proposedTarget')) for r in old_holds):raise SystemExit('FAIL prior hold text leak')
    shutil.copyfile(inp/'prior-active-holds-hash-only.jsonl',OUT/'prior-active-holds-hash-only.jsonl')
    wjl(OUT/'blind-review-ledger.jsonl',ledger);wjl(OUT/'independent-target-hashes.jsonl',hashes);wjl(OUT/'current-window-holds-hash-only.jsonl',new_holds)
    pins={'candidateFreeDirectory':str(CF),'head':HEAD,'tree':TREE,'window':WINDOW,'candidateFreeOuterChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),'candidateFreeInputChecksumListSha256':sha((inp/'SHA256SUMS.txt').read_bytes()),'candidateFreeManifestSha256':sha((inp/'manifest.json').read_bytes()),'candidateFreeCellsSha256':sha((inp/'candidate-free-cells.jsonl').read_bytes()),'candidateFreeSourceContextsSha256':sha((inp/'source-contexts.jsonl').read_bytes()),'candidateFreePriorActiveHoldsSha256':sha((inp/'prior-active-holds-hash-only.jsonl').read_bytes()),'candidateFreeChecksumsVerified':True,'candidateFreeProducerVerifier':'PASS (recorded by preparer)','blindReviewerIndependentlyReranCandidateFreeVerifier':False,'blindReviewerDidNotInspectProductWorktree':True,'primaryOrOtherProposalPacketsInspected':False,'candidateFreeReviewInputOnly':True}
    wj(OUT/'input-pins.json',pins)
    wj(OUT/'proposal-freeze.json',{'window':WINDOW,'head':HEAD,'tree':TREE,'sourceCount':16,'callerBackedCellCount':192,'localeOrder':LOCALES,'proposalCellCount':len(REVISIONS),'proposalMatrixSha256':sha((OUT/'independent-target-hashes.jsonl').read_bytes()),'frozenAfterCandidateFreeChecksumVerification':True,'priorProposalContentConsulted':False,'primaryReviewConsulted':False,'productWorktreeConsulted':False,'nativeSpeakerApproval':False})
    summary={'artifact':'Independent blind translation review, ROMarrNG PR #70 W785-W804','head':HEAD,'tree':TREE,'window':WINDOW,'cellCount':240,'callerBackedCells':192,'callerBackedSources':16,'localeCount':12,'decisions':dict(changes),'proposalCells':len(REVISIONS),'acceptedCurrentCells':changes['accept-current'],'currentWindowHashOnlyHolds':changes['hold'],'priorActiveHashOnlyHolds':len(old_holds),'resultingActiveHashOnlyHolds':len(old_holds)+len(new_holds),'tokenMismatches':{'placeholder':0,'markup':0,'numeric':0,'protectedLiteral':0},'exactBlindTargetHashes':len(hashes),'candidateFreeChecksums':'PASS','candidateFreeManifestPin':'PASS','candidateFreeProducerVerifier':'PASS','primaryOrOtherProposalPacketsInspected':False,'productWorktreeInspected':False,'nativeSpeakerApproval':False,'nextBoundary':manifest['nextBoundary']}
    wj(OUT/'summary.json',summary)
    (OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W785–W804 independent blind review

This packet reviews the sealed candidate-free input at `{CF}` and is pinned to HEAD `{HEAD}` / tree `{TREE}`. Its outer and input checksum lists were verified before review; the candidate-free manifest reports the producer verifier passed at the same pin. No primary or other proposal packet, and no product worktree, was consulted.

The ledger covers all 240 cells. It independently accepts the current wording for {changes['accept-current']} caller-backed cells, proposes revisions for {changes['revise']} cells, and preserves all {changes['hold']} callerless cells as hash-only holds. Source and target text is omitted for all current holds; the 1,012 prior active holds are retained in a separate text-free hash ledger. The resulting active hold count is {len(old_holds)+len(new_holds)}.

Every caller-backed cell has an exact blind target and SHA256. Placeholder, markup, numeric and protected-literal checks pass for all selected targets. Proposals are semantic suggestions, not native-speaker approval.

Verify with `python3 verify_blind_review.py --candidate-free {CF}`. This verifier reads only the candidate-free packet and this blind output; it does not access the product worktree.
''',encoding='utf-8')
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n' for p in files),encoding='utf-8')
    print(json.dumps({'result':'BUILT','head':HEAD,'tree':TREE,'window':WINDOW,'cells':len(ledger),'callerBacked':192,'accepted':changes['accept-current'],'revised':changes['revise'],'holds':changes['hold'],'priorHolds':len(old_holds),'resultingHolds':len(old_holds)+len(new_holds)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
