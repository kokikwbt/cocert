"""Known-total symbolic TV feasibility using the Eris OSQP execution path."""

from fractions import Fraction as F
import time
import numpy as np
from scipy import sparse
import osqp
from cocert.baselines.recent.tv_query_common import fractions,recover_allocation,thresholds,tv


def compile_linear(query,total,epsilon):
    a,b,c=fractions(query);s=F(total);mass=sum(b);scale=max(F(1),mass)
    if not 0<=s<=mass:raise ValueError('Infeasible split total')
    active=[j for j,v in enumerate(b) if v];m=len(active);k=len(a);n=k*m
    ep=thresholds(epsilon,k)
    if s in {0,mass} or m<=1:
        x=[F(0)]*len(b)
        if s==mass:x=b
        elif m:x[active[0]]=s
        changed=any(tv(aa,b,cc,x)>e for aa,cc,e in zip(a,c,ep))
        return {'constant':True,'status':'positive' if changed else 'negative','allocation':list(map(str,x))}
    rows=[];rhs=[]
    positive=[];negative=[];prhs=[];nrhs=[];tvrows=[];trhs=[]
    fixed=[j for j in range(len(b)) if not b[j]]
    for i,(aa,cc,e) in enumerate(zip(a,c,ep)):
        left,right=sum(aa)+s,sum(cc)+mass-s;h=scale*(1/left+1/right)
        constant=[u/left-(v+w)/right for u,v,w in zip(aa,cc,b)]
        fixed_tv=sum((abs(constant[j]) for j in fixed),F(0))/2
        if fixed_tv>e:
            return {'constant':True,'status':'positive','constant_margin':str(fixed_tv-e)}
        for j,original in enumerate(active):
            z=m+i*m+j
            positive.append({j:h,z:F(-1)});prhs.append(-constant[original])
            negative.append({j:-h,z:F(-1)});nrhs.append(constant[original])
        tvrows.append({m+i*m+j:F(1,2) for j in range(m)});trhs.append(e-fixed_tv)
    rows=positive+negative+tvrows;rhs=prhs+nrhs+trhs;width=m+n
    rr=[];cols=[];values=[]
    for i,row in enumerate(rows):
        for j,value in row.items():rr.append(i);cols.append(j);values.append(float(value))
    matrix=sparse.csc_matrix((values,(rr,cols)),shape=(len(rows),width))
    eq=sparse.csc_matrix((np.ones(m),(np.zeros(m,int),np.arange(m))),shape=(1,width))
    upper=[b[j]/scale for j in active]+[F(1)]*n
    return {'constant':False,'matrix':matrix,'eq':eq,'rows':rows,'rhs':rhs,'upper':upper,
            's':s/scale,'scale':scale,'active':active}


def infeasibility_margin(model,certificate):
    count=len(model['rows']);m=len(model['active'])
    y=[F(float(v)).limit_denominator(10**6) for v in certificate]
    weights=[max(F(0),v) for v in y[:count]];eq=y[count]
    residual=[eq]*m+[F(0)]*(len(model['upper'])-m)
    base=-eq*model['s']-sum((w*v for w,v in zip(weights,model['rhs'])),F(0))
    for w,row in zip(weights,model['rows']):
        for j,value in row.items():residual[j]+=w*value
    return base+sum((min(F(0),v)*upper for v,upper in zip(residual,model['upper'])),F(0))


def decide(query,epsilon,total=None,*,eps_abs=1e-5,eps_rel=1e-5,max_iter=10000):
    if total is None:return {'status':'not_applicable','reason':'Unknown normalization is outside the linear query model'}
    started=time.perf_counter()
    model=compile_linear(query,total,epsilon)
    if model['constant']:
        return {**model,'raw_status':'constant_query','solver_seconds':time.perf_counter()-started,
                'check_seconds':0.,'iterations':0}
    matrix=model['matrix'];rhs=np.array(model['rhs'],float);s=float(model['s']);width=len(model['upper'])
    allmat=sparse.vstack([matrix,model['eq'],sparse.eye(width)],format='csc')
    lo=np.r_[np.full(len(rhs),-np.inf),s,np.zeros(width)]
    hi=np.r_[rhs,s,np.array(model['upper'],float)]
    solver=osqp.OSQP()
    solver.setup(P=sparse.csc_matrix((width,width)),q=np.zeros(width),A=allmat,l=lo,u=hi,
                 verbose=False,eps_abs=eps_abs,eps_rel=eps_rel,max_iter=max_iter)
    result=solver.solve();solved=time.perf_counter();status=result.info.status
    answer={'raw_status':status,'status':'undecided','iterations':int(result.info.iter),
            'solver_seconds':solved-started,'check_seconds':0.}
    if 'primal infeasible' in status:
        margin=infeasibility_margin(model,result.prim_inf_cert)
        if margin>0:answer.update(status='positive',margin=str(margin))
    elif status in {'solved','solved inaccurate'}:
        values=np.zeros(len(query['B']))
        values[model['active']]=result.x[:len(model['active'])]*float(model['scale'])
        x=recover_allocation(query,values,total)
        a,b,c=fractions(query);ep=thresholds(epsilon,len(a))
        if all(tv(ai,b,ci,x)<=e for ai,ci,e in zip(a,c,ep)):
            answer.update(status='negative',allocation=list(map(str,x)))
    answer['check_seconds']=time.perf_counter()-solved
    return answer
