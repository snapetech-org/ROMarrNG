#!/usr/bin/env python3
"""Verify the sealed W305-W324 application evidence against its pinned base."""
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

EVIDENCE=Path(__file__).resolve().parent
REPO=EVIDENCE.parents[3]
BASE='9ecde2b300fea97e52846f274fbcae19cff1fcc5'
REL='romarr/ui-labels.json'
PROTECTED=['ROMarr','SeerrNG','Prowlarr','No-Intro','Redump','IGDB','HTTP','HTTPS','JSON','1G1R']

def fail(message): raise RuntimeError(message)
def require(condition,message):
    if not condition: fail(message)
def sha(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(path.read_text(encoding='utf-8'))
def git_show(path): return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=REPO)
def tokens(text,pattern): return re.findall(pattern,text)
def structure(c):
    return (list(c),list(c['messages']),
            {sid:list(msg) for sid,msg in c['messages'].items()},
            {sid:list(msg['translations']) for sid,msg in c['messages'].items()})

try:
    auth_bytes=(EVIDENCE/'root-application-authorization.json').read_bytes()
    selected_bytes=(EVIDENCE/'selected-changes.jsonl').read_bytes()
    auth=json.loads(auth_bytes)
    rows=[json.loads(line) for line in selected_bytes.decode('utf-8').splitlines() if line.strip()]
    require(auth['applicationApproved'] is True and auth['releaseApproved'] is False,'authorization flags mismatch')
    require(auth['head']==BASE and auth['tree']=='df77009a42ee07366803f7553f6dcab25b62c638','authorization base pin mismatch')
    require(auth['selectedChangeCount']==105 and auth['holds']==0 and len(rows)==105,'authorization count/hold mismatch')
    require(sha(selected_bytes)==auth['selectedChangesSha256'],'selected file checksum differs from authorization')
    current_bytes=(REPO/REL).read_bytes()
    base_bytes=git_show(REL)
    base=json.loads(base_bytes); current=json.loads(current_bytes)
    summary=read_json(EVIDENCE/'application-summary.json')
    require(summary['catalogBeforeSha256']==sha(base_bytes),'base catalog checksum mismatch')
    require(summary['catalogAfterSha256']==sha(current_bytes),'applied catalog checksum mismatch')
    require(summary['cellCount']==240 and summary['selectedUpdates']==105 and summary['retainedCurrentValues']==135 and summary['holds']==0,'summary counts mismatch')
    source_rows=json.loads(git_show('romarr/ui-source-messages.json'))['messages']
    ordered=sorted(source_rows,key=lambda row:row['id'])
    window=ordered[304:324]
    require(len(window)==20,'pinned source window size mismatch')
    by_pos={p:r for p,r in zip(range(305,325),window)}
    active=summary['directLocales']
    require(len(active)==12 and len(set(active))==12,'direct locale count mismatch')
    selected={(r['sourceId'],r['locale']):r for r in rows}
    require(len(selected)==105,'selected row duplicates')
    require(set(r['locale'] for r in rows)==set(active),'selected locales mismatch')
    for row in rows:
        require(row['position'] in by_pos and by_pos[row['position']]['id']==row['sourceId'],'selected source position mismatch')
        msg=base['messages'][row['sourceId']]
        require(msg['source']==row['source'] and msg['sourceHash']==row['sourceSha256']==by_pos[row['position']]['sourceHash'],'source identity mismatch')
        previous=msg['translations'][row['locale']]
        require(previous==row['previousTarget'] and sha(previous.encode())==row['previousTargetSha256'],'previous target mismatch')
        require(sha(row['target'].encode())==row['targetSha256'],'proposed target hash mismatch')
        require(tokens(row['source'],r'\{[^{}]+\}')==tokens(row['target'],r'\{[^{}]+\}'),'placeholder mismatch')
        require(tokens(row['source'],r'</?[A-Za-z][^>]*>')==tokens(row['target'],r'</?[A-Za-z][^>]*>'),'markup mismatch')
        require(tokens(row['source'],r'\d+(?:\.\d+)?')==tokens(row['target'],r'\d+(?:\.\d+)?'),'numeric token mismatch')
        for literal in PROTECTED:
            if literal in row['source']:
                require(row['source'].count(literal)==row['target'].count(literal),f'protected literal mismatch: {literal}')
    expected=json.loads(base_bytes)
    for row in rows:
        expected['messages'][row['sourceId']]['translations'][row['locale']]=row['target']
    require(current==expected,'catalog contains missing, extra, or non-target changes')
    require(structure(base)==structure(current),'ordered catalog structures/key sets changed')
    changed=[]
    for sid,msg in base['messages'].items():
        for locale,old in msg['translations'].items():
            if current['messages'][sid]['translations'][locale]!=old: changed.append((sid,locale))
    require(set(changed)==set(selected) and len(changed)==105,'exact changed-cell set mismatch')
    readback=[json.loads(line) for line in (EVIDENCE/'application-readback.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    require(len(readback)==240,'readback row count mismatch')
    readback_by={(r['sourceId'],r['locale']):r for r in readback}
    require(len(readback_by)==240,'readback duplicate key')
    expected_pairs={(src['id'],locale) for src in window for locale in active}
    require(set(readback_by)==expected_pairs,'readback cell set mismatch')
    for pos,src in by_pos.items():
        msg=base['messages'][src['id']]
        for locale in active:
            pair=(src['id'],locale); record=readback_by[pair]
            after=current['messages'][src['id']]['translations'][locale]
            row=selected.get(pair)
            require(record['position']==pos and record['source']==src['source'] and record['sourceSha256']==src['sourceHash'],'readback source mismatch')
            require(record['previousTarget']==msg['translations'][locale] and record['previousTargetSha256']==sha(msg['translations'][locale].encode()),'readback prior value mismatch')
            require(record['target']==after and record['targetSha256']==sha(after.encode()),'readback target mismatch')
            require(record['disposition']==('update' if row else 'retain'),'readback disposition mismatch')
            require(record['rootRationale']==(row['rootRationale'] if row else None),'readback rationale mismatch')
    require(sum(r['disposition']=='update' for r in readback)==105,'readback update count mismatch')
    require(sum(r['disposition']=='retain' for r in readback)==135,'readback retain count mismatch')
    caller=read_json(EVIDENCE/'caller-context.json')
    require(caller['sourceContextCount']==20 and set(caller['sources'])=={r['id'] for r in window},'caller context source set mismatch')
    for src in window:
        entry=caller['sources'][src['id']]
        require(entry['source']==src['source'] and entry['sourceSha256']==src['sourceHash'] and entry['locations']==src['locations'],'caller context differs from pinned source metadata')
        require(len(entry['callerReferences'])==len(src['locations']),'caller reference count mismatch')
    wanted=read_json(EVIDENCE/'wanted-label-context.json')
    wanted_msg=base['messages']['ui.wanted.c296832656']
    require(wanted['position']==310 and wanted['sourceId']==by_pos[310]['id'] and wanted['source']==by_pos[310]['source'],'Wanted context identity mismatch')
    require(wanted['semantics']['confidence']=='high','Wanted semantics confidence mismatch')
    require(set(wanted['localeLabelsAndTargets'])==set(active),'Wanted locale set mismatch')
    for locale in active:
        rec=wanted['localeLabelsAndTargets'][locale]
        help_target=selected[(by_pos[310]['id'],locale)]['target']
        label=wanted_msg['translations'][locale]
        require(rec['existingWantedLabel']==label and rec['proposedHelpText']==help_target,'Wanted locale evidence mismatch')
        require(rec['containsExactExistingLabel'] is True and label in help_target,'rank-310 target lacks exact localized list label')
    for line in (EVIDENCE/'SHA256SUMS').read_text().splitlines():
        digest,rel=line.split('  ',1)
        require(sha((EVIDENCE/rel).read_bytes())==digest,f'evidence checksum mismatch: {rel}')
    expected_files={p.name for p in EVIDENCE.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
    listed={line.split('  ',1)[1] for line in (EVIDENCE/'SHA256SUMS').read_text().splitlines()}
    require(expected_files==listed,'checksum manifest file set mismatch')
    print(json.dumps({'verification':'passed','baseHead':BASE,'cellCount':240,'selectedUpdates':105,'retained':135,'holds':0,'nonTargetChanges':0,'orderedCatalogStructures':'unchanged','placeholderMarkupNumericProtectedLiterals':'passed','wantedLabels':'exact match in all 12 locales','evidenceChecksums':len(listed)},ensure_ascii=False,indent=2))
except Exception as exc:
    print(f'ERROR: {exc}',file=sys.stderr); sys.exit(1)
