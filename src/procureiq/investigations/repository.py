"""Parameterized persistence; immutable historical evidence never joins active views."""
from hashlib import sha256
from sqlalchemy import text
from procureiq.opportunities import canonical
from .domain import InvestigationError
from .namespace import current_namespace

CASE_COLUMNS='namespace,case_id,case_reference,title,objective,opportunity_id,opportunity_type,original_score,rule_version,configuration_identity,reporting_filters,source_fingerprint,review_basis_key,status,row_version,primary_count,contextual_count,created_at,updated_at,reviewed_at,closed_at,disposition,closure_explanation'


def get_case(conn,case_id,lock=False,detail=True):
    cols=CASE_COLUMNS+(',review_snapshot,configuration' if detail else '')
    row=conn.execute(text(f'SELECT {cols} FROM procureiq_app.investigation_case WHERE case_id=:id'+(' FOR UPDATE' if lock else '')),dict(id=case_id)).mappings().first()
    if not row:raise InvestigationError('case_not_found','Investigation case not found.',404)
    if row['namespace']!=current_namespace.get():raise InvestigationError('namespace_mismatch','This case belongs to the other workspace. Switch Normal/Demo Mode explicitly.',409)
    return dict(row)


def existing(conn,keys):
    if not keys:return {}
    rows=conn.execute(text('SELECT review_basis_key,case_id,case_reference,status FROM procureiq_app.investigation_case WHERE review_basis_key=ANY(:keys) AND namespace=:namespace'),dict(keys=keys,namespace=current_namespace.get())).mappings()
    return {r['review_basis_key']:dict(r) for r in rows}


def insert_case(conn,item,basis,key,title,objective,configuration):
    snapshot={k:v for k,v in item.items() if k not in ('source_references','context_source_references','configuration')}
    row=conn.execute(text('''INSERT INTO procureiq_app.investigation_case
      (namespace,title,objective,opportunity_id,opportunity_type,original_score,review_snapshot,rule_version,configuration,
       configuration_identity,reporting_filters,source_fingerprint,review_basis_key,primary_count,contextual_count)
      VALUES (:namespace,:title,:objective,:oid,:kind,:score,CAST(:snapshot AS jsonb),:rule,CAST(:config AS jsonb),:config_id,
       CAST(:filters AS jsonb),:source,:key,:primary,:contextual)
      ON CONFLICT (review_basis_key,namespace) DO NOTHING RETURNING case_id'''),dict(namespace=current_namespace.get(),title=title,objective=objective,
        oid=item['opportunity_id'],kind=item['opportunity_type'],score=item['scoring']['priority_score'],
        snapshot=canonical(snapshot),rule=basis['rule_version'],config=canonical(configuration),config_id=basis['configuration_identity'],
        filters=canonical(basis['filters']),source=basis['source_fingerprint'],key=key,
        primary=len(item['source_references']),contextual=len(item['context_source_references']))).scalar()
    return row


def insert_evidence(conn,case_id,item):
    allrefs=item['source_references']+item['context_source_references']
    ids=list({r['raw_row_id'] for r in allrefs})
    rows={r['raw_row_id']:r for r in conn.execute(text('''SELECT r.raw_row_id,r.file_id,r.source_record_number,r.row_hash,f.sha256,
       r.physical_line_start,r.physical_line_end,f.reporting_month FROM procureiq.raw_spend_row r
       JOIN procureiq.source_file f USING(file_id) WHERE r.raw_row_id=ANY(:ids)'''),dict(ids=ids)).mappings()}
    records=[]
    for kind,field in [('primary','source_references'),('contextual','context_source_references')]:
        for ordinal,ref in enumerate(item[field],1):
            row=rows.get(ref['raw_row_id'])
            if not row or any(row[k]!=ref[k] for k in ('file_id','source_record_number','sha256','physical_line_start','physical_line_end','reporting_month')):
                raise InvestigationError('evidence_integrity','Resolved evidence does not match immutable source lineage.')
            records.append(dict(case_id=case_id,classification=kind,ordinal=ordinal,raw_row_id=row['raw_row_id'],file_id=row['file_id'],
                file_sha256=row['sha256'],source_record_number=row['source_record_number'],row_hash=row['row_hash']))
    if records:
        # One bounded set of executemany batches, without a giant VALUES SQL string.
        stmt=text('''INSERT INTO procureiq_app.case_evidence
          (case_id,classification,ordinal,raw_row_id,file_id,file_sha256,source_record_number,row_hash)
          VALUES (:case_id,:classification,:ordinal,:raw_row_id,:file_id,:file_sha256,:source_record_number,:row_hash)''')
        for start in range(0,len(records),500):conn.execute(stmt,records[start:start+500])


def event(conn,case_id,event_type,previous,new,reason,details):
    conn.execute(text('''INSERT INTO procureiq_app.case_event(case_id,event_type,previous_status,new_status,reason,details)
       VALUES (:id,:kind,:old,:new,:reason,CAST(:details AS jsonb))'''),dict(id=case_id,kind=event_type,old=previous,new=new,reason=reason,details=canonical(details)))


def list_cases(conn,status,offset,limit):
    params=dict(status=status,offset=offset,limit=limit,namespace=current_namespace.get())
    where='WHERE namespace=:namespace'+(' AND status=:status' if status else '')
    total=conn.execute(text('SELECT count(*) FROM procureiq_app.investigation_case '+where),params).scalar_one()
    rows=conn.execute(text(f'SELECT {CASE_COLUMNS} FROM procureiq_app.investigation_case {where} ORDER BY case_id LIMIT :limit OFFSET :offset'),params).mappings()
    return dict(total=total,items=[dict(r) for r in rows],offset=offset,limit=limit)


def evidence(conn,case,classification,offset,limit,filters=None):
    filters=filters or {}
    params=dict(id=case['case_id'],kind=classification,offset=offset,limit=limit,**filters)
    base=""" FROM procureiq_app.case_evidence e
       LEFT JOIN procureiq.raw_spend_row r ON r.raw_row_id=e.raw_row_id
       LEFT JOIN procureiq.source_file f ON f.file_id=e.file_id
       LEFT JOIN procureiq.spend_line s ON s.raw_row_id=e.raw_row_id
       WHERE e.case_id=:id AND e.classification=:kind"""
    total=conn.execute(text('SELECT count(*)'+base),params).scalar_one()
    expected=case['primary_count' if classification=='primary' else 'contextual_count']
    broken=conn.execute(text("SELECT count(*)"+base+" AND (r.raw_row_id IS NULL OR f.file_id IS NULL OR r.file_id<>e.file_id OR r.row_hash<>e.row_hash OR f.sha256<>e.file_sha256 OR r.source_record_number<>e.source_record_number)"),params).scalar_one()
    if total!=expected or broken:raise InvestigationError('evidence_integrity','Saved historical evidence is missing or inconsistent; no substitution is permitted.')
    clauses=[]
    for key,expr in [('supplier',"r.source_values->>'Supplier' = :supplier"),('start_month','f.reporting_month>=CAST(:start_month AS date)'),('end_month','f.reporting_month<=CAST(:end_month AS date)'),('minimum_amount','s.amount_gbp>=:minimum_amount'),('maximum_amount','s.amount_gbp<=:maximum_amount'),('transaction',"strpos(coalesce(r.source_values->>'Transaction number',''),:transaction)>0"),('search',"strpos(lower(r.source_values::text),lower(:search))>0")]:
        if filters.get(key) is not None:clauses.append(expr)
    selected=base+(' AND '+' AND '.join(clauses) if clauses else '')
    filtered=conn.execute(text('SELECT count(*)'+selected),params).scalar_one()
    summary=dict(count=filtered,
        suppliers=[dict(r) for r in conn.execute(text("SELECT r.source_values->>'Supplier' AS supplier,count(*) AS count,coalesce(sum(greatest(s.amount_gbp,0)),0) AS positive_gbp"+selected+" GROUP BY 1 ORDER BY positive_gbp DESC, supplier LIMIT 8"),params).mappings()],
        months=[dict(r) for r in conn.execute(text('SELECT f.reporting_month,count(*) AS count'+selected+' GROUP BY 1 ORDER BY 1'),params).mappings()],
        composition=dict(conn.execute(text('SELECT coalesce(sum(greatest(s.amount_gbp,0)),0) AS positive_gbp,coalesce(-sum(least(s.amount_gbp,0)),0) AS credit_gbp'+selected),params).mappings().one()))
    rows=conn.execute(text("""SELECT e.*,r.source_values,r.physical_line_start,r.physical_line_end,f.filename,f.reporting_month,
         f.active AS source_currently_active,s.amount_gbp,
         EXISTS(SELECT 1 FROM procureiq_app.case_bookmark b WHERE b.case_id=e.case_id AND b.classification=e.classification AND b.ordinal=e.ordinal AND b.active) AS bookmarked
       """+selected+' ORDER BY e.ordinal LIMIT :limit OFFSET :offset'),params).mappings()
    output=[]
    for r in rows:
        if sha256(canonical(r['source_values']).encode()).hexdigest()!=r['row_hash']:
            raise InvestigationError('evidence_integrity','Historical raw field contents failed their recorded checksum.')
        output.append(dict(r))
    return dict(total=filtered,unfiltered_total=total,summary=summary,items=output,offset=offset,limit=limit,classification=classification)


def activity(conn,case_id,offset,limit,kind=None):
    get_case(conn,case_id,detail=False)
    params=dict(id=case_id,offset=offset,limit=limit)
    events={'lifecycle':['CASE_CREATED','STATUS_CHANGED','CASE_REOPENED'],'findings':['FINDING_CREATED','FINDING_UPDATED','FINDING_DELETED'],'notes':['NOTE_CREATED','NOTE_UPDATED','NOTE_DELETED'],'evidence':['EVIDENCE_BOOKMARKED','BOOKMARK_REMOVED']}
    clause=''
    if kind:
        if kind not in events:raise InvestigationError('invalid_input','Unknown activity filter.',422)
        params['events']=events[kind];clause=' AND event_type=ANY(:events)'
    total=conn.execute(text('SELECT count(*) FROM procureiq_app.case_event WHERE case_id=:id'+clause),params).scalar_one()
    rows=conn.execute(text('SELECT * FROM procureiq_app.case_event WHERE case_id=:id'+clause+' ORDER BY event_id LIMIT :limit OFFSET :offset'),params).mappings()
    return dict(total=total,items=[dict(r) for r in rows],offset=offset,limit=limit)
