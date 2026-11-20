"""Independent reconstruction of the pinned left-deep QUBO's actual penalties."""
import itertools
import math
import numpy as np
from qopt.core import valid_membership


def components(bits,cards,pred,pred_sel,precision_digits=2,threshold=.63):
    n=len(cards);joins=n-2;p=len(pred)
    slack_count=math.floor(math.log2(threshold/(.1**precision_digits)))+1
    assert len(bits)==n*joins+p*joins+slack_count*joins
    v=np.asarray(bits[:n*joins]).reshape(n,joins)
    z=np.asarray(bits[n*joins:(n+p)*joins]).reshape(p,joins)
    slack=np.asarray(bits[(n+p)*joins:]).reshape(joins,slack_count)
    count=sum((j+2-int(v[:,j].sum()))**2 for j in range(joins))
    nesting=sum(int(v[t,j-1])*(1-int(v[t,j])) for t in range(n) for j in range(1,joins))
    activation=sum(int(z[k,j])*(2-int(v[a,j])-int(v[b,j])) for k,(a,b) in enumerate(pred) for j in range(joins))
    inactive=sum(int(v[a,j] and v[b,j] and not z[k,j]) for k,(a,b) in enumerate(pred) for j in range(joins))
    log_cards=np.around(np.log10(cards),precision_digits)
    log_sel=np.around(np.log10(pred_sel),precision_digits)
    weights=np.asarray([(.1**precision_digits)*2**i for i in range(slack_count)])
    cost=sum(float(slack[j].dot(weights)-v[:,j].dot(log_cards)-z[:,j].dot(log_sel))**2 for j in range(joins))
    weight=max(20,2*joins)
    return {'count_penalty':int(count),'nesting_penalty':int(nesting),'predicate_activation_penalty':int(activation),
        'inactive_applicable_predicates':int(inactive),'hard_penalty':int(count+nesting+activation),
        'hard_feasible':not(count+nesting+activation),'cost_component':cost,
        'penalty_weight':weight,'reconstructed_energy':weight*(count+nesting+activation)+cost,
        'note':'Predicate constraints are one-way implications; an inactive applicable predicate is not a hard violation in this encoding. Slack residual is an objective term, not an extra hard equality.'}


def validity_bqm(n,pred):
    import dimod
    joins=n-2;bqm=dimod.BinaryQuadraticModel({}, {},0,dimod.BINARY)
    for j in range(joins):
        ids=[t*joins+j for t in range(n)]
        bqm.offset+=(j+2)**2
        for x in ids:
            bqm.add_variable(x,1-2*(j+2))
        for a,b in itertools.combinations(ids,2):
            bqm.add_interaction(a,b,2)
    for t in range(n):
        for j in range(1,joins):
            bqm.add_variable(t*joins+j-1,1)
            bqm.add_interaction(t*joins+j-1,t*joins+j,-1)
    for k,(a,b) in enumerate(pred):
        for j in range(joins):
            z=n*joins+k*joins+j
            bqm.add_variable(z,2)
            bqm.add_interaction(z,a*joins+j,-1)
            bqm.add_interaction(z,b*joins+j,-1)
    return bqm
