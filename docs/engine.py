"""CSV profiling and explicit quality rules; dependency-free Python."""
from collections import Counter
from datetime import date
from statistics import median, quantiles
from common import *

def legacy_run(p):
    h,rows=read_csv(p.get('csv',''));nulls={'','null','none','n/a'}
    required=columns(p.get('required'),h);unique=columns(p.get('unique'),h)
    findings=[];profile=[];chart=[];missing_total=0
    for col in h:
        values=[r[col].strip() for r in rows];valid=[v for v in values if v.lower() not in nulls]
        missing=len(values)-len(valid);missing_total+=missing
        nums=[number(v) for v in valid];numeric=bool(valid) and all(n is not None for n in nums)
        kind='number' if numeric else 'text'
        if valid and all(v.lower() in {'true','false'} for v in valid):kind='boolean'
        elif valid and not numeric:
            try:
                for v in valid:date.fromisoformat(v)
                kind='date'
            except ValueError:pass
        repetitions=sum(c-1 for c in Counter(valid).values() if c>1)
        summary='—'
        if numeric:
            fs=[float(n) for n in nums]
            if not all(math.isfinite(n) for n in fs):raise ValueError(f'{col}: numeric magnitude is too large for charting.')
            summary=f'{min(fs):g} → {max(fs):g} (median {median(fs):g})'
            if len(fs)>=4:
                q1,_,q3=quantiles(fs,n=4,method='inclusive');iqr=q3-q1
                outliers=sum(v<q1-1.5*iqr or v>q3+1.5*iqr for v in fs)
                if outliers:findings.append(finding('info',f'{col}: {outliers} statistical outlier(s)','Tukey IQR flags are review candidates, not proven data errors.'))
        profile.append([col,kind,str(len(set(valid))),str(missing),f'{100*(len(values)-missing)/len(values):.1f}%',summary])
        chart.append({'label':col,'value':round(100*(len(values)-missing)/len(values),1)})
        if col in required and missing:findings.append(finding('error',f'{col}: {missing} required value(s) missing','Null tokens are blank, null, none, and n/a (case insensitive).'))
        if col in unique and repetitions:findings.append(finding('error',f'{col}: {repetitions} duplicate non-null value(s)','Uniqueness compares trimmed strings; 001 and 1 are distinct.'))
    duplicates=sum(n-1 for n in Counter(tuple(r[c] for c in h) for r in rows).values() if n>1)
    if duplicates:findings.append(finding('warning',f'{duplicates} exact duplicate row(s)','Review ingestion retries or deduplication policy.'))
    if not findings:findings.append(finding('success','No issues found by the selected checks','This does not establish semantic correctness. Add business-specific checks for your dataset.'))
    return result('Data profile complete',[metric('Rows',len(rows)),metric('Columns',len(h)),metric('Completeness',f'{100*(1-missing_total/(len(rows)*len(h))):.1f}%'),metric('Duplicate rows',duplicates)],['Column','Inferred type','Distinct values','Missing','Completeness','Numeric range'],profile,findings,chart)


def run(p):
    if not isinstance(p,dict):raise ValueError("Send a JSON object.")
    if p.get("workspace")=="studio":
        from lab import run as studio_run
        return studio_run(p)
    return legacy_run(p)
