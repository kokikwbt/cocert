"""Minimum TV over the cores of archive-induced lower probabilities."""

from fractions import Fraction as F
from functools import lru_cache
import time
import networkx as nx
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from cocert.baselines.recent.tv_query_common import fractions


@lru_cache(maxsize=12)
def events(m):
    return ((np.arange(1<<m)[:,None]>>np.arange(m))&1).astype(float)


def lower_event(a,b,selected,total=None):
    mass=sum(a[j] for j in selected);boundary=sum(b[j] for j in selected)
    if total is None:
        return mass/(sum(a)+sum(b)-boundary)
    return (mass+max(F(0),F(total)-sum(b)+boundary))/(sum(a)+F(total))


def event_bound(a,b,c,total=None):
    m=len(b);av,bv,cv=map(lambda v:np.array(v,float),(a,b,c))
    varying=[j for j in range(m) if b[j]>0]
    fixed=[j for j in range(m) if b[j]==0]
    e=events(len(varying));sa,sb,sc=e@av[varying],e@bv[varying],e@cv[varying]
    if total is None:
        left,right=av.sum()+bv.sum()-sb,cv.sum()+sb
        value=sa/left+(cv.sum()-sc)/right-1
        for j in fixed:value+=np.maximum(0,av[j]/left-cv[j]/right)
    else:
        s=float(F(total));t=bv.sum()-s
        value=(sa+np.maximum(0,s-bv.sum()+sb))/(av.sum()+s)
        value+=(cv.sum()-sc+np.maximum(0,t-sb))/(cv.sum()+t)-1
    mask=int(np.argmax(value));selected=[j for h,j in enumerate(varying) if mask>>h&1]
    if total is None:
        selected.extend(j for j in fixed if av[j]/left[mask]-cv[j]/right[mask]>0)
    elif fixed:
        # Fixed-total callers use the normalized-band identity instead.
        raise ValueError('Use the fixed-total band formula when zero-boundary bins remain')
    other=[j for j in range(m) if j not in selected]
    rtotal=None if total is None else sum(b)-F(total)
    bound=lower_event(a,b,selected,total)+lower_event(c,b,other,rtotal)-1
    return max(F(0),bound),selected


def separate_core(p,a,b):
    """Minimize the quadratic submodular form for a violated core constraint."""
    m=len(b);a=np.array(a,float);b=np.array(b,float);p=np.maximum(p,0)
    pair=(b[:,None]*p[None,:]+p[:,None]*b[None,:])/2
    np.fill_diagonal(pair,0)
    unary=(a.sum()+b.sum())*p-a-b*p-pair.sum(axis=1)
    graph=nx.DiGraph();source=m;sink=m+1
    graph.add_nodes_from(range(m+2))
    for j,v in enumerate(unary):
        if v>=0:graph.add_edge(j,sink,capacity=float(v))
        else:graph.add_edge(source,j,capacity=float(-v))
    for i in range(m):
        for j in range(i):
            if pair[i,j]>0:
                graph.add_edge(i,j,capacity=float(pair[i,j]))
                graph.add_edge(j,i,capacity=float(pair[i,j]))
    _,partition=nx.minimum_cut(graph,source,sink)
    return frozenset(j for j in partition[0] if j<m)


def core_lp(a,b,c,total=None,max_cuts=96,time_limit=1.):
    """Solve the published core-distance LP; add valid event constraints."""
    started=time.perf_counter();m=len(b)
    rows=[];rhs=[];exact=[];seen=set()
    rtotal=None if total is None else sum(b)-F(total)
    def add(side,selected):
        selected=frozenset(selected);key=(side,selected)
        if key in seen:return
        seen.add(key)
        row={side*m+j:F(-1) for j in selected}
        bound=-lower_event(a if side==0 else c,b,selected,total if side==0 else rtotal)
        rows.append(row);exact.append(bound);rhs.append(float(bound))
    for side in range(2):
        for j in range(m):
            add(side,[j]);add(side,[h for h in range(m) if h!=j])
    for j in range(m):
        rows.extend([{j:F(1),m+j:F(-1),2*m+j:F(-1)},
                     {j:F(-1),m+j:F(1),2*m+j:F(-1)}])
        exact.extend([F(0),F(0)]);rhs.extend([0.,0.])
    eq=sparse.csc_matrix((np.ones(2*m),(np.repeat([0,1],m),np.arange(2*m))),shape=(2,3*m))
    obj=np.r_[np.zeros(2*m),np.full(m,.5)]
    last=None;complete=False
    for iteration in range(max_cuts+1):
        remaining=time_limit-(time.perf_counter()-started)
        if remaining<=0:break
        rr=[];cc=[];vv=[]
        for i,row in enumerate(rows):
            for j,v in row.items():rr.append(i);cc.append(j);vv.append(float(v))
        matrix=sparse.csc_matrix((vv,(rr,cc)),shape=(len(rows),3*m))
        solved=linprog(obj,A_ub=matrix,b_ub=rhs,A_eq=eq,b_eq=[1,1],bounds=(0,1),
            method='highs',options={'time_limit':remaining,'primal_feasibility_tolerance':1e-9,
            'dual_feasibility_tolerance':1e-9})
        if not solved.success:break
        last=(solved,list(rows),list(exact))
        if total is not None:complete=True;break
        added=False
        for side,aa in [(0,a),(1,c)]:
            point=solved.x[side*m:(side+1)*m]
            selected=separate_core(point,aa,b)
            gap=float(lower_event(aa,b,selected))-sum(point[j] for j in selected)
            if gap>1e-8 and (side,selected) not in seen:
                add(side,selected);added=True
        if not added:complete=True;break
    if last is None:return F(0),False,iteration
    solved,used_rows,used_rhs=last
    dual=[min(F(0),F(float(v)).limit_denominator(10**6)) for v in solved.ineqlin.marginals]
    eqdual=[F(float(v)).limit_denominator(10**6) for v in solved.eqlin.marginals]
    residual=[-eqdual[0]]*m+[-eqdual[1]]*m+[F(1,2)]*m
    lower=sum(eqdual)+sum((y*v for y,v in zip(dual,used_rhs)),F(0))
    for y,row in zip(dual,used_rows):
        for j,v in row.items():residual[j]-=y*v
    lower+=sum((min(F(0),r) for r in residual),F(0))
    return max(F(0),lower),complete,iteration


def bounds(query,total=None,max_cuts=96,time_limit=1.):
    a,b,c=fractions(query)
    active=[j for j in range(len(b)) if b[j] or any(row[j] for row in a+c)]
    a=[[row[j] for j in active] for row in a];c=[[row[j] for j in active] for row in c];b=[b[j] for j in active]
    results=[];complete=[];iterations=[]
    for left,right in zip(a,c):
        if total is not None:
            from cocert.baselines.recent.density_bands.model import bands,lower_bounds
            value=lower_bounds(*bands(left,b,right,total))[1];done=True;it=0
        elif sum(v>0 for v in b)<=16:
            value,_=event_bound(left,b,right,total);done=True;it=0
        else:
            value,done,it=core_lp(left,b,right,total,max_cuts,time_limit/len(a))
        results.append(str(value));complete.append(done);iterations.append(it)
    return {'bounds':results,'complete':all(complete),'iterations':iterations,'effective_bins':len(b)}
