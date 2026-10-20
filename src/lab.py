"""Executable contracts, row-level violation maps and baseline distribution drift."""
import json, math
from collections import Counter
from common import *
NULL={'','null','none','n/a'}
def present(v):return v.strip().lower() not in NULL

def profile(headers,rows):
    output=[]
    for c in headers:
        vals=[r[c] for r in rows if present(r[c])];nums=[number(v) for v in vals];numeric=bool(vals) and all(v is not None and abs(v)<10**100 for v in nums)
        fs=[float(v) for v in nums] if numeric else []
        output.append({'column':c,'type':'number' if numeric else 'text','nulls':len(rows)-len(vals),'distinct':len(set(vals)),'min':min(fs) if fs else None,'max':max(fs) if fs else None,'mean':sum(fs)/len(fs) if fs else None,'top':Counter(vals).most_common(8)})
    return output

def bins(values,low,high,n=10):
    out=[0]*n
    for v in values:out[min(n-1,max(0,int((v-low)/(high-low)*n))) if high>low else 0]+=1
    return out

def run(p):
    h,rows=read_csv(p.get('csv',''));profiles=profile(h,rows)
    try:rules=json.loads(p.get('rules','[]'))
    except (ValueError,TypeError):raise ValueError('Contracts must be a JSON array.')
    if not isinstance(rules,list) or len(rules)>60:raise ValueError('Use at most 60 contract rules.')
    checks=[];violations=[];flags={};accepted={'not_null','unique','range','allowed','numeric'}
    for idx,r in enumerate(rules):
        if not isinstance(r,dict) or r.get('column') not in h or r.get('type') not in accepted:raise ValueError('Each contract needs a known column and a type: not_null, unique, range, allowed, numeric.')
        c=r['column'];kind=r['type'];counts=Counter(row[c] for row in rows if present(row[c]));bad=[]
        if kind=='range':
            lo=number(r.get('min'));hi=number(r.get('max'))
            if lo is None or hi is None or lo>hi:raise ValueError('Range rules require finite min ≤ max.')
        if kind=='allowed' and (not isinstance(r.get('values'),list) or len(r['values'])>100):raise ValueError('Allowed rules require a values array with at most 100 entries.')
        for i,row in enumerate(rows):
            value=row[c];n=number(value)
            fail=(not present(value)) if kind=='not_null' else (present(value) and counts[value]>1) if kind=='unique' else (n is None or not lo<=n<=hi) if kind=='range' else value not in r['values'] if kind=='allowed' else n is None
            if fail:bad.append(i+2);flags.setdefault((i,c),[]).append(kind)
        checks.append({'id':idx+1,'column':c,'type':kind,'failed':len(bad),'passed':not bad,'rows':bad[:100],'rule':r})
        violations.extend([{'row':i,'column':c,'rule':kind} for i in bad])
    drift=[];baseline=p.get('baseline','')
    if baseline.strip():
        bh,br=read_csv(baseline);bp={x['column']:x for x in profile(bh,br)}
        for pro in profiles:
            c=pro['column'];old=bp.get(c)
            if old is None:drift.append({'column':c,'status':'new column','psi':None,'bins':[]});continue
            a=[r[c] for r in br if present(r[c])];b=[r[c] for r in rows if present(r[c])]
            if pro['type']=='number' and old['type']=='number' and a and b:
                aa=list(map(float,a));bb=list(map(float,b));low=min(aa+bb);high=max(aa+bb);av=bins(aa,low,high);bv=bins(bb,low,high);labels=[f'{low+(high-low)*i/10:.2g}' for i in range(10)]
            else:
                cats=[v for v,_ in Counter(a+b).most_common(9)];ac=Counter(a);bc=Counter(b);av=[ac[x] for x in cats]+[sum(v for k,v in ac.items() if k not in cats)];bv=[bc[x] for x in cats]+[sum(v for k,v in bc.items() if k not in cats)];labels=cats+['Other']
            # Additive smoothing produces normalized proportions, including empty populations.
            ap=[(v+0.5)/(sum(av)+len(av)*0.5) for v in av];bpp=[(v+0.5)/(sum(bv)+len(bv)*0.5) for v in bv]
            psi=sum((v-u)*math.log(v/u) for u,v in zip(ap,bpp))
            drift.append({'column':c,'status':'type changed' if pro['type']!=old['type'] else 'distribution shifted' if psi>=.2 else 'stable','psi':round(psi,5),'null_delta':round(pro['nulls']/len(rows)-old['nulls']/len(br),4),'bins':[{'label':str(label),'baseline':round(x*100,2),'current':round(y*100,2)} for label,x,y in zip(labels,ap,bpp)]})
        for c in bh:
            if c not in h:drift.append({'column':c,'status':'removed column','psi':None,'bins':[]})
    score=round(100*sum(x['passed'] for x in checks)/len(checks),1) if checks else None
    matrix=[{'record':i+2,'cells':[{'column':c,'state':'violation' if (i,c) in flags else 'missing' if not present(row[c]) else 'valid','rules':flags.get((i,c),[])} for c in h[:30]]} for i,row in enumerate(rows[:80])]
    out=result('Contract and drift analysis complete',[metric('Records',len(rows)),metric('Contracts passed',f"{sum(x['passed'] for x in checks)}/{len(checks)}"),metric('Contract score',f'{score}%' if score is not None else 'No rules'),metric('Flagged cells',len(flags))],['Column','Type','Missing','Distinct','Mean'],[[x['column'],x['type'],x['nulls'],x['distinct'],round(x['mean'],3) if x['mean'] is not None else '—'] for x in profiles],[finding('info','Drift is a review signal','PSI uses shared bins with additive smoothing. The 0.2 review threshold is a configurable-design heuristic, not a statistical significance test; small samples are illustrative.')],artifacts=[{'name':'quality-contracts.json','content':json.dumps(rules,indent=2)},{'name':'violations.json','content':json.dumps(violations,indent=2)}])
    out['lab']={'profiles':profiles,'checks':checks,'matrix':matrix,'drift':drift,'columns':h,'score':score,'violations':violations,'record_count':len(rows)};return out
