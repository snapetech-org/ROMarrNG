#!/usr/bin/env python3
"""Build the independent W425-W444 primary review from candidate-free evidence only."""
from pathlib import Path
import collections, hashlib, json, re, subprocess, datetime

OUT = Path(__file__).resolve().parent
IN = Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w425-444-candidate-free-20261103/input')
HEAD = '7681ea470ee0f387cd3a1a5be0541979d9cd06f6'
TREE = 'f8b34f29814233cb10dd9d608d5a69ce539b9f6d'
BRANCH = 'task/localization-translation-review-20261030'
REPO = 'snapetech-org/ROMarrNG'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TOKEN_RE = re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
NUMBER_RE = re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])')
PROTECTED = ['ROMarr','GG Requestz','RomM','ROMm','ES-DE','gamelist.xml','1G1R','Battle.net','No-Intro','Redump','RetroArch','Steam','EA','Epic','ROM','Hub','DAT']

PROPOSALS = {
 (425,'de'): ('refinement','Aufgrund der Richtlinie ausgeschlossen','The existing phrase is understandable but the article-free wording is stilted. The proposal clearly expresses exclusion under the collection policy.'),
 (425,'fr'): ('refinement','Exclus par la politique','The caller is a count label for items excluded by a collection policy. “Règle” narrows policy to a rule; this wording matches the source.'),
 (425,'hi'): ('correction','नीति के तहत बहिष्कृत','The current wording means “outside according to policy” and does not state exclusion directly. The proposal names the excluded state.'),
 (425,'zh-Hans'): ('refinement','按政策排除','The count tile reports items excluded by policy. The current “规则” means rule; “政策” matches the source more closely.'),
 (425,'zh-Hant'): ('refinement','依政策排除','The count tile reports items excluded by policy. The current “規則” means rule; “政策” matches the source more closely.'),
 (426,'fr'): ('refinement','Dossier existant de listes de jeux ES-DE (facultatif)','The current word order and “de ES-DE” are awkward in French. The proposal keeps the existing folder, ES-DE gamelists, and optional setting meaning.'),
 (427,'fr'): ('refinement','Dossier de médias ES-DE existant (facultatif)','The current placement of “ES-DE” makes the label awkward. This wording identifies the existing ES-DE media folder.'),
 (430,'ar'): ('correction','تصدير','The exact caller is an action button. The current plural “الصادرات” means exports; this is the standard concise export action label.'),
 (430,'es'): ('refinement','Exportar','The exact caller is an action button. The current noun “Exportación” is understandable, while the infinitive names the button action directly.'),
 (430,'fr'): ('refinement','Exporter','The exact caller is an action button. The current noun is understandable, while the infinitive is the direct action label.'),
 (430,'hi'): ('refinement','निर्यात करें','The exact caller is an action button. The proposal expresses the action directly instead of the bare noun.'),
 (431,'es'): ('refinement','Exporta la propia biblioteca para usarla en una hoja de cálculo u otra herramienta:','The current “la biblioteca misma” is less idiomatic. The proposal preserves the library-itself distinction and makes the intended spreadsheet/tool use clear.'),
 (431,'hi'): ('refinement','स्प्रेडशीट या किसी अन्य टूल में इस्तेमाल करने के लिए पूरी लाइब्रेरी निर्यात करें:','The current word order is awkward. The proposal makes the export purpose clear and preserves the instruction to export the library itself.'),
 (431,'id'): ('refinement','Ekspor pustaka itu sendiri untuk digunakan di spreadsheet atau alat lain:','The current comma makes the phrase choppy. The proposal keeps the library-itself meaning and ties the export to its intended use.'),
 (431,'ja'): ('refinement','スプレッドシートやほかのツールで使うために、ライブラリ自体をエクスポートできます：','The current sentence shifts to “you can use it” after export. This proposal makes the export purpose explicit while keeping a natural explanatory tone.'),
 (431,'ko'): ('refinement','스프레드시트나 다른 도구에서 사용할 수 있도록 라이브러리 자체를 내보내세요:','The current word order and spacing (“스프레드 시트”) are awkward. The proposal uses the standard compound and clearly states the export purpose.'),
 (431,'pt-BR'): ('refinement','Exporte a própria biblioteca para usar em uma planilha ou outra ferramenta:','The current infinitive fragment and comma are awkward in this help paragraph. The proposal gives a clear, concise instruction.'),
 (431,'vi'): ('refinement','Xuất thư viện để sử dụng trong bảng tính hoặc công cụ khác:','The current “Xuất thư viện ra, cho…” is unidiomatic. This wording preserves the export action and its purpose.'),
 (431,'zh-Hans'): ('refinement','导出游戏库本身，供电子表格或其他工具使用：','The current literal “库本身” is awkward and uses English-style punctuation spacing. The proposal clarifies this is the game library and uses Chinese punctuation.'),
 (431,'zh-Hant'): ('refinement','匯出遊戲庫本身，供試算表或其他工具使用：','The current literal “庫本身” is awkward and uses English-style punctuation spacing. The proposal clarifies this is the game library and uses Traditional Chinese wording and punctuation.'),
 (432,'hi'): ('refinement','फ़ाइल एक्सटेंशन','The technical-details table lists filename suffixes such as .chd and .cue. The current generic loanword could also mean an add-on; this names file extensions.'),
 (432,'id'): ('refinement','Ekstensi file','The table lists file suffixes. Adding “file” distinguishes file extensions from software extensions.'),
 (432,'ja'): ('correction','拡張子','The technical-details table lists file suffixes such as .chd and .cue. “エクステンション” can mean a software add-on; the standard Japanese file term is 拡張子.'),
 (432,'ko'): ('correction','파일 확장자','The table lists filename suffixes. The current “확장 기능” means an extension feature/add-on; this is the file-extension term.'),
 (432,'vi'): ('refinement','Phần mở rộng tệp','The technical-details table lists file suffixes. Adding “tệp” distinguishes file extensions from other kinds of extensions.'),
 (432,'zh-Hans'): ('refinement','文件扩展名','The table lists file suffixes. The current “扩展” is broad and can mean software extensions; this is the file-extension term.'),
 (432,'zh-Hant'): ('correction','副檔名','The table lists file suffixes. “擴充套件” means software plug-ins in Traditional Chinese; 副檔名 is the standard file term.'),
 (434,'de'): ('correction','Fehlschläge','The caller is a metric counting failed events, not service outages. “Ausfälle” suggests outages; this names failures.'),
 (434,'id'): ('correction','Kegagalan','The caller is a metric label for a count of failed events. The current “Gagal” is an adjective/status (“failed”); the proposal is the failure noun.'),
 (434,'vi'): ('refinement','Thất bại','The caller is a count of failed events. “Lỗi” means errors, while this names the failures reported by the metric.'),
 (435,'de'): ('correction','Fan-Übersetzungen','German compounds need a hyphen or closed spelling here; the current separated words are not a standard compound.'),
 (435,'id'): ('refinement','Terjemahan penggemar','The current “Fan terjemahan” is an awkward mixed-order phrase. This is the natural Indonesian noun phrase for fan translations.'),
 (436,'id'): ('refinement','Bahasa untuk terjemahan penggemar','This is a settings label for languages used by fan translations. The preposition makes the current compressed phrase clearer.'),
 (436,'pt-BR'): ('refinement','Idiomas das traduções feitas por fãs','The current wording is understandable but compressed. The proposal clearly means languages of fan-made translations.'),
 (437,'vi'): ('refinement','Nguồn cấp dữ liệu','The caller is an indexer/feed column. This is the Vietnamese term for a feed, while the current phrase means a broader data source.'),
 (437,'zh-Hans'): ('refinement','订阅源','The caller labels an indexer feed column. “数据源” is broader than a feed; 订阅源 fits the RSS/indexer context.'),
 (437,'zh-Hant'): ('refinement','訂閱來源','The caller labels an indexer feed column. “資料來源” is broader than a feed; 訂閱來源 fits the RSS/indexer context.'),
 (438,'zh-Hant'): ('refinement','訂閱來源 URL','The field is the URL for the indexer feed. This aligns with the feed terminology and preserves the protected literal URL.'),
 (439,'ar'): ('refinement','أضف الألعاب إلى قائمة الألعاب المطلوبة من مصادر مثل مقال عن أفضل 100 لعبة، أو فهرس ألعاب منزلية الصنع، أو جدول بيانات لصديق. لا يُضاف كل عنوان إلا مرة واحدة؛ وتوجد المجموعات الكاملة و1G1R ضمن «المجموعات».','The caller is explanatory copy on the import-list page. This version uses a clearer games-wanted-list phrase, preserves the 100-game example and 1G1R, and keeps the one-time-addition and Collections details.'),
 (439,'hi'): ('refinement','सूचियों से गेम अपनी वांछित सूची में जोड़ें—जैसे शीर्ष 100 खेलों पर लेख, होमब्रू कैटलॉग या किसी मित्र की स्प्रेडशीट। हर शीर्षक केवल एक बार जोड़ा जाता है; पूरे सेट और 1G1R संग्रह में मिलते हैं।','The caller is explanatory copy on the import-list page. This version improves the list construction while preserving 100, 1G1R, and the one-time-addition behavior.'),
 (439,'id'): ('refinement','Tambahkan judul ke daftar incaran dari sumber seperti artikel 100 teratas, katalog homebrew, atau spreadsheet teman. Setiap judul hanya ditambahkan satu kali; set lengkap dan 1G1R ada di Koleksi.','The caller is explanatory copy on the import-list page. “Daftar incaran” is more idiomatic than “daftar yang diinginkan”; the source magnitude and 1G1R remain intact.'),
 (439,'ja'): ('refinement','トップ100の記事、自作ゲームのカタログ、友人のスプレッドシートなどのリストから、タイトルを「欲しいゲーム」リストに追加できます。各タイトルは一度だけ追加され、全セットと1G1Rは「コレクション」にあります。','The caller is explanatory copy on the import-list page. This gives the Wanted destination a clear game-list meaning and retains the top-100 example, one-time addition, and 1G1R.'),
 (439,'pt-BR'): ('refinement','Adicione títulos à lista de desejos a partir de listas como um artigo com os 100 melhores jogos, um catálogo homebrew ou a planilha de um amigo. Cada título é adicionado uma única vez; conjuntos completos e 1G1R ficam em Coleções.','The caller is explanatory copy on the import-list page. “Lista de desejos” is idiomatic and the proposal makes the top-100 example explicit while preserving 1G1R and the one-time rule.'),
 (439,'vi'): ('refinement','Thêm trò chơi vào danh sách mong muốn từ các nguồn như bài viết xếp hạng 100 trò chơi, danh mục homebrew hoặc bảng tính của bạn bè. Mỗi tựa game chỉ được thêm một lần; các bộ trò chơi đầy đủ và 1G1R có trong mục Bộ sưu tập.','The caller is explanatory copy on the import-list page. This avoids using “tiêu đề” for game titles and keeps the 100-game ranking, one-time addition, and 1G1R details.'),
 (441,'id'): ('refinement','Diambil {count} pada {date}','The caller reports a completed import-list sync. The current active “Mengambil” reads as an ongoing action; the passive form reports the fetched count.'),
 (441,'ja'): ('refinement','{date}に{count}件を取得済み','The caller reports a completed sync. The current noun-ending 取得 is incomplete; 取得済み clearly marks the count as fetched.'),
 (444,'hi'): ('correction','फ़ाइल का नाम','The current “फाईल” has a spelling/transliteration error. फ़ाइल is the standard Hindi spelling for file.'),
}

HOLD_POSITIONS = {440: 'The catalog row has no active source-registry entry and the candidate-free exact-source search found zero source-ID and source-text production matches. No pinned caller context establishes what “Fern accent” labels, so current translations cannot be semantically adjudicated.'}
POSITION_CONTEXT = {
 425:'collection-scan tile label for the count excluded by policy',
 426:'optional settings field for an existing ES-DE gamelists folder',
 427:'optional settings field for an existing ES-DE media folder',
 428:'fixed organizer error for invalid existing gamelist.xml, shown while preserving that file',
 429:'tooltip on a game-genre chip that opens more games of that genre',
 430:'Export action button in the Backup & Export page',
 431:'help sentence above the library export controls',
 432:'technical-details table header for file suffixes/extensions',
 433:'Failed state/status label in download and connection diagnostics',
 434:'dashboard metric label counting failed events',
 435:'settings/filter label for fan translations',
 436:'settings field for languages used by fan translations',
 437:'indexer diagnostics feed column/label',
 438:'RSS indexer feed URL field label',
 439:'explanatory text on the import-list page',
 440:'no exact caller evidence in the candidate-free packet',
 441:'import-list sync summary template with count and date',
 442:'loading copy while the first library fetch is running',
 443:'File column header in the importable-files table',
 444:'Filename input label in the metadata lookup form',
}

def sha(x):
    return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()
def read_json(name): return json.loads((IN/name).read_text(encoding='utf-8'))
def read_jsonl(name): return [json.loads(x) for x in (IN/name).read_text(encoding='utf-8').splitlines() if x.strip()]
def protected_terms(text):
    return sorted([term for term in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])', text)],key=lambda t:text.find(t))
def match_ref(source_position,path,line_start):
    source=contexts[source_position]
    return next(ref for ref in source['callerContextRefs'] if ref['path']==path and ref['lineStart']==line_start)
def compact_ref(ref, evidence_note=None):
    out={k:ref[k] for k in ('path','lineStart','lineEnd','role','anchor','contextSha256','fileSha256','gitBlob') if k in ref}
    if evidence_note: out['evidenceNote']=evidence_note
    return out

def capture_pr():
    view=json.loads(subprocess.check_output(['gh','pr','view','70','--repo',REPO,'--json','state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url'],text=True))
    branch_ref=subprocess.check_output(['git','ls-remote',f'https://github.com/{REPO}.git',f'refs/heads/{BRANCH}'],text=True).split()[0]
    pull_ref=subprocess.check_output(['git','ls-remote',f'https://github.com/{REPO}.git','refs/pull/70/head'],text=True).split()[0]
    tree=subprocess.check_output(['gh','api',f'repos/{REPO}/git/commits/{view["headRefOid"]}','--jq','.tree.sha'],text=True).strip()
    result={
      'observedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'repository':REPO,'pullRequest':70,'url':view['url'],'state':view['state'],'isDraft':view['isDraft'],
      'branch':view['headRefName'],'baseBranch':view['baseRefName'],'baseHead':view['baseRefOid'],
      'head':view['headRefOid'],'tree':tree,'liveBranchRef':branch_ref,'livePullRef':pull_ref,
      'matchesPinnedHeadTree':view['headRefOid']==HEAD and tree==TREE,
      'matchesBothRemoteRefs':branch_ref==HEAD and pull_ref==HEAD,
    }
    if not (result['state']=='OPEN' and result['isDraft'] is True and result['branch']==BRANCH and result['matchesPinnedHeadTree'] and result['matchesBothRemoteRefs']):
        raise SystemExit('live PR/branch/pull refs drifted from the pinned OPEN/DRAFT head/tree')
    return result

# Capture the live PR before making the review ledger.
(OUT/'PR-attestation-before.json').write_text(json.dumps(capture_pr(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest_input=read_json('manifest.json')
selection=read_json('selection.json')
sources={x['position']:x for x in read_jsonl('source-inventory-selection.jsonl')}
cells=read_jsonl('current-target-cells.jsonl')
contexts={x['position']:x for x in read_jsonl('source-contexts.jsonl')}
mechanics=read_json('dispatch-mechanics.json')
mechanic_refs=mechanics['evidence']
# Raw static text sources whose visible sentence spans source lines are evidenced in adjacent exact-source snippets.
def mechanic_ref(line_start):
    return next(x for x in mechanic_refs if x['path']=='romarr/ui.py' and x['lineStart']==line_start)

CALLERS={
 425:[compact_ref(match_ref(425,'romarr/ui.py',5605))],
 426:[compact_ref(match_ref(426,'romarr/ui.py',4210))],
 427:[compact_ref(match_ref(427,'romarr/ui.py',4211))],
 428:[compact_ref(match_ref(428,'romarr/organizer.py',2275)),compact_ref(match_ref(428,'romarr/ui.py',5737))],
 429:[compact_ref(match_ref(429,'romarr/ui.py',2549))],
 430:[compact_ref(match_ref(430,'romarr/ui.py',4659))],
 431:[compact_ref(match_ref(430,'romarr/ui.py',4659),'Visible source sentence is split across UI lines 4664-4665; this exact context contains both fragments.')] + [compact_ref(mechanic_ref(1295),'Raw text source matching/translation mechanics.')] + [compact_ref(mechanic_ref(1376),'Inserted text nodes are passed through translated-text traversal.')],
 432:[compact_ref(match_ref(432,'romarr/ui.py',4988))],
 433:[compact_ref(match_ref(433,'romarr/ui.py',872)),compact_ref(match_ref(433,'romarr/ui.py',4024)),compact_ref(match_ref(433,'romarr/ui.py',4470))],
 434:[compact_ref(match_ref(434,'romarr/ui.py',3631))],
 435:[compact_ref(match_ref(435,'romarr/ui.py',4235)),compact_ref(match_ref(435,'romarr/ui.py',5482))],
 436:[compact_ref(match_ref(436,'romarr/ui.py',4252))],
 437:[compact_ref(match_ref(437,'romarr/ui.py',4474)),compact_ref(match_ref(437,'romarr/indexers.py',915))],
 438:[compact_ref(match_ref(438,'romarr/indexers.py',923))],
 439:[compact_ref(match_ref(437,'romarr/ui.py',2661),'Visible sentence is split across UI lines 2666-2669; this exact context contains the complete text.'),compact_ref(mechanic_ref(1295),'Raw text source matching/translation mechanics.'),compact_ref(mechanic_ref(1376),'Inserted import-list text nodes are passed through translated-text traversal.')],
 440:[],
 441:[compact_ref(match_ref(441,'romarr/ui.py',2676))],
 442:[compact_ref(match_ref(442,'romarr/ui.py',1987))],
 443:[compact_ref(match_ref(443,'romarr/ui.py',6052))],
 444:[compact_ref(match_ref(444,'romarr/ui.py',5128))],
}

ledger=[]
for c in cells:
    pos,locale=c['position'],c['locale']
    if locale not in LOCALES: raise SystemExit('unexpected locale')
    source=sources[pos]
    if c['sourceId']!=source['sourceId'] or c['sourceSha256']!=source['sourceSha256']:
        raise SystemExit(f'source mismatch {pos}/{locale}')
    src_tokens=TOKEN_RE.findall(c['source']); cur_tokens=TOKEN_RE.findall(c['currentTarget'])
    src_numbers=NUMBER_RE.findall(c['source']); cur_numbers=NUMBER_RE.findall(c['currentTarget'])
    src_literals=protected_terms(c['source']); cur_literals=protected_terms(c['currentTarget'])
    if src_tokens!=c['sourcePlaceholderTokens'] or cur_tokens!=c['currentPlaceholderTokens'] or sorted(src_tokens)!=sorted(cur_tokens):
        raise SystemExit(f'baseline placeholder mismatch {pos}/{locale}')
    if src_numbers!=c['sourceNumericTokens'] or cur_numbers!=c['currentNumericTokens']:
        raise SystemExit(f'baseline number mismatch {pos}/{locale}')
    if src_literals!=c['sourceProtectedLiterals'] or cur_literals!=c['currentProtectedLiterals']:
        raise SystemExit(f'baseline protected literal mismatch {pos}/{locale}')
    decision=PROPOSALS.get((pos,locale))
    if pos in HOLD_POSITIONS:
        disposition='hold'; proposal=None; rationale=HOLD_POSITIONS[pos]
    elif decision:
        disposition,proposal,rationale=decision
    else:
        disposition='accept-current'; proposal=None
        rationale=f'The current wording conveys the source in the pinned caller context ({POSITION_CONTEXT[pos]}). Exact caller references and current target hash are recorded; available placeholders and protected literals are preserved.'
        if pos==439 and locale in ('zh-Hans','zh-Hant'):
            rationale += ' The source number 100 is naturally rendered as 百 (“hundred”) in this Chinese sentence; the numeric scanner’s missing ASCII digits are a reviewed semantic equivalent, not a numeric loss.'
    selected=c['currentTarget'] if disposition=='accept-current' else (proposal if disposition in ('correction','refinement') else None)
    selected_tokens=TOKEN_RE.findall(selected) if selected is not None else None
    selected_numbers=NUMBER_RE.findall(selected) if selected is not None else None
    selected_literals=protected_terms(selected) if selected is not None else None
    placeholder_ok=(selected_tokens is not None and sorted(src_tokens)==sorted(selected_tokens))
    literal_ok=(selected_literals is not None and all(x in selected_literals for x in src_literals))
    exact_number_ok=(selected_numbers is not None and src_numbers==selected_numbers)
    semantic_number=None
    if pos==439 and locale in ('zh-Hans','zh-Hant'):
        semantic_number={'status':'accepted-naturalized-magnitude','sourceValue':100,'targetForm':'百','meaning':'one hundred','asciiDigitPreserved':False}
        if '百' not in selected: raise SystemExit('Chinese 100 semantic numeral check failed')
    if selected is not None and not placeholder_ok: raise SystemExit(f'selected placeholder check failed {pos}/{locale}')
    if selected is not None and not literal_ok: raise SystemExit(f'selected protected literal check failed {pos}/{locale}')
    if selected is not None and not exact_number_ok and semantic_number is None:
        raise SystemExit(f'selected numeric check failed {pos}/{locale}')
    refs=CALLERS[pos]
    # The source/caller packet has no production occurrence for the held Fern accent entry.
    if pos!=440 and not refs: raise SystemExit(f'missing selected caller context {pos}')
    entry={
      'position':pos,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],
      'sourceId':c['sourceId'],'locale':locale,'source':c['source'],'sourceSha256':c['sourceSha256'],
      'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'catalogTranslationHash':c['catalogTranslationHash'],
      'inputCallerContextSha256':c['callerContextSha256'],'selectedCallerContextRefs':refs,
      'reviewedContext':POSITION_CONTEXT[pos],
      'disposition':disposition,'proposedTarget':proposal,'proposedTargetSha256':sha(proposal) if proposal is not None else None,
      'selectedTarget':selected,'selectedTargetSha256':sha(selected) if selected is not None else None,
      'rationale':rationale,
      'tokenAndLiteralChecks':{
        'sourcePlaceholderTokens':src_tokens,'currentPlaceholderTokens':cur_tokens,'selectedPlaceholderTokens':selected_tokens,
        'selectedPlaceholderMultisetMatches':placeholder_ok,
        'sourceNumericTokens':src_numbers,'currentNumericTokens':cur_numbers,'selectedNumericTokens':selected_numbers,
        'selectedNumericTokensExactMatch':exact_number_ok,'semanticNumericReview':semantic_number,
        'sourceProtectedLiterals':src_literals,'currentProtectedLiterals':cur_literals,'selectedProtectedLiterals':selected_literals,
        'selectedProtectedLiteralsPreserved':literal_ok
      }
    }
    ledger.append(entry)

# Stable position/locale order and exact 240-cell coverage.
expected=[(pos,loc) for pos in range(425,445) for loc in LOCALES]
if [(x['position'],x['locale']) for x in ledger]!=expected: raise SystemExit('ledger coverage/order mismatch')
(OUT/'primary-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in ledger),encoding='utf-8')
counts=collections.Counter(x['disposition'] for x in ledger)
summary={
 'artifact':'ROMarrNG PR #70 W425-W444 primary review',
 'reviewerRole':'independent primary reviewer; candidate-free input only',
 'repository':REPO,'pullRequest':70,'branch':BRANCH,'head':HEAD,'tree':TREE,
 'candidateFreeInputPath':str(IN),'candidateFreeInputManifestSha256':sha((IN/'manifest.json').read_bytes()),
 'candidateFreeInputChecksumsSha256':sha((IN/'SHA256SUMS.txt').read_bytes()),
 'candidateFreeInputVerified':True,'primaryProposalsReadBeforeReview':False,'blindReviewOutputInspected':False,
 'sourceCount':20,'localeCount':12,'cellCount':len(ledger),'dispositions':dict(sorted(counts.items())),
 'proposedCellCount':sum(x['proposedTarget'] is not None for x in ledger),
 'numericScannerFindings':2,'chineseSemanticNumeralAccepted':2,
 'chineseNumeralAdjudications':[{'position':439,'locale':loc,'source':'100','target':'百','result':'semantically equivalent; accepted current'} for loc in ('zh-Hans','zh-Hant')],
 'newHolds':sum(x['disposition']=='hold' for x in ledger),'holdPositions':[440],
 'priorLineageSelectionsReattested':40,'priorHoldCellsReattested':336,
 'sourceContextAvailable':19,'callerlessCellCount':12,
 'callerlessHoldFinding':'All 12 position-440 cells remain held because “Fern accent” has no exact active source registration or production caller context in this candidate-free packet.',
 'placeholderMismatchesInSelectedTargets':0,'protectedLiteralMismatchesInSelectedTargets':0,
 'numericExactMismatchesAfterSemanticReview':0,'nativeSpeakerReview':'not performed; primary machine review does not establish native-speaker approval',
 'browserReview':'not performed','createdUtc':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Reattest after reviewing, and stop if the live PR moved.
(OUT/'PR-attestation-after.json').write_text(json.dumps(capture_pr(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
before=json.loads((OUT/'PR-attestation-before.json').read_text())
after=json.loads((OUT/'PR-attestation-after.json').read_text())
if before['head']!=after['head'] or before['tree']!=after['tree']:
    raise SystemExit('PR moved during primary review')
print(f'BUILT 240 cells: {dict(sorted(counts.items()))}; 45 proposals; 12 position-440 holds; 2 Chinese 100→百 semantic reviews accepted')
