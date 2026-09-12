"""Build the top-to-bottom Iteration 13 scientific benchmark Colab notebook."""
from pathlib import Path
import ast, json

ROOT=Path(__file__).resolve().parents[1]
NAME='SkyGuard_AI_Iteration_13_SIH26073_Benchmark.ipynb'

def build():
    cells=[]
    def md(title,body): cells.append({'cell_type':'markdown','metadata':{},'source':(f'# {title}\n\n'+body).splitlines(keepends=True)})
    def code(value):
        ast.parse(value); cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':value.splitlines(keepends=True)})
    md('SkyGuard AI — Iteration 13','Genuine IMD AWS + controlled fault injection + event-aware hybrid anomaly benchmark. Metrics are produced only after genuine-data and timezone gates pass. Phase 10 remains the production baseline.')
    md('0. Environment','Install deterministic scientific dependencies and mount Drive. GPU is optional; the benchmark baselines are CPU-oriented.')
    code("""import sys,subprocess
subprocess.check_call([sys.executable,'-m','pip','install','-q','pandas>=2.2,<3','numpy>=1.26,<3','pyarrow>=16,<24','scikit-learn>=1.5,<1.9','pyyaml>=6,<7'])
from google.colab import drive
drive.mount('/content/drive')""")
    md('1. Repository/data configuration','The repository is cloned fresh. Private observations stay in Drive and are never added to Git.')
    code("""from pathlib import Path
import os,subprocess,sys,json,zipfile
REPO=Path('/content/skyguard-ai')
if not REPO.exists(): subprocess.check_call(['git','clone','-q','https://github.com/CodeWithDeepanshuk/skyguard-ai.git',str(REPO)])
else: subprocess.check_call(['git','-C',str(REPO),'pull','--ff-only'])
CODE_COMMIT=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
DATA=Path('/content/drive/MyDrive/SkyGuard_AI_GPU/experiments/iteration12_genuine_imd_aws_v1/processed/imd_aws_observations_deduplicated.parquet')
OUT=Path('/content/drive/MyDrive/SkyGuard_AI_GPU/experiments/iteration13_sih26073_v1/reports')
OUT.mkdir(parents=True,exist_ok=True)
TIMESTAMP_TIMEZONE_CONFIRMED=False  # change only after authoritative IMD confirmation
print('Code commit:',CODE_COMMIT,'| data exists:',DATA.exists())""")
    for number,title,body in [
      (2,'Genuine-data verification','Requires exclusively `IMD_AUTHORIZED_AWS_API`, source hashes and no generated rows.'),
      (3,'Integrity verification','Dataset SHA-256 and source snapshot hashes are recorded.'),
      (4,'Dataset readiness','Requires 50 stations with 30 distinct days and confirmed timestamp timezone.'),
      (5,'Station/time split','Station holdouts and chronological development splits occur before injection.'),
      (6,'Controlled fault injection','Nine fault signatures × subtle/moderate/severe; independent partition seeds.'),
      (7,'Feature engineering','Past-only rolling robust, frozen, drift and exact-time spatial features.'),
      (8,'Baselines','Range QC, Hampel-style, Isolation Forest and HistGradientBoosting.'),
      (9,'Hybrid challenger','QC + temporal + multivariate proxy + frozen + drift + spatial event gate.'),
      (10,'Calibration','Sigmoid calibrator fits validation scores only; Brier score is saved.'),
      (11,'Fault classification','Cautious signature labels permit `ROOT_CAUSE_UNCERTAIN`.'),
      (12,'Event safeguard evaluation','Coherent neighbours reduce isolated-sensor probability but do not prove a named weather event.'),
      (13,'Temporal generalization','Final development test contains future timestamps only.'),
      (14,'Station generalization','Unseen stations contribute no training rows.'),
      (15,'Fault severity evaluation','Recall is separated for subtle, moderate and severe injections.'),
      (16,'Sensor health evaluation','Transparent 0–100 score; no remaining-life claim.'),
      (17,'Correction evaluation','Existing safe correction must be scored against untouched originals.'),
      (18,'Streaming latency benchmark','Must be sequential and causal; no full-future batch claim.'),
      (19,'Scalability benchmark','Infrastructure replication must be labelled synthetic workload scaling.'),
      (20,'Explainability examples','Reason codes are generated from actual triggers; SHAP requires a fitted compatible model.'),
      (21,'SIH scorecard','Evidence-backed status, weaknesses and confidence only.'),
      (22,'Final scientific conclusion','No promotion unless predefined gate and same-benchmark Phase 10 comparison pass.')]:
        md(f'{number}. {title}',body)
    code("""if not DATA.exists():
    (OUT/'BLOCKED.txt').write_text('NOT ENOUGH GENUINE TEMPORAL DATA FOR THIS EXPERIMENT',encoding='utf-8')
    return_code=2
else:
    command=[sys.executable,str(REPO/'tools/run_iteration13_benchmark.py'),'--data',str(DATA),'--out',str(OUT)]
    if TIMESTAMP_TIMEZONE_CONFIRMED: command.append('--timezone-confirmed')
    return_code=subprocess.run(command,cwd=REPO).returncode
print('Benchmark return code:',return_code,'(0=completed, 2=scientifically blocked)')""")
    md('23. Export report ZIP','The ZIP contains only reports/configuration—never credentials or raw observations.')
    code("""zip_path=OUT.parent/'SkyGuard_Iteration13_SIH26073_Scientific_Validation_Reports.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(OUT.rglob('*')):
        if path.is_file(): archive.write(path,path.relative_to(OUT.parent))
print('Return this file:',zip_path)
from google.colab import files
files.download(str(zip_path))
if return_code != 0: print('Safe stop retained: collect more genuine IMD history; no model was promoted.')""")
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.x'}},'nbformat':4,'nbformat_minor':5}
    for folder in (ROOT/'notebooks',ROOT/'deliverables'):
        folder.mkdir(exist_ok=True); (folder/NAME).write_text(json.dumps(nb,indent=1),encoding='utf-8')
    return ROOT/'notebooks'/NAME

if __name__=='__main__': print(build())
