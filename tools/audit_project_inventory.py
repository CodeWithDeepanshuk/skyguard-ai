"""Read-only project inventory; writes separate audit artifacts, never source edits.
File role classification is evidence-assisted triage, not proof of scientific validity.
"""
from pathlib import Path
import ast, collections, hashlib, json, zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables'/'FOLDER_AUDIT_2026_09_11'
TEXT_EXT={'.py','.js','.cjs','.css','.html','.md','.json','.txt','.ps1','.bat','.yml','.yaml'}

def main():
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and OUT not in p.parents)
    texts={}; trees={}; checks={}; errors=[]
    for p in files:
        rel=p.relative_to(ROOT).as_posix()
        if p.suffix in TEXT_EXT and p.stat().st_size<8_000_000:
            try: texts[rel]=p.read_text(encoding='utf-8-sig')
            except UnicodeDecodeError:
                texts[rel]=p.read_text(encoding='latin-1')
                checks[rel]='Non-UTF8 text; inspected with Latin-1 fallback (encoding not independently confirmed)'
            except Exception as e: errors.append([rel,str(e)]);continue
        try:
            if p.suffix=='.py':
                trees[rel]=ast.parse(texts.get(rel,p.read_text(encoding='utf-8-sig')))
                checks[rel]='Python AST valid; not all execution paths tested'
            elif p.suffix=='.json':
                json.loads(p.read_text(encoding='utf-8-sig'));checks[rel]='JSON parses; values not independently verified'
            elif p.suffix=='.ipynb':
                notebook=json.loads(p.read_text(encoding='utf-8-sig'))
                code=[c for c in notebook.get('cells',[]) if c.get('cell_type')=='code']
                errs=[o.get('ename','error') for c in code for o in c.get('outputs',[]) if o.get('output_type')=='error']
                checks[rel]=f'Notebook JSON valid; {len(code)} code cells; {len(errs)} saved error outputs; not executed in audit'
            elif p.suffix.lower() in {'.zip','.pptx','.docx'}:
                with zipfile.ZipFile(p) as z: checks[rel]=f'ZIP directory readable; {len(z.infolist())} members; contents not semantically reviewed'
        except Exception as e: checks[rel]='INSPECTION ERROR: '+str(e);errors.append([rel,str(e)])
    modules={}
    for rel in trees:
        if rel.startswith('src/'):
            name=rel[4:-3].replace('/','.')
            if name.endswith('.__init__'):name=name[:-9]
            modules[name]=rel
    edges={}
    for name,rel in modules.items():
        imports=set(); package=name if rel.endswith('/__init__.py') else name.rpartition('.')[0]
        for node in ast.walk(trees[rel]):
            if isinstance(node,ast.Import): imports.update(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:
                    parts=package.split('.')
                    prefix='.'.join(parts[:len(parts)-node.level+1]+([prefix] if prefix else []))
                imports.add(prefix); imports.update(prefix+'.'+a.name for a in node.names)
        edges[name]={i for i in imports if i in modules}
    active=set(); queue=['skyguard.api.app']
    while queue:
        module=queue.pop()
        if module in active:continue
        active.add(module);queue.extend(edges.get(module,set()))
    runtime={modules[m] for m in active if m in modules}
    active_assets={'models/phase10_final.joblib','models/phase10_climatology.joblib','config/stations.csv','reports/qc_baseline.json','reports/replay_scenarios.json','reports/data_validation.json','reports/phase10_final.json','reports/correction_health.json','reports/safe_repair.json','reports/streaming_platform.json','reports/competition_readiness.json'}
    rows=[]; hashes=collections.defaultdict(list)
    for p in files:
        rel=p.relative_to(ROOT).as_posix(); top=rel.split('/')[0]
        category='MANUAL_REVIEW'; role='Purpose not established from path alone'; action='Inspect before archiving'; requirement='Unconfirmed'
        if '__pycache__' in rel or top=='.pytest_cache':category='GENERATED_CACHE';role='Interpreter/test cache, not model knowledge';action='Regenerable; no deletion performed';requirement='None directly'
        elif rel in runtime:category='RUNTIME_CODE';role='Reachable in local API static import graph';action='Keep; import reachability does not prove every function executes';requirement='Detection / QC / incidents / serving'
        elif rel in active_assets:category='RUNTIME_ASSET';role='Explicit source reference in API/live path (some are offline evidence)';action='Keep';requirement='Model inference / configuration / evaluation'
        elif top=='config':category='DEVELOPMENT_CONFIG';role='DWD source/station configuration for multi-climate experiments';action='Keep for reproducibility; not direct METAR runtime configuration';requirement='Data / transfer evaluation'
        elif top=='dashboard':category='DASHBOARD';role='Presentation assets or map library/data; does not train the model';action='Keep referenced assets and licenses';requirement='Visualization / explainability'
        elif top=='tests':category='TEST';role='Regression/unit test or test support';action='Keep; passing tests are not accuracy evidence';requirement='Correct implementation'
        elif top in {'tools','src'}:category='DEVELOPMENT_CODE';role='Training, preparation, audit, profiling or experiment utility; not reached by API import graph';action='Keep for reproducibility; review before executing';requirement='Development / validation'
        elif top=='models':category='NONDEPLOYED_MODEL';role='Historical/alternative model or policy; not one of two direct live model loads';action='Archive logically; do not advertise as deployed';requirement='Experimental comparison'
        elif top=='notebooks':category='NOTEBOOK_EXPERIMENT';role='Colab training/analysis workflow, not automatically deployed';action='Keep versioned; verify outputs and leakage before promotion';requirement='Development / comparison'
        elif top=='reports' or top=='iteration 10 result':category='EVALUATION_EVIDENCE';role='Generated benchmark/audit/experiment output, not necessarily current or successful';action='Keep provenance; do not mix experiment scores';requirement='Evaluation / reproducibility'
        elif top=='docs' or rel=='README.md':category='DOCUMENTATION';role='Methodology, use case, operation or audit narrative; may be stale';action='Reconcile claims with current code/results';requirement='Executable delivery documentation'
        elif top=='deliverables':category='DELIVERY_PACKAGE';role='Packaged notebook/data/presentation handoff; may duplicate source artifacts';action='Keep release packages; not needed in live runtime';requirement='Reproducible delivery'
        elif top=='Letter to write':category='ADMINISTRATIVE';role='Data-access correspondence, not ML implementation';action='Keep privately outside public deployment';requirement='Data-access enablement'
        elif top=='data':
            sub=rel.split('/')[1]
            category='DATA_'+sub.upper();role={'raw':'Source observations; no genuine fault labels implied','manifest':'Source provenance/checksums','processed':'Normalized historical observations','labelled':'Historical weather with injected anomaly labels','features':'Earlier derived feature tables','features_phase10':'Three-parameter feature tables for model development/evaluation','predictions':'Earlier model outputs','predictions_phase10':'Phase10 model outputs','incidents':'Historical incident/repair/health evidence, not current live health','demo':'Packaged offline replay scenarios','live':'Mutable observation cache; timestamp freshness must be checked','runtime':'Local mutable SQLite runtime state','iteration8':'DWD curriculum development data','iteration10':'Revised India development data','blind_2025':'Previously opened holdout evidence; do not reuse for tuning'}.get(sub,'Development data; detailed purpose requires inspection')
            action='Preserve lineage; not all data belongs in deployment';requirement='Data / training / evaluation'
        elif p.suffix=='.pptx':category='PRESENTATION';role='Presentation deck; not executable model';action='Check claims before presenting';requirement='Demonstration'
        elif p.name in {'Dockerfile','requirements.txt','.gitignore','.dockerignore','start_skyguard.bat','start_skyguard.ps1','verify_skyguard.ps1'}:category='DEPLOYMENT';role='Environment, launch, exclusion or verification configuration';action='Keep; audit deployment scope and failure handling';requirement='Deployability'
        source=texts.get(rel,''); description=''
        if rel in trees:description=(ast.get_docstring(trees[rel]) or '').split('\n')[0][:180]
        elif p.suffix=='.md':description=next((s.lstrip('# ').strip() for s in source.splitlines() if s.startswith('#')),'')[:180]
        digest=hashlib.sha256()
        try:
            with p.open('rb') as handle:
                for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
            sha=digest.hexdigest();hashes[sha].append(rel)
        except OSError as e:sha='unreadable';errors.append([rel,str(e)])
        references=[r for r,t in texts.items() if r!=rel and p.name in t][:5]
        rows.append(dict(path=rel,bytes=p.stat().st_size,category=category,role=role,requirement=requirement,action=action,description=description,inspection=checks.get(rel,'Inventory/hash only; not fully content-validated'),sha256=sha,basename_mentions=references))
    OUT.mkdir(parents=True,exist_ok=True)
    duplicates=[v for v in hashes.values() if len(v)>1]
    stats={'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'categories':dict(collections.Counter(r['category'] for r in rows)),'duplicate_groups':len(duplicates),'inspection_errors':errors,'runtime_import_files':sorted(runtime),'scope':'All filesystem files including caches. Audit output directory excluded. No training or protected-test scoring. Binary models not deserialized. Classification is triage, not scientific certification.'}
    (OUT/'inventory.json').write_text(json.dumps({'summary':stats,'files':rows,'exact_duplicate_groups':duplicates},indent=2),encoding='utf-8')
    def safe(v):return str(v).replace('|','/').replace('\n',' ')
    lines=['# Every-file SIH26073 relevance inventory','',stats['scope'],'','Every file has a row below. Runtime means static import reachability or explicit reference, not proven execution. Name mentions are weak evidence, not an orphan detector.','',f"Files: {len(rows)}; total: {stats['bytes']/1024**3:.2f} GiB; exact duplicate groups: {len(duplicates)}.",'']
    for top in sorted({r['path'].split('/')[0] for r in rows}):
        lines += ['## '+top,'','| File | Category | Contribution / role | Inspection | Recommended handling |','|---|---|---|---|---|']
        for r in rows:
            if r['path'].split('/')[0]==top:lines.append('| '+' | '.join(safe(v) for v in [r['path'],r['category'],r['role']+(' — '+r['description'] if r['description'] else ''),r['inspection'],r['action']])+' |')
        lines.append('')
    lines += ['## Exact byte-identical groups','','Copies are not automatically waste: a release package may deliberately preserve an artifact.']
    for group in duplicates:lines.append('- '+'; '.join('`'+r+'`' for r in group))
    (OUT/'EVERY_FILE_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
