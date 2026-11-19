"""Continuous allocation + binary supplier selection, solved with SciPy HiGHS MILP."""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
MODEL_VERSION='allocation_milp_v1'

class Candidate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=150)
    unit_cost:Decimal=Field(ge=0,le=1000000000,decimal_places=4)
    capacity:Decimal=Field(ge=0,le=1000000000,decimal_places=4)
    minimum:Decimal=Field(default=Decimal(0),ge=0,le=1000000000,decimal_places=4)
    maximum:Decimal|None=Field(default=None,ge=0,le=1000000000,decimal_places=4)
    fixed_cost:Decimal=Field(default=Decimal(0),ge=0,le=1000000000,decimal_places=2)
    eligible:bool=True
    @model_validator(mode='after')
    def consistent(self):
        if self.minimum>self.capacity or self.maximum is not None and self.minimum>self.maximum:raise ValueError('Minimum exceeds capacity/maximum')
        return self
class OptimizationInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=3,max_length=200)
    units:str=Field(min_length=3,max_length=100)
    assumption_note:str=Field(min_length=10,max_length=2000)
    demand:Decimal=Field(gt=0,le=1000000000,decimal_places=4)
    candidates:list[Candidate]=Field(min_length=1,max_length=40)
    dependency_pct:Decimal=Field(default=Decimal(100),gt=0,le=100,decimal_places=4)
    min_suppliers:int=Field(default=1,ge=1,le=40)
    max_suppliers:int=Field(default=40,ge=1,le=40)
    time_limit:float=Field(default=10,ge=.01,le=30)
    context:str|None=Field(default=None,max_length=300)
    source_fingerprint:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')
    @model_validator(mode='after')
    def consistent(self):
        if self.min_suppliers>self.max_suppliers:raise ValueError('Supplier count bounds conflict')
        if len({x.name for x in self.candidates})!=len(self.candidates):raise ValueError('Supplier names must be distinct')
        return self

def solve(model:OptimizationInput):
    n=len(model.candidates);d=float(model.demand)
    costs=np.array([float(s.unit_cost) for s in model.candidates]+[float(s.fixed_cost) for s in model.candidates])
    upper=np.array([min(float(s.capacity),float(s.maximum) if s.maximum is not None else d,d*float(model.dependency_pct)/100) if s.eligible else 0 for s in model.candidates])
    # Selection means a strictly positive allocation, with a disclosed 0.0001-unit floor.
    floor=1e-4
    A=[];lo=[];hi=[]
    A.append([1]*n+[0]*n);lo.append(d);hi.append(d)
    A.append([0]*n+[1]*n);lo.append(model.min_suppliers);hi.append(model.max_suppliers)
    for i,s in enumerate(model.candidates):
        a=np.zeros(2*n);a[i]=1;a[n+i]=-upper[i];A.append(a);lo.append(-np.inf);hi.append(0)
        a=np.zeros(2*n);a[i]=1;a[n+i]=-max(float(s.minimum),floor);A.append(a);lo.append(0);hi.append(np.inf)
    matrix=np.array(A);lower=np.array(lo);higher=np.array(hi)
    result=milp(costs,integrality=np.array([0]*n+[1]*n),bounds=Bounds(np.zeros(2*n),np.concatenate([upper,np.array([1 if s.eligible else 0 for s in model.candidates])])),constraints=LinearConstraint(matrix,lower,higher),options={'time_limit':model.time_limit,'mip_rel_gap':0})
    statuses={0:'optimal',1:'limit_reached',2:'infeasible',3:'unbounded',4:'failed'}
    status=statuses.get(result.status,'unknown');valid=False;allocations=[];objective=None;bindings=[]
    tolerance=max(1e-6,d*1e-8)
    if result.x is not None and np.all(np.isfinite(result.x)):
        x=result.x;v=matrix@x
        valid=bool(all(x[i] >= floor/2 for i in range(n) if round(float(x[n+i]))) and np.all(x<=np.concatenate([upper,np.ones(n)])+tolerance) and np.all(v>=lower-tolerance) and np.all(v<=higher+tolerance) and np.all(x>=-tolerance) and np.all(np.abs(x[n:]-np.round(x[n:]))<=1e-6))
        if valid:
            for i,s in enumerate(model.candidates):
                amount=max(0,float(x[i]));selected=bool(round(float(x[n+i])))
                allocations.append(dict(name=s.name,allocation=format(amount,'.10g'),share_pct=format(amount/d*100,'.10g'),selected=selected,unit_cost=str(s.unit_cost),fixed_cost=str(s.fixed_cost),modelled_cost=str(Decimal(str(amount))*s.unit_cost+(s.fixed_cost if selected else 0))))
                if abs(amount-upper[i])<=tolerance and selected:bindings.append(f'{s.name}: capacity, allocation maximum or dependency bound')
                if selected and abs(amount-float(s.minimum))<=tolerance:bindings.append(f'{s.name}: minimum allocation')
            count=sum(a['selected'] for a in allocations)
            if count==model.min_suppliers:bindings.append('Minimum selected suppliers')
            if count==model.max_suppliers:bindings.append('Maximum selected suppliers')
            objective=str(sum(Decimal(a['modelled_cost']) for a in allocations))
            if status=='limit_reached':status='feasible_not_proven_optimal'
    if status=='optimal' and not valid:status='failed_validation'
    explanations=[]
    if sum(upper)+tolerance<d:explanations.append('Eligible capacity after dependency/allocation caps is below demand.')
    if sum(s.eligible for s in model.candidates)<model.min_suppliers:explanations.append('Fewer eligible suppliers than the required minimum.')
    if status=='infeasible' and not explanations:explanations.append('The combined minimum allocations, capacities and supplier-count constraints are infeasible. Relax constraints and rerun; no irreducible conflict set is claimed.')
    return dict(model_version=MODEL_VERSION,status=status,solver_status=int(result.status),feasible=valid,objective_gbp=objective,allocations=allocations,binding_constraints=bindings,
        explanations=explanations,mip_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None,
        validation=dict(tolerance_units=tolerance,selected_allocation_floor_units=floor,checked_constraints=valid),
        limitation='Analyst-supplied comparable-unit assumptions, not HMRC quotations, capacities or achievable savings. Solver uses floating-point tolerances.')
