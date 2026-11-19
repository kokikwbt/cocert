"""Retained-count parsing and generic linear TV models."""

from fractions import Fraction as F
import numpy as np
from scipy import sparse
from scipy.optimize import linprog


def fractions(query):
    a = [[F(v) for v in row] for row in query['A']]
    b = list(map(F, query['B']))
    c = [[F(v) for v in row] for row in query['C']]
    if not b or len(a) != len(c) or not a:
        raise ValueError('Nonempty common-bin windows required')
    if min(b) < 0 or any(len(row) != len(b) or min(row) < 0 or sum(row) <= 0 for row in a+c):
        raise ValueError('Nonnegative counts and positive cores required')
    return a, b, c


def numeric(query):
    a,b,c = fractions(query)
    return tuple(np.array(v, float) for v in (a,b,c))


def thresholds(epsilon, k):
    values = list(epsilon) if isinstance(epsilon, (list,tuple)) else [epsilon]*k
    if len(values) != k or min(map(F, values)) < 0:
        raise ValueError('One nonnegative threshold per window required')
    return list(map(F, values))


def tv(a,b,c,x):
    left,right = sum(a)+sum(x),sum(c)+sum(b)-sum(x)
    return sum((abs((u+v)/left-(w+t-v)/right)
                for u,t,w,v in zip(a,b,c,x)),F(0))/2


def recover_allocation(query, values, total=None, denominator=10**7):
    """Recover a rational witness in an external, explicitly timed check layer."""
    a,b,c=fractions(query)
    x=[min(v,max(F(0),F(float(w)).limit_denominator(denominator))) for v,w in zip(b,values)]
    if total is not None:
        delta=F(total)-sum(x)
        for j in range(len(b)):
            change=min(delta,b[j]-x[j]) if delta>=0 else max(delta,-x[j])
            x[j]+=change;delta-=change
        if delta: raise ValueError('Infeasible split total')
    return x


def fixed_model(query, total, epsilon=0, *, feasibility=False):
    _,exact_b,_=fractions(query)
    if not 0<=F(total)<=sum(exact_b):raise ValueError('Infeasible split total')
    a,b,c=numeric(query); k,m=a.shape;n=k*m
    scale=max(1.,b.sum());s=float(F(total))/scale
    a,b,c=a/scale,b/scale,c/scale
    s=float(np.clip(s,0,b.sum()))
    ep=np.array(thresholds(epsilon,k),float)
    left,right=a.sum(1)+s,c.sum(1)+b.sum()-s
    constant=a/left[:,None]-(c+b)/right[:,None]
    coefficient=1/left+1/right
    kk=np.repeat(np.arange(k),m);jj=np.tile(np.arange(m),k);z=np.arange(n)
    rows=np.r_[z,z,n+z,n+z,2*n+kk]
    cols=np.r_[jj,m+z,jj,m+z,m+z]
    data=np.r_[coefficient[kk],-np.ones(n),-coefficient[kk],-np.ones(n),np.full(n,.5)]
    width=m+n+(not feasibility)
    if not feasibility:
        rows=np.r_[rows,2*n+np.arange(k)]
        cols=np.r_[cols,np.full(k,m+n)]
        data=np.r_[data,-np.ones(k)]
    matrix=sparse.csc_matrix((data,(rows,cols)),shape=(2*n+k,width))
    rhs=np.r_[-constant.ravel(),constant.ravel(),ep]
    eq=sparse.csc_matrix((np.ones(m),(np.zeros(m,int),np.arange(m))),shape=(1,width))
    delta_lower=min(-1.,-float(ep.max()))
    bounds=[(0,float(v)) for v in b]+[(0,1.)]*n+([] if feasibility else [(delta_lower,1.)])
    objective=np.zeros(width)
    if not feasibility: objective[-1]=1
    return matrix,rhs,eq,s,bounds,objective,scale


def fixed_lower(query,total,epsilon,result,denominator=10**6):
    """Check a generic LP dual by exact Lagrangian minimization on a box."""
    a,b,c=fractions(query);k=len(a);m=len(b);n=k*m
    scale=max(F(1),sum(b));s=F(total)
    ep=thresholds(epsilon,k)
    w=[max(F(0),F(float(-v)).limit_denominator(denominator)) for v in result.ineqlin.marginals]
    eq=F(float(result.eqlin.marginals[0])).limit_denominator(denominator)
    r=[-eq]*m+[F(0)]*n+[F(1)]
    base=eq*s/scale
    for i in range(k):
        left,right=sum(a[i])+s,sum(c[i])+sum(b)-s
        h=scale*(1/left+1/right)
        for j in range(m):
            z=i*m+j;u,v=w[z],w[n+z]
            d=a[i][j]/left-(c[i][j]+b[j])/right
            base+=(u-v)*d
            r[j]+=(u-v)*h
            r[m+z]-=u+v
            r[m+z]+=w[2*n+i]/2
        base-=w[2*n+i]*ep[i]
        r[-1]-=w[2*n+i]
    upper=[v/scale for v in b]+[F(1)]*n
    delta_lower=min(F(-1),-max(ep))
    return base+sum((min(F(0),v)*u for v,u in zip(r,upper)),F(0))+min(delta_lower*r[-1],r[-1])


def solve_fixed(query,total,epsilon=0,time_limit=1.):
    matrix,rhs,eq,s,bounds,obj,scale=fixed_model(query,total,epsilon)
    result=linprog(obj,A_ub=matrix,b_ub=rhs,A_eq=eq,b_eq=[s],bounds=bounds,
                   method='highs',options={'time_limit':time_limit,
                   'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    if not result.success:
        return {'status':'undecided','solver_status':result.message}
    x=recover_allocation(query,result.x[:len(query['B'])]*scale,total)
    a,b,c=fractions(query);ep=thresholds(epsilon,len(a))
    upper=max(tv(ai,b,ci,x)-e for ai,ci,e in zip(a,c,ep))
    lower=fixed_lower(query,total,epsilon,result)
    assert lower<=upper
    return {'lower':str(lower),'upper':str(upper),'allocation':list(map(str,x)),
            'status':'positive' if lower>0 else 'negative' if upper<=0 else 'undecided',
            'raw_value':float(result.fun),'iterations':int(result.nit)}
