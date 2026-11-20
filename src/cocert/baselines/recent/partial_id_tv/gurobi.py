"""Author-backend conditional LP grid with incremental model updates."""

from fractions import Fraction as F
from types import SimpleNamespace
import time
import numpy as np
import gurobipy as gp
from cocert.baselines.recent.tv_query_common import fixed_model,fixed_lower,fractions,recover_allocation,thresholds,tv

ENVIRONMENT=None


def environment():
    global ENVIRONMENT
    if ENVIRONMENT is None:
        ENVIRONMENT=gp.Env(empty=True);ENVIRONMENT.setParam('OutputFlag',0);ENVIRONMENT.start()
    return ENVIRONMENT


class ConditionalLP:
    def __init__(self,query,total,epsilon):
        self.query=query;self.epsilon=epsilon
        matrix,rhs,eq,s,bounds,obj,scale=fixed_model(query,total,epsilon)
        self.scale=scale;self.k=len(query['A']);self.m=len(query['B']);self.n=self.k*self.m
        self.model=gp.Model(env=environment())
        self.model.Params.Method=1;self.model.Params.Threads=1
        self.model.Params.FeasibilityTol=1e-9;self.model.Params.OptimalityTol=1e-9
        self.variables=self.model.addMVar(len(obj),lb=[v[0] for v in bounds],ub=[v[1] for v in bounds])
        self.constraints=self.model.addMConstr(matrix,self.variables,'<',rhs)
        self.equality=self.model.addMConstr(eq,self.variables,'=',[s])
        self.model.setObjective(obj @ self.variables,gp.GRB.MINIMIZE)
        self.model.update();self.rows=self.constraints.tolist();self.cols=self.variables.tolist()

    def solve(self,total,time_limit):
        started=time.perf_counter()
        matrix,rhs,eq,s,bounds,obj,scale=fixed_model(self.query,total,self.epsilon)
        for i in range(self.k):
            for j in range(self.m):
                row=i*self.m+j;value=float(matrix[row,j])
                self.model.chgCoeff(self.rows[row],self.cols[j],value)
                self.model.chgCoeff(self.rows[self.n+row],self.cols[j],-value)
        self.constraints.RHS=rhs;self.equality.RHS=[s]
        self.model.Params.TimeLimit=max(.001,time_limit)
        self.model.optimize();numeric=time.perf_counter()-started
        if self.model.Status!=gp.GRB.OPTIMAL:
            return {'status':'undecided','numeric_seconds':numeric,'verification_seconds':0.}
        proposal=SimpleNamespace(ineqlin=SimpleNamespace(marginals=self.constraints.Pi),
          eqlin=SimpleNamespace(marginals=self.equality.Pi))
        point=self.variables.X
        x=recover_allocation(self.query,point[:self.m]*scale,total)
        a,b,c=fractions(self.query);ep=thresholds(self.epsilon,len(a))
        upper=max(tv(aa,b,cc,x)-e for aa,cc,e in zip(a,c,ep))
        lower=fixed_lower(self.query,total,self.epsilon,proposal)
        assert lower<=upper
        return {'status':'positive' if lower>0 else 'negative' if upper<=0 else 'undecided',
          'lower':str(lower),'upper':str(upper),'allocation':list(map(str,x)),
          'numeric_seconds':numeric,'verification_seconds':time.perf_counter()-started-numeric}

    def close(self):
        self.model.dispose()


def decide(query,epsilon,total=None,*,points=129,time_limit=1.):
    started=time.perf_counter();a,b,c=fractions(query);mass=sum(b)
    if mass==0:total=F(0)
    grid=[F(total)] if total is not None else [mass*F(j,points-1) for j in range(points)]
    order=sorted(range(len(grid)),key=lambda j:(abs(2*j-len(grid)+1),j))
    try:engine=ConditionalLP(query,grid[order[0]],epsilon)
    except gp.GurobiError as error:return {'status':'not_applicable','reason':str(error)}
    values={};calls=0;numeric=0.;checking=0.
    try:
        for j in order:
            remaining=time_limit-(time.perf_counter()-started)
            if remaining<=0:break
            result=engine.solve(grid[j],remaining);calls+=1
            numeric+=result['numeric_seconds'];checking+=result['verification_seconds']
            if total is not None or result['status']=='negative':
                return dict(result,lp_calls=calls,completed=total is not None,
                            numeric_seconds=numeric,verification_seconds=checking,split_total=str(grid[j]))
            if 'lower' in result:values[j]=F(result['lower'])
        if len(values)!=len(grid):return {'status':'undecided','lp_calls':calls,'completed':False,
             'numeric_seconds':numeric,'verification_seconds':checking}
        lower=F(1)
        for j in range(points-1):
            lo,hi=grid[j],grid[j+1]
            lip=max(1/(sum(aa)+lo)+1/(sum(cc)+mass-hi) for aa,cc in zip(a,c))
            lower=min(lower,min(values[j],values[j+1])-lip*(hi-lo)/2)
        return {'status':'positive' if lower>0 else 'undecided','lower':str(lower),'lp_calls':calls,
                'completed':True,'numeric_seconds':numeric,'verification_seconds':checking}
    finally:engine.close()
