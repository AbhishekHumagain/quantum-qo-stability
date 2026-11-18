"""Estimated filtered base/pair inputs, with SQL evidence and modelling caveats."""
import math


def quote(name):
    return '"'+name.replace('"','""')+'"'


def estimate_inputs(conn, query):
    mapping = query['alias_mapping']
    aliases = [item['alias'] for item in mapping]
    sources = {item['alias']: quote(item['table'])+' AS '+quote(item['alias']) for item in mapping}
    cards, evidence = [], []
    def estimate(involved, predicates):
        statement = 'SELECT * FROM '+', '.join(sources[a] for a in involved)
        if predicates:
            statement += ' WHERE '+' AND '.join('('+p+')' for p in predicates)
        plan = conn.execute('EXPLAIN (FORMAT JSON) '+statement).fetchone()[0][0]
        rows = plan['Plan']['Plan Rows']
        if not math.isfinite(rows) or rows <= 0:
            raise ValueError('Encoding requires positive estimated cardinalities')
        evidence.append({'aliases':involved,'sql':statement,'estimated_rows':rows,'explain':plan})
        return rows
    if query['unsupported_cross_alias_predicates']:
        raise ValueError('Unsupported cross-alias predicates')
    filters=query['local_filters']
    for alias in aliases:
        cards.append(estimate([alias],filters.get(alias,[])))
    factors=[[1.0]*len(cards) for _ in cards]
    lost_edges=[]
    for i,a in enumerate(aliases):
        for j in range(i+1,len(aliases)):
            b=aliases[j]
            predicates=[p['sql'] for p in query['join_predicates'] if set(p['aliases'])=={a,b}]
            if not predicates:
                continue
            rows=estimate([a,b],filters.get(a,[])+filters.get(b,[])+predicates)
            factor=rows/(cards[i]*cards[j])
            factors[i][j]=factors[j][i]=factor
            if factor==1.0:
                lost_edges.append([a,b])
    return {'kind':'PostgreSQL_estimated_filtered_base_and_pair_rows',
        'alias_mapping':mapping,'cards':cards,'factors':factors,'evidence':evidence,
        'factor_one_predicate_edges':lost_edges,
        'upstream_factor_parser_preserves_all_predicate_edges':not lost_edges,
        'warning':'Pair factors are an approximation; not true multiway cardinalities. PostgreSQL Plan Rows floors/rounding are retained.'}
