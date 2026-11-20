"""Author-example median bandwidth with outward-rational kernel bounds."""

from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
from fractions import Fraction as F
from functools import lru_cache
import numpy as np
from .model import bound as fixed_bound,eligible
from cocert.baselines.recent.tv_query_common import fractions,thresholds


def median_distance(a,c):
    weights=[int(x)+int(y) for x,y in zip(a,c)];n=sum(weights)
    count=n*(n-1)//2
    if count==0:return F(0)
    hist=[sum(w*(w-1)//2 for w in weights)]
    hist.extend(sum(weights[j]*weights[j+d] for j in range(len(weights)-d)) for d in range(1,len(weights)))
    targets=[(count-1)//2,count//2];values=[];acc=0
    for d,mass in enumerate(hist):
        for t in targets:
            if acc<=t<acc+mass:values.append(d)
        acc+=mass
    return F(sum(values),2)


@lru_cache(maxsize=128)
def matrices(m,median,exact=False):
    if not exact:
        value=np.exp(-np.abs(np.arange(m)[:,None]-np.arange(m)[None,:]).astype(float)/float(median))
        return value,value
    lower=[];upper=[];scale=2**64
    with localcontext() as context:
        context.prec=80
        for distance in range(m):
            if distance==0:lower.append(F(1));upper.append(F(1));continue
            context.rounding=ROUND_FLOOR
            arglo=context.divide(Decimal(-distance*median.denominator),Decimal(median.numerator))
            context.rounding=ROUND_CEILING
            arghi=context.divide(Decimal(-distance*median.denominator),Decimal(median.numerator))
            lower_exp=arglo.exp().next_minus();upper_exp=arghi.exp().next_plus()
            context.rounding=ROUND_FLOOR
            lo=int((lower_exp*scale).to_integral_value(rounding=ROUND_FLOOR))
            context.rounding=ROUND_CEILING
            hi=int((upper_exp*scale).to_integral_value(rounding=ROUND_CEILING))
            lower.append(F(max(0,lo),scale));upper.append(F(min(scale,hi),scale))
    index=np.abs(np.arange(m)[:,None]-np.arange(m)[None,:])
    return np.array(lower,dtype=object)[index],np.array(upper,dtype=object)[index]


def bound(a,c,r,s,*,exact=False,upper=False):
    median=median_distance(a,c)
    if median==0:return fixed_bound(a,c,r,s,exact=exact,upper=upper),median
    lo,hi=matrices(len(a),median,exact)
    if exact:
        active=[j for j in range(len(a)) if a[j]+c[j]>0]
        lo=lo[np.ix_(active,active)];hi=hi[np.ix_(active,active)]
        a=[a[j] for j in active];c=[c[j] for j in active]
    a=np.array(list(map(F,a)) if exact else a,dtype=object if exact else float)
    c=np.array(list(map(F,c)) if exact else c,dtype=object if exact else float)
    n=sum(a)+r;m=sum(c)+s
    c1=2/(n*(n-1));c2=2/(m*(m-1));c3=2/(n*m)
    aa=(hi if upper else lo)@a;cc=(hi if upper else lo)@c
    cross=(lo if upper else hi)@c
    observed=c1*(sum(a*aa)-sum(a))/2+c2*(sum(c*cc)-sum(c))/2-c3*sum(a*cross)
    choose=max if upper else min
    active=[j for j in range(len(a)) if a[j]+c[j]>0]
    left=c1*aa-c3*((lo if upper else hi)@c)
    right=c2*cc-c3*((lo if upper else hi)@a)
    unknown=c1*r*(r-1)/2+c2*s*(s-1)/2 if upper else -c3*r*s
    value=observed+unknown+r*choose([0]+[left[j] for j in active])+s*choose([0]+[right[j] for j in active])
    return value,median


def decide(query,epsilon,total=None,*,domain='real',max_count=100):
    ok,reason=eligible(query,total)
    if not ok:return {'status':'not_applicable','reason':reason}
    a,b,c=fractions(query);a=[[int(v) for v in row] for row in a];c=[[int(v) for v in row] for row in c]
    mass=int(sum(b));ep=thresholds(epsilon,len(a))
    if total is None:
        if domain!='integer':return {'status':'not_applicable','reason':'Unknown real split count'}
        if mass>max_count:return {'status':'undecided','reason':'Count enumeration budget'}
        totals=range(mass+1)
    else:totals=[int(F(total))]
    selected=[];raw=[]
    medians=[str(median_distance(aa,cc)) for aa,cc in zip(a,c)]
    for s in totals:
        if any(min(sum(aa)+s,sum(cc)+mass-s)<2 for aa,cc in zip(a,c)):
            return {'status':'not_applicable','reason':'Completed sample size below two'}
        values=[float(bound(aa,cc,s,mass-s)[0])-4*float(e)**2 for aa,cc,e in zip(a,c,ep)]
        k=int(np.argmax(values));raw.append(values[k]);selected.append((s,k))
    if min(raw)<=1e-10:return {'status':'not_certified','medians':medians,'zero_median_fallback':medians.count('0')}
    margin=min(bound(a[k],c[k],s,mass-s,exact=True)[0]-4*ep[k]**2 for s,k in selected)
    return {'status':'positive' if margin>0 else 'not_certified','margin':str(margin),
            'medians':medians,'zero_median_fallback':medians.count('0')}
