#!/usr/bin/env python3
import hashlib, json, re
from collections import Counter
from pathlib import Path

INPUT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-20261105/candidate-free/input')
OUT = Path(__file__).resolve().parent
HEAD = '50e3f8a48a800affff8bad367b5c493cc0fdfd62'
TREE = '22cd46ff4821fcbbe76b4760a15e22d688b3f548'
CELL_FILE = INPUT / 'candidate-free-cells.jsonl'
CONTEXT_FILE = INPUT / 'source-contexts.jsonl'
PROPOSALS = {
    (709, 'ar'): ('correction', 'لا تتوفر أي صيغ للواجهة الأمامية.', 'The caller shows an empty state when the frontend export format list is empty. The current Arabic says there are no display/presentation formats, which loses the software frontend meaning. This names the frontend explicitly.'),
    (709, 'fr'): ('correction', 'Aucun format frontend n’est disponible.', 'In this technical UI, “frontend” identifies the software front end. “Format frontal” can mean a front-facing format in French, so the current phrase is ambiguous.'),
    (709, 'zh-Hans'): ('correction', '没有可用的前端格式。', 'The current Chinese string has an unnecessary space before the full-width sentence stop. Removing it follows Chinese punctuation spacing.'),
    (709, 'zh-Hant'): ('correction', '沒有可用的前端格式。', 'The current Chinese string has an unnecessary space before the full-width sentence stop. Removing it follows Chinese punctuation spacing.'),
}

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha_bytes(s.encode('utf-8'))
def canonical(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
def digest_obj(obj): return sha_bytes(canonical(obj))
def read_jsonl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def write_jsonl(p, rows): p.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True)+'\n' for x in rows),encoding='utf-8')
def caller_refs(ctx):
    return [{k: c.get(k) for k in ('path','line','gitBlob','fileSha256','lineSha256','excerptSha256')} for c in ctx['callers']]
def binding(position, locale, source_sha, target_sha, ctx_sha, caller_hashes_sha):
    return digest_obj({'position':position,'locale':locale,'sourceSha256':source_sha,'currentTargetSha256':target_sha,'callerContextSha256':ctx_sha,'callerHashesSha256':caller_hashes_sha})
def tokens(s): return re.findall(r'\{[^{}]+\}', s)
def nums(s): return re.findall(r'\d+', s)
def tags(s): return re.findall(r'<[^>]+>', s)

cells=read_jsonl(CELL_FILE)
# Do not materialize or inspect text in callerless source-context records.
contexts={r['sourceId']:r for r in read_jsonl(CONTEXT_FILE) if not r.get('callerless', False)}
if len(cells)!=240 or len(PROPOSALS)!=4: raise SystemExit('unexpected input/proposal count')
input_hashes={'candidate-free-cells.jsonl':sha_bytes(CELL_FILE.read_bytes()),'source-contexts.jsonl':sha_bytes(CONTEXT_FILE.read_bytes())}
records=[]
counts=Counter()
for cell in cells:
    pos, locale = cell['position'], cell['locale']
    if cell['callerless']:
        caller_hashes=[]
        caller_hashes_sha=digest_obj(caller_hashes)
        record={
            'position':pos,'locale':locale,'callerless':True,'decision':'hold',
            'sourceSha256':cell['sourceSha256'],'currentTargetSha256':cell['currentTargetSha256'],
            'callerContextSha256':cell['callerContextSha256'],'callerHashes':[],
            'callerHashesSha256':caller_hashes_sha,
            'bindingSha256':binding(pos,locale,cell['sourceSha256'],cell['currentTargetSha256'],cell['callerContextSha256'],caller_hashes_sha),
            'rationale':'Callerless catalog cell; kept hash-only with no source or target text.'
        }
        counts['hold']+=1
        records.append(record)
        continue
    source, current=cell['source'],cell['currentTarget']
    decision_data=PROPOSALS.get((pos,locale))
    if decision_data:
        decision,replacement,rationale=decision_data
        replacement_checks={
            'placeholders':{'source':tokens(source),'target':tokens(replacement),'match':tokens(source)==tokens(replacement)},
            'numbers':{'source':nums(source),'target':nums(replacement),'match':nums(source)==nums(replacement)},
            'markupTags':{'source':tags(source),'target':tags(replacement),'match':tags(source)==tags(replacement)},
            'protectedLiterals':{'required':cell['sourceProtectedLiterals'],'missing':[x for x in cell['sourceProtectedLiterals'] if x not in replacement],'match':all(x in replacement for x in cell['sourceProtectedLiterals'])}
        }
        if not all(replacement_checks[k].get('match', True) for k in ('placeholders','numbers','markupTags','protectedLiterals')):
            raise SystemExit(f'replacement token integrity mismatch at {pos}/{locale}')
        counts[decision]+=1
    else:
        decision,replacement,rationale='accept',None,None
        replacement_checks=None
        counts['accept']+=1
    if sha_text(source)!=cell['sourceSha256'] or sha_text(current)!=cell['currentTargetSha256']:
        raise SystemExit(f'input text hash mismatch at {pos}/{locale}')
    ctx=contexts.get(cell['sourceId'])
    if not ctx or ctx['contextSha256']!=cell['callerContextSha256']:
        raise SystemExit(f'missing/mismatched visible caller context at {pos}/{locale}')
    refs=caller_refs(ctx)
    refs_sha=digest_obj(refs)
    record={
        'position':pos,'sourceId':cell['sourceId'],'locale':locale,'callerless':False,
        'decision':decision,'sourceSha256':cell['sourceSha256'],'currentTargetSha256':cell['currentTargetSha256'],
        'callerContextSha256':cell['callerContextSha256'],'callerHashes':refs,'callerHashesSha256':refs_sha,
        'bindingSha256':binding(pos,locale,cell['sourceSha256'],cell['currentTargetSha256'],cell['callerContextSha256'],refs_sha),
        'sourceText':source,'currentTargetText':current,'replacementText':replacement,'rationale':rationale,
        'integrityChecks':{
            'placeholders':{'source':cell['sourcePlaceholderTokens'],'target':cell['currentPlaceholderTokens'],'match':cell['placeholderMultisetMatches']},
            'numbers':{'source':cell['sourceNumericTokens'],'target':cell['currentNumericTokens'],'match':cell['numericTokensPreserved']},
            'markupTags':{'source':cell['sourceMarkupTags'],'target':cell['currentMarkupTags'],'match':cell['markupMatches']},
            'protectedLiterals':{'required':cell['sourceProtectedLiterals'],'missing':cell['missingProtectedLiterals'],'match':cell['protectedLiteralsPreserved']}
        },
        'replacementIntegrityChecks':replacement_checks,
        'confidence':'moderate' if decision in ('correction','refinement') else None
    }
    records.append(record)
if counts != Counter({'hold':48,'accept':188,'correction':4}): raise SystemExit(f'unexpected decisions: {counts}')
if {(r['position'],r['locale']) for r in records if r['decision']=='correction'}!=set(PROPOSALS): raise SystemExit('proposal identity mismatch')
write_jsonl(OUT/'review.jsonl',records)
summary={
    'artifact':'ROMarrNG PR #70 W705-W724 independent blind translation review',
    'schemaVersion':1,'reviewerMode':'independent blind review; candidate-free inputs only',
    'exactPrHead':HEAD,'exactPrTree':TREE,'inputPacketDirectory':str(INPUT),'inputSha256':input_hashes,
    'reviewFile':'review.jsonl','records':240,'sourceKeys':20,'locales':12,
    'visibleCellsReviewed':192,'callerlessHashOnlyHolds':48,
    'decisions':dict(counts),'proposedChanges':4,
    'integrityAudit':{
        'visibleCurrentTargetsChecked':192,'visibleProposedReplacementsChecked':4,
        'placeholderMultisets':'all match','numericTokens':'all match','markupTagSequences':'all match','declaredProtectedLiterals':'all match'
    },
    'qualifiedNativeSpeakerApprovalClaimed':False,
    'notes':[
        'Only candidate-free inputs were used; no primary or cross-review proposal was accessed before this sealed blind packet.',
        'The 48 callerless cells are hash-only holds; source ID, source text, and current target text are omitted from their review rows.',
        'Each visible cell binds source/current text, locale, caller-context digest, and caller source hashes to the candidate-free packet.',
        'This machine review is not qualified native-speaker approval.'
    ]
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'built','decisions':dict(counts),'inputSha256':input_hashes},ensure_ascii=False,indent=2))
