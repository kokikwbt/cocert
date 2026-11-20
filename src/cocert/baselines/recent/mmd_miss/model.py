"""Count-compressed univariate MMD-Miss with the fixed Laplacian beta log(2)."""

from fractions import Fraction as F
from functools import lru_cache
import numpy as np
from cocert.baselines.recent.tv_query_common import fractions,thresholds


@lru_cache(maxsize=16)
def kernel(m):
    return np.exp2(-np.abs(np.arange(m)[:,None]-np.arange(m)[None,:]).astype(float))


def bound(a,c,missing_left,missing_right,*,upper=False,exact=False):
    m=len(a);na=sum(a);nc=sum(c);n=na+missing_left;t=nc+missing_right
    if min(n,t)<2:raise ValueError('At least two observations in each completed sample required')
    if exact:
        positions=[j for j in range(m) if a[j]+c[j]>0]
        a=[F(a[j]) for j in positions];c=[F(c[j]) for j in positions];n=F(n);t=F(t)
        mat=[[F(1,2**abs(i-j)) for j in positions] for i in positions]
        ka=[sum((v*w for v,w in zip(row,a)),F(0)) for row in mat]
        kc=[sum((v*w for v,w in zip(row,c)),F(0)) for row in mat]
        m=len(positions)
    else:
        a=np.array(a,float);c=np.array(c,float);mat=kernel(m);ka=mat@a;kc=mat@c
    c1=2/(n*(n-1));c2=2/(t*(t-1));c3=2/(n*t)
    within_a=(sum(v*w for v,w in zip(a,ka))-sum(a))/2
    within_c=(sum(v*w for v,w in zip(c,kc))-sum(c))/2
    observed=c1*within_a+c2*within_c-c3*sum(v*w for v,w in zip(a,kc))
    active=[i for i in range(m) if a[i]+c[i]>0]
    left=[c1*ka[i]-c3*kc[i] for i in active]
    right=[c2*kc[i]-c3*ka[i] for i in active]
    choose=max if upper else min
    unknown=(c1*missing_left*(missing_left-1)/2+c2*missing_right*(missing_right-1)/2
             if upper else -c3*missing_left*missing_right)
    return observed+unknown+missing_left*choose([0]+left)+missing_right*choose([0]+right)


def eligible(query,total):
    a,b,c=fractions(query)
    if any(v.denominator!=1 for row in a+c+[b] for v in row):return False,'Integer observations required'
    if total is not None and F(total).denominator!=1:return False,'Integer split count required'
    return True,''


def decide(query,epsilon,total=None,*,domain='real',max_count=100):
    ok,reason=eligible(query,total)
    if not ok:return {'status':'not_applicable','reason':reason}
    a,b,c=fractions(query);a=[[int(v) for v in row] for row in a];c=[[int(v) for v in row] for row in c]
    mass=int(sum(b));ep=thresholds(epsilon,len(a))
    if total is None:
        if domain!='integer':return {'status':'not_applicable','reason':'Unknown real split count is outside fixed-size testing'}
        if mass>max_count:return {'status':'undecided','reason':'Count enumeration budget'}
        totals=range(mass+1)
    else:totals=[int(F(total))]
    candidate=[];numeric_lower=[]
    for s in totals:
        if any(min(sum(aa)+s,sum(cc)+mass-s)<2 for aa,cc in zip(a,c)):
            return {'status':'not_applicable','reason':'Completed sample size below two'}
        residual=[bound(aa,cc,s,mass-s)-4*float(e)**2 for aa,cc,e in zip(a,c,ep)]
        k=int(np.argmax(residual));candidate.append((s,k));numeric_lower.append(residual[k])
    worst=min(numeric_lower)
    if worst<=1e-10:
        return {'status':'not_certified','raw_margin':float(worst),'sizes_checked':len(candidate)}
    exact=[bound(a[k],c[k],s,mass-s,exact=True)-4*ep[k]**2 for s,k in candidate]
    margin=min(exact)
    return {'status':'positive' if margin>0 else 'not_certified','margin':str(margin),
            'sizes_checked':len(candidate),'raw_margin':float(worst)}


def permutation(query,total,*,permutations=199,alpha=0.05,seed=0):
    ok,reason=eligible(query,total)
    if not ok or total is None:return {'status':'not_applicable','reason':reason}
    a,b,c=fractions(query);mass=int(sum(b));s=int(F(total));rng=np.random.default_rng(seed)
    pvalues=[];stats=[]
    for aa,cc in zip(a,c):
        aa=np.array(aa,dtype=np.int64);cc=np.array(cc,dtype=np.int64)
        n=int(aa.sum())+s;t=int(cc.sum())+mass-s
        if min(n,t)<2:return {'status':'not_applicable','reason':'Completed sample size below two'}
        statistic=float(bound(aa,cc,s,mass-s));pooled=np.r_[aa+cc,mass]
        exceed=0
        for _ in range(permutations):
            first=rng.multivariate_hypergeometric(pooled,n,method='marginals');second=pooled-first
            upper=bound(first[:-1],second[:-1],int(first[-1]),int(second[-1]),upper=True)
            exceed+=upper>=statistic
        pvalues.append((exceed+1)/(permutations+1));stats.append(statistic)
    return {'status':'rejected' if min(pvalues)<=alpha/len(a) else 'not_rejected',
            'pvalues':pvalues,'statistics':stats,'family_alpha':alpha,
            'permutations':permutations,'seed':seed}
