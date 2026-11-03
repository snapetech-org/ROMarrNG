#!/usr/bin/env python3
"""Independent blind semantic review of ROMarrNG PR #70 W206-W225."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,pathlib,re,subprocess

BASE=pathlib.Path('/mnt/disks/scratch/task-scratch')
INPUT=BASE/'romarrng-pr70-w206-225-primary-20261103/clean-input'
OUT=BASE/'romarrng-pr70-w206-225-independent-blind-20261103'
EXPECTED_HEAD='bef31ca8a94f21273b11303524d79bd9c5344305'
EXPECTED_TREE='7616d96ddd3a1bfe8078d43492eb5bea7213f080'
EXPECTED_BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Protected literals apparent in the pinned English messages.
PROTECTED={
 210:['DAT','ROMarrNG'],
 211:['DAT','DAT_PATH','No-Intro','Redump'],
 212:['DAT'],
 214:['ROM'],
 219:['JSON','patch-catalog.d'],
 220:['PIN'],
}

# Independent per-cell decisions: (disposition, target, confidence, rationale).
PROPOSALS={
 (206,'ar'):('correction','أحدث من أحدث إصدار مدرج','moderate','The target repeats “latest” with awkward noun agreement. “أحدث إصدار” is the natural Arabic rendering of the latest release/version listed.'),
 (206,'de'):('correction','Neuer als die neueste aufgeführte Version','high','The current comparison omits the definite article before “neueste aufgeführte Version.” Adding “die” gives the required German comparison.'),
 (206,'fr'):('refinement','Plus récent que la dernière version répertoriée','moderate','“Répertoriée” more directly expresses a version listed in a catalog than “enregistrée” (recorded). The masculine comparison remains consistent with the implicit release being compared.'),
 (206,'pt-BR'):('correction','Mais recente do que a versão mais recente listada','moderate','The current target omits “latest” and says only “the listed version.” The proposal restores the comparison with the most recent listed version.'),
 (206,'vi'):('refinement','Mới hơn phiên bản mới nhất được liệt kê','moderate','The current target omits the “listed” qualifier. Adding “được liệt kê” preserves that distinction.'),
 (207,'ar'):('correction','أحدث إصدار','moderate','For a software/game release, “إصدار” means release/version; “إطلاق” more often means a launch event.'),
 (207,'de'):('refinement','Neueste Version','moderate','“Neueste Release” is understandable software jargon but mixes German with an English noun. “Neueste Version” is the natural German UI label for a software release.'),
 (207,'vi'):('refinement','Bản phát hành mới nhất','moderate','Adding “Bản” supplies the noun for “release”; the current phrase “phát hành mới nhất” is less complete as a standalone label.'),
 (208,'ar'):('refinement','الأحدث','moderate','The definite form reads naturally as a standalone “Newest” library-tab label; the current bare adjective is less complete.'),
 (208,'es'):('refinement','Más recientes','moderate','“Más recientes” is a natural standalone plural sort/tab label for the newest library items; “Últimas” is less specific here.'),
 (208,'pt-BR'):('refinement','Mais recentes','moderate','“Mais recentes” is a natural standalone sort/tab label for the newest library items; the current “Últimas” is less specific.'),
 (210,'de'):('correction','In ROMarrNG ist kein DAT-Katalog geladen.','high','The current “wird ... geladen” describes an ongoing loading action rather than the absent loaded state. The proposal states that no DAT catalog is loaded and preserves both protected literals.'),
 (210,'fr'):('correction','Aucun catalogue DAT n’est chargé dans ROMarrNG.','high','French negative syntax requires “ne” with “aucun”; the current target omits it. The proposal preserves DAT and ROMarrNG.'),
 (210,'pt-BR'):('correction','Nenhum catálogo DAT está carregado no ROMarrNG.','moderate','“É carregado” reads as a general passive process. “Está carregado” expresses the current state that no catalog is loaded.'),
 (215,'fr'):('refinement','Aucune bibliothèque de jeux gérée par un lanceur n’a été trouvée sur cette machine.','moderate','“Bibliothèque de lanceur” is an awkward literal compound. The proposed wording makes clear that these are game libraries managed by a launcher.'),
 (215,'vi'):('correction','Không tìm thấy thư viện trò chơi nào của trình khởi chạy trên máy này.','moderate','“Thư viện khởi động” means a startup library. The source means a game library belonging to/managed by a launcher.'),
 (217,'ja'):('correction','リストが設定されていません。','moderate','“設定リストなし” can read as “no settings list.” The proposal clearly says that no lists are configured.'),
 (217,'vi'):('refinement','Chưa có danh sách nào được cấu hình.','moderate','The current passive phrase is awkward. This is a more natural way to say that no lists have been configured yet.'),
 (217,'id'):('refinement','Belum ada daftar yang dikonfigurasi.','moderate','“Belum ada” is a more natural status phrasing for “no lists configured” than “Tidak ada ... terkonfigurasi.”'),
 (220,'de'):('correction','Keine PIN angegeben.','high','“Keine PIN gegeben” is unidiomatic German for a PIN form error. “Keine PIN angegeben” is the standard wording.'),
 (220,'id'):('correction','Tidak ada PIN yang diberikan.','moderate','The current Indonesian omits the relative marker “yang.” The proposal is grammatical and preserves the exact PIN token.'),
 (220,'ko'):('correction','PIN이 제공되지 않았습니다.','moderate','The current fragment omits the subject particle and sounds like a clipped note. The proposal is a natural user-facing error message.'),
 (220,'vi'):('correction','Không có PIN nào được cung cấp.','moderate','The current word order “không PIN được cung cấp” is ungrammatical. The proposal expresses that no PIN was provided.'),
 (222,'ja'):('correction','安全な正規タイトルはありません。','moderate','“カノニック” is an obscure transliteration in this UI phrase. “正規タイトル” clearly conveys a canonical/standardized title.'),
 (222,'vi'):('correction','Không có tiêu đề chuẩn nào an toàn.','moderate','“Canonic” is an unnatural English calque. “Tiêu đề chuẩn” is the clear Vietnamese rendering of a canonical title.'),
 (223,'de'):('correction','In diesem Stapel sind keine sicheren Umbenennungen verfügbar.','high','The current leaves “Renames” in English and uses “Paket” for a batch. The proposal uses standard German terms for safe renames in this batch.'),
 (223,'es'):('refinement','No hay cambios de nombre seguros listos en este lote.','moderate','“Renombrados” is awkward as a noun here. “Cambios de nombre” is clearer for filesystem rename actions.'),
 (223,'zh-Hans'):('correction','此批次没有可安全执行的重命名。','moderate','The current “包装” means packaging/package, not a review batch, and its word order is unnatural. The proposal uses 批次 and a natural safe-to-execute construction.'),
 (223,'zh-Hant'):('correction','此批次沒有可安全執行的重新命名。','moderate','The current “包裝” means packaging/package, not a review batch, and its word order is unnatural. The proposal uses 批次 and a natural safe-to-execute construction.'),
 (224,'ko'):('correction','해당 친구를 찾을 수 없습니다.','moderate','The current “없어” is informal banmal. The proposal is a polite, user-facing equivalent of “no such friend.”'),
}

HOLD_RATIONALE=('Hold all locales for this source. The pinned exact-head caller shows {what} is interpolated from caller arguments “browse” and “answer for a date range,” but does not show that either value is localized before interpolation or that the UI receives a localized template/value descriptor. The current translated sentence cannot be judged as a complete localized message while this boundary is unresolved; preserve the current target pending evidence or localization of the argument.')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def str_sha(s):return sha(s.encode('utf-8'))
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def read_jsonl(path):
    raw=path.read_bytes(); lines=[x for x in raw.splitlines() if x.strip()]
    return raw,[json.loads(x) for x in lines],lines
def placeholders(s):return sorted(set(re.findall(r'\{([^{}]+)\}',s)))
def tags(s):return sorted(re.findall(r'</?[^>]+>',s))
def main():
    output_names=('blind-ledger.jsonl','summary.json','input-attestation.json','README.md','manifest.json','SHA256SUMS.txt')
    assert not any((OUT/name).exists() for name in output_names),'blind output artifacts already exist'
    # Verify the supplied candidate-free packet and exact live PR pins only.
    checks={}
    for line in (INPUT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected,name=line.split(None,1);name=name.strip();actual=sha((INPUT/name).read_bytes())
        assert actual==expected,(name,expected,actual);checks[name]=actual
    att=read_json(INPUT/'PR-attestation.json');manifest=read_json(INPUT/'manifest.json');pins=read_json(INPUT/'catalog-file-pins.json')
    assert att['repository']=='snapetech-org/ROMarrNG' and att['pullRequest']==70
    assert att['headRefOid']==EXPECTED_HEAD and att['headRefName']==EXPECTED_BRANCH and att['tree']==EXPECTED_TREE
    assert att['state']=='OPEN' and att['draft'] is True
    assert manifest['head']==EXPECTED_HEAD and manifest['tree']==EXPECTED_TREE and manifest['window']=='W206-W225'
    assert manifest['cellCount']==240 and manifest['sourceContextRows']==20 and manifest['proposedTranslationsIncluded'] is False
    assert manifest['reviewDecisionsIncluded'] is False and manifest['candidateFreeInputOnly'] is True
    assert pins['head']==EXPECTED_HEAD and pins['tree']==EXPECTED_TREE
    assert pins['clientCatalog']['sha256']=='15a3893bc95cfd35a61a44fe881b2f793bda26dc32eaba277c4186d69acb536b'
    live=json.loads(subprocess.check_output(['gh','pr','view','70','-R','snapetech-org/ROMarrNG','--json','number,state,isDraft,headRefName,headRefOid,baseRefName'],text=True))
    assert live=={'number':70,'state':'OPEN','isDraft':True,'headRefName':EXPECTED_BRANCH,'headRefOid':EXPECTED_HEAD,'baseRefName':'main'},live
    remote=subprocess.check_output(['git','ls-remote','https://github.com/snapetech-org/ROMarrNG.git',f'refs/heads/{EXPECTED_BRANCH}'],text=True).split()
    assert remote and remote[0]==EXPECTED_HEAD

    cells_raw,cells,cell_lines=read_jsonl(INPUT/'current-target-cells.jsonl')
    contexts_raw,contexts,context_lines=read_jsonl(INPUT/'source-contexts.jsonl')
    assert len(cells)==240 and len(contexts)==20
    assert [r['locale'] for r in cells[:12]]==LOCALES
    assert set(r['position'] for r in cells)==set(range(206,226))
    assert set(r['position'] for r in contexts)==set(range(206,226))
    key=lambda r:(r['position'],r['locale'])
    cm={key(r):r for r in cells}; assert len(cm)==240
    ctxmap={r['position']:(r,sha(raw)) for r,raw in zip(contexts,context_lines)}
    source_info={x['position']:x for x in manifest['sourceIds']}
    assert len(source_info)==20
    protected_failures=[]; placeholder_failures=[]; ledger=[];counts=Counter();by_locale=Counter()
    for row in cells:
        pos,locale=row['position'],row['locale'];k=(pos,locale)
        assert row['head']==EXPECTED_HEAD and row['tree']==EXPECTED_TREE and row['window']=='W206-W225'
        assert row['pullRequest']==70 and row['repository']=='snapetech-org/ROMarrNG'
        assert row['catalogPath']=='romarr/ui-labels.json' and row['catalogSha256']==pins['clientCatalog']['sha256'] and row['catalogGitBlob']==pins['clientCatalog']['gitBlob']
        assert str_sha(row['source'])==row['sourceSha256'] and str_sha(row['currentTarget'])==row['currentTargetSha256']
        meta=source_info[pos]
        assert (meta['sourceId'],meta['source'],meta['sourceSha256'])==(row['sourceId'],row['source'],row['sourceSha256'])
        ctx,ctxhash=ctxmap[pos]
        assert ctx['sourceId']==row['sourceId'] and ctx['source']==row['source'] and ctx['sourceSha256']==row['sourceSha256']
        source_ph=placeholders(row['source']);current_ph=placeholders(row['currentTarget'])
        required=PROTECTED.get(pos,[])
        assert all(lit in row['source'] for lit in required),(pos,required,row['source'])
        current_integrity={'sourcePlaceholders':source_ph,'currentPlaceholders':current_ph,'placeholderParity':source_ph==current_ph,'protectedLiteralsRequired':required,'currentProtectedLiteralsPreserved':all(lit in row['currentTarget'] for lit in required),'sourceMarkupTags':tags(row['source']),'currentMarkupTags':tags(row['currentTarget']),'markupParity':tags(row['source'])==tags(row['currentTarget'])}
        if not current_integrity['placeholderParity']:placeholder_failures.append((k,current_integrity))
        if not current_integrity['currentProtectedLiteralsPreserved']:protected_failures.append((k,current_integrity))
        assert current_integrity['placeholderParity'] and current_integrity['markupParity']
        ruling=PROPOSALS.get(k)
        if pos==218:
            disposition='hold';target=row['currentTarget'];confidence='unknown';rationale=HOLD_RATIONALE;proposed=None
        elif ruling:
            disposition,target,confidence,rationale=ruling;proposed=target
        else:
            disposition='accept-current';target=row['currentTarget'];proposed=None;confidence='moderate'
            reasons={
              206:'This locale expresses the newer-versus-listed-version relation without a material meaning shift.',
              207:'This locale clearly labels the newest release.',
              208:'This locale functions as a concise newest-item sort/tab label.',
              209:'This locale clearly indicates that no cover is present.',
              210:'This locale states that no DAT catalog is loaded in ROMarrNG.',
              211:'This locale preserves the no-DAT state and the DAT_PATH/No-Intro/Redump setup instruction.',
              212:'This locale preserves the instruction to configure the DAT directory under Settings → Media Management first.',
              213:'This locale conveys that no indexer could be read in the error context.',
              214:'This locale conveys the empty inventory state and the scan-to-begin instruction.',
              215:'This locale conveys that no launcher libraries were found on the machine.',
              216:'This locale clearly states that no game library is configured.',
              217:'This locale clearly states that no lists are configured.',
              219:'This locale explains that no patch projects match and preserves the catalog/JSON patch-catalog.d instructions.',
              220:'This locale clearly reports that no PIN was provided.',
              221:'This locale clearly states that no platforms match the filter.',
              222:'This locale conveys that no safe canonical title exists.',
              223:'This locale conveys that no safe renames are ready in this batch.',
              224:'This locale conveys that the requested friend does not exist.',
              225:'This locale conveys that the requested peer does not exist.'
            }
            rationale=reasons[pos]
        chosen_ph=placeholders(target);chosen_tags=tags(target)
        protected_ok=all(lit in target for lit in required)
        placeholder_ok=chosen_ph==source_ph
        markup_ok=chosen_tags==tags(row['source'])
        if not protected_ok:protected_failures.append((k,target,required))
        if not placeholder_ok:placeholder_failures.append((k,target,source_ph,chosen_ph))
        assert protected_ok and placeholder_ok and markup_ok,(k,required,source_ph,chosen_ph)
        if proposed is not None:assert target!=row['currentTarget'] and str_sha(target)
        else:assert target==row['currentTarget']
        calls=[]
        for ref in ctx['references']:
            calls.append({'path':ref['path'],'startLine':ref['startLine'],'endLine':ref['endLine'],'matchBasis':ref['matchBasis'],'contextSha256':ref['contextSha256'],'localizedCallsiteMetadata':ref.get('localizedCallsiteMetadata'),'contextLines':ref['contextLines']})
        ledger.append({
          'schemaVersion':1,'window':'W206-W225','position':pos,'sourceId':row['sourceId'],'locale':locale,'localeInfo':row['localeInfo'],
          'catalogPath':row['catalogPath'],'source':row['source'],'sourceSha256':row['sourceSha256'],
          'currentTarget':row['currentTarget'],'currentTargetSha256':row['currentTargetSha256'],
          'decision':disposition,'candidateTarget':proposed,'candidateTargetSha256':str_sha(proposed) if proposed is not None else None,
          'selectedTarget':target,'selectedTargetSha256':str_sha(target),'rationale':rationale,'confidence':confidence,
          'callerContext':{'category':ctx['category'],'callerReferenceCount':ctx['callerReferenceCount'],'contextRowSha256':ctxhash,'references':calls},
          'integrityChecks':{'sourceHashVerified':True,'currentTargetHashVerified':True,'sourcePlaceholders':source_ph,'selectedPlaceholders':chosen_ph,'placeholderParity':placeholder_ok,'sourceMarkupTags':tags(row['source']),'selectedMarkupTags':chosen_tags,'markupParity':markup_ok,'protectedLiteralsRequired':required,'currentProtectedLiteralsPreserved':current_integrity['currentProtectedLiteralsPreserved'],'selectedProtectedLiteralsPreserved':protected_ok},
          'nativeSpeakerApproved':False
        })
        counts[disposition]+=1;by_locale[(locale,disposition)]+=1
    assert not protected_failures,protected_failures
    assert not placeholder_failures,placeholder_failures
    assert counts=={'accept-current':198,'correction':19,'refinement':11,'hold':12},counts
    assert all(x['decision']=='hold' for x in ledger if x['position']==218)
    assert all(x['selectedTarget']==x['currentTarget'] for x in ledger if x['position']==218)

    OUT.mkdir(parents=True,exist_ok=True)
    ledger_path=OUT/'blind-ledger.jsonl'
    ledger_path.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in ledger),encoding='utf-8')
    summary={
      'artifact':'ROMarrNG PR #70 independent blind localization review W206-W225',
      'repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':EXPECTED_BRANCH,
      'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'window':[206,225],
      'reviewedCells':240,'sourceIds':20,'locales':12,
      'decisionCounts':dict(counts),'proposalCounts':{'correction':counts['correction'],'refinement':counts['refinement']},
      'contextHolds':{'cells':12,'positions':[218]},
      'rank218':{'decision':'hold-all-locales','sourceId':source_info[218]['sourceId'],'reason':'The supplied exact-head caller fragments show English what arguments (browse; answer for a date range) passed into _gap but do not establish that they are localized before interpolation or supplied through a localized template/value boundary.'},
      'inputChecksumFilesVerified':len(checks),'placeholderMarkupProtectedFailures':0,
      'nativeSpeakerApproval':False,'primaryReviewInspected':False,'repositoryOrPREdited':False,
      'testsBuildsScansCIOrBrowserWork':False,
      'confidenceLimit':'Machine semantic review; language fluency for all 12 locales remains unverified by native speakers.'
    }
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    input_attestation={
      'inputPath':'/mnt/disks/scratch/task-scratch/romarrng-pr70-w206-225-primary-20261103/clean-input/',
      'inputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'verifiedInputFiles':checks,
      'livePR':live,'remoteBranchHead':remote[0],'pinnedHead':EXPECTED_HEAD,'pinnedTree':EXPECTED_TREE,
      'reviewInputSha256':sha(cells_raw),'sourceContextsSha256':sha(contexts_raw),
      'cellCounts':{'input':len(cells),'ledger':len(ledger),'unique':len(cm)},
      'callerPins':{'count':len(pins['callerFiles']),'files':pins['callerFiles']},
      'catalogPin':pins['clientCatalog'],
      'reviewBoundary':'Only clean-input files, GitHub PR metadata, and the remote branch ref were read. No primary review or repository contents were inspected.'
    }
    (OUT/'input-attestation.json').write_text(json.dumps(input_attestation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    readme='''# ROMarrNG PR #70 blind review — W206–W225\n\nThis independent review covers 240 translation cells across 20 source IDs and 12 locales, pinned to open/draft PR head `bef31ca8a94f21273b11303524d79bd9c5344305` and tree `7616d96ddd3a1bfe8078d43492eb5bea7213f080`. The candidate-free packet checksums and remote branch head were verified. The primary review was not opened or used.\n\nThe ledger records 198 accept-current values, 19 corrections, 11 refinements, and 12 holds. All 12 cells for position 218 are held. The pinned snippets show `{what}` interpolated from the English values “browse” and “answer for a date range,” but do not show localization at that boundary or a localized template descriptor; the existing translations cannot be assessed as complete messages without that evidence.\n\nSource/current hashes, placeholders, markup, and selected protected literals were checked. The ledger retains caller spans and exact line hashes. This is machine review, not native-speaker approval. No repository/PR changes, tests, builds, scans, CI, browser work, workflow edits, merge, release, or tag were made.\n'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt'))
    manifest_out={'artifact':'ROMarrNG PR #70 W206-W225 independent blind review','sealed':True,'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'rowCount':240,'decisionCounts':dict(counts),'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files]}
    (OUT/'manifest.json').write_text(json.dumps(manifest_out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt'))
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
