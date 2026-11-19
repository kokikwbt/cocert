"""Conditional LP grids for TV queries, following denominator discretization."""

from fractions import Fraction as F
import time
import numpy as np
from cocert.baselines.recent.tv_query_common import fractions,solve_fixed


def decide(query,epsilon,total=None,*,points=33,time_limit=1.):
    started=time.perf_counter()
    if total is not None:
        result=solve_fixed(query,total,epsilon,time_limit)
        return dict(result,lp_calls=1,completed=True,route='fixed_total_lp')
    if points<2:raise ValueError('At least two grid endpoints required')
    a,b,c=fractions(query);mass=sum(b)
    if mass==0:
        return dict(solve_fixed(query,0,epsilon,time_limit),lp_calls=1,completed=True,route='fixed_total_lp')
    grid=[mass*F(j,points-1) for j in range(points)]
    # A midpoint-first order returns a valid low-TV allocation without a full grid.
    order=sorted(range(points),key=lambda j:(abs(2*j-points+1),j))
    values={};calls=0
    for j in order:
        remaining=time_limit-(time.perf_counter()-started)
        if remaining<=0:break
        result=solve_fixed(query,grid[j],epsilon,remaining);calls+=1
        if result['status']=='negative':
            return dict(result,lp_calls=calls,completed=False,route='grid_witness',split_total=str(grid[j]))
        if 'lower' in result:values[j]=F(result['lower'])
    if len(values)!=points:
        return {'status':'undecided','lp_calls':calls,'completed':False,'route':'grid_budget'}
    lower=F(1)
    for j in range(points-1):
        lo,hi=grid[j],grid[j+1]
        lip=max(1/(sum(aa)+lo)+1/(sum(cc)+mass-hi) for aa,cc in zip(a,c))
        lower=min(lower,min(values[j],values[j+1])-lip*(hi-lo)/2)
    return {'status':'positive' if lower>0 else 'undecided','lower':str(lower),
            'lp_calls':calls,'completed':True,'route':'grid_error_bound','grid_points':points}


def refine(query,epsilon,total=None,*,backend='highs',meshes=(9,33,129),time_limit=1.):
    """Refine nested denominator grids, reusing only same-query LP nodes."""
    started=time.process_time();a,b,c=fractions(query);mass=sum(b)
    if mass==0:total=F(0)
    engine=None;values={};calls=0
    def solve(s,remaining):
        nonlocal engine
        if backend=='highs':return solve_fixed(query,s,epsilon,remaining)
        if backend!='gurobi':raise ValueError('Unknown LP backend')
        from .gurobi import ConditionalLP
        if engine is None:engine=ConditionalLP(query,s,epsilon)
        return engine.solve(s,remaining)
    try:
        if total is not None:
            answer=solve(F(total),time_limit)
            return dict(answer,lp_calls=1,completed='lower' in answer,route='fixed_total_lp',backend=backend)
        for points in meshes:
            grid=[mass*F(j,points-1) for j in range(points)]
            order=sorted(range(points),key=lambda j:(abs(2*j-points+1),j))
            for j in order:
                s=grid[j]
                if s in values:continue
                remaining=time_limit-(time.process_time()-started)
                if remaining<=0:
                    return {'status':'undecided','lp_calls':calls,'completed':False,'route':'cpu_budget','backend':backend}
                result=solve(s,remaining);calls+=1
                if result['status']=='negative':
                    return dict(result,lp_calls=calls,completed=False,route='grid_witness',split_total=str(s),backend=backend)
                if 'lower' in result:values[s]=F(result['lower'])
            if not all(s in values for s in grid):continue
            lower=F(1)
            for lo,hi in zip(grid,grid[1:]):
                lip=max(1/(sum(aa)+lo)+1/(sum(cc)+mass-hi) for aa,cc in zip(a,c))
                lower=min(lower,min(values[lo],values[hi])-lip*(hi-lo)/2)
            if lower>0:return {'status':'positive','lower':str(lower),'lp_calls':calls,'completed':True,
                'route':'nested_grid_bound','grid_points':points,'backend':backend}
        return {'status':'undecided','lower':str(lower) if 'lower' in locals() else None,
                'lp_calls':calls,'completed':True,'route':'grid_resolution','backend':backend}
    finally:
        if engine is not None:engine.close()
