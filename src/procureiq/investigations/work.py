"""Transactional analyst work, referencing frozen case evidence; never source edits."""
from sqlalchemy import text
from . import repository as repo
from .domain import InvestigationError


def rows(conn,sql,params):
    return [dict(r) for r in conn.execute(text(sql),params).mappings()]


class CaseWork:
    def __init__(self,engine):self.engine=engine

    def list(self,case_id,offset=0,limit=50):
        with self.engine.connect() as c:
            repo.get_case(c,case_id,detail=False)
            entries=rows(c,'SELECT * FROM procureiq_app.case_entry WHERE case_id=:id AND NOT deleted ORDER BY entry_id LIMIT :limit OFFSET :offset',dict(id=case_id,limit=limit,offset=offset))
            for e in entries:
                e['citations']=rows(c,'SELECT classification,ordinal FROM procureiq_app.finding_evidence WHERE entry_id=:id ORDER BY classification,ordinal',dict(id=e['entry_id']))
            total=c.execute(text('SELECT count(*) FROM procureiq_app.case_entry WHERE case_id=:id AND NOT deleted'),dict(id=case_id)).scalar_one()
            return dict(items=entries,total=total,offset=offset,limit=limit)

    def bookmarks(self,case_id,offset=0,limit=50):
        with self.engine.connect() as c:
            repo.get_case(c,case_id,detail=False)
            items=rows(c,'''SELECT b.*,e.raw_row_id,e.file_id,e.file_sha256,e.source_record_number,r.source_values,f.reporting_month FROM procureiq_app.case_bookmark b
              JOIN procureiq_app.case_evidence e USING(case_id,classification,ordinal)
              JOIN procureiq.raw_spend_row r ON r.raw_row_id=e.raw_row_id JOIN procureiq.source_file f ON f.file_id=e.file_id
              WHERE b.case_id=:id AND b.active ORDER BY classification,ordinal LIMIT :limit OFFSET :offset''',dict(id=case_id,limit=limit,offset=offset))
            total=c.execute(text('SELECT count(*) FROM procureiq_app.case_bookmark WHERE case_id=:id AND active'),dict(id=case_id)).scalar_one()
            return dict(items=items,total=total,offset=offset,limit=limit)

    def bookmark(self,case_id,classification,ordinal,active):
        with self.engine.begin() as c:
            case=repo.get_case(c,case_id,detail=False,lock=True)
            self.editable(case)
            ref=c.execute(text('SELECT 1 FROM procureiq_app.case_evidence WHERE case_id=:id AND classification=:kind AND ordinal=:ordinal'),dict(id=case_id,kind=classification,ordinal=ordinal)).scalar()
            if not ref:raise InvestigationError('invalid_evidence','Evidence does not belong to this case.',422)
            old=c.execute(text('SELECT active FROM procureiq_app.case_bookmark WHERE case_id=:id AND classification=:kind AND ordinal=:ordinal'),dict(id=case_id,kind=classification,ordinal=ordinal)).scalar()
            if old==active or old is None and not active:return dict(changed=False)
            c.execute(text('''INSERT INTO procureiq_app.case_bookmark(case_id,classification,ordinal,active) VALUES(:id,:kind,:ordinal,:active)
              ON CONFLICT(case_id,classification,ordinal) DO UPDATE SET active=excluded.active'''),dict(id=case_id,kind=classification,ordinal=ordinal,active=active))
            repo.event(c,case_id,'EVIDENCE_BOOKMARKED' if active else 'BOOKMARK_REMOVED',case['status'],case['status'],None,dict(classification=classification,ordinal=ordinal))
            return dict(changed=True)

    @staticmethod
    def editable(case):
        if case['status']=='CLOSED':raise InvestigationError('case_closed','Reopen this case with a reason before editing analyst work.')

    def save(self,case_id,body,entry_id=None):
        with self.engine.begin() as c:
            case=repo.get_case(c,case_id,detail=False,lock=True);self.editable(case)
            old=None
            if entry_id is not None:
                old=c.execute(text('SELECT * FROM procureiq_app.case_entry WHERE entry_id=:entry AND case_id=:id FOR UPDATE'),dict(entry=entry_id,id=case_id)).mappings().first()
                if not old or old['deleted']:raise InvestigationError('entry_not_found','Analyst entry not found.',404)
                if old['row_version']!=body.expected_version:raise InvestigationError('case_version_conflict','This entry changed. Refresh before editing.')
                if old['kind']!=body.kind:raise InvestigationError('invalid_input','Entry kind cannot change.',422)
                old=dict(old)
                old['citations']=rows(c,'SELECT classification,ordinal FROM procureiq_app.finding_evidence WHERE entry_id=:entry ORDER BY classification,ordinal',dict(entry=entry_id))
            elif body.deleted:raise InvestigationError('invalid_input','Cannot create a deleted entry.',422)
            citations=[x.model_dump() for x in body.citations]
            if body.kind=='note' and citations:raise InvestigationError('invalid_input','Only findings can cite bookmarked evidence.',422)
            for citation in citations:
                exists=c.execute(text('SELECT 1 FROM procureiq_app.case_bookmark WHERE case_id=:id AND classification=:classification AND ordinal=:ordinal AND active'),dict(id=case_id,**citation)).scalar()
                if not exists and not (old and citation in old['citations']):raise InvestigationError('invalid_evidence','Citations must be active bookmarks in this case.',422)
            from procureiq.opportunities import canonical
            params=dict(sections=canonical(body.sections.model_dump()) if body.sections else None,id=case_id,title=body.title.strip(),content=body.content.strip(),kind=body.kind,deleted=body.deleted,entry=entry_id)
            if old:
                entry_id=c.execute(text('UPDATE procureiq_app.case_entry SET title=:title,content=:content,sections=CAST(:sections AS jsonb),deleted=:deleted,row_version=row_version+1,updated_at=now() WHERE entry_id=:entry RETURNING entry_id'),params).scalar_one()
                c.execute(text('DELETE FROM procureiq_app.finding_evidence WHERE entry_id=:entry'),dict(entry=entry_id))
            else:entry_id=c.execute(text('INSERT INTO procureiq_app.case_entry(case_id,title,content,kind,sections) VALUES(:id,:title,:content,:kind,CAST(:sections AS jsonb)) RETURNING entry_id'),params).scalar_one()
            for citation in citations:
                c.execute(text('INSERT INTO procureiq_app.finding_evidence(case_id,entry_id,classification,ordinal) VALUES(:id,:entry,:classification,:ordinal)'),dict(id=case_id,entry=entry_id,**citation))
            new=rows(c,'SELECT * FROM procureiq_app.case_entry WHERE entry_id=:entry',dict(entry=entry_id))[0]
            new['citations']=citations
            # Full prior/current analyst text retained in append-only history, including soft deletion.
            from procureiq.opportunities import canonical
            import json
            event=body.kind.upper()+'_'+('DELETED' if body.deleted else 'UPDATED' if old else 'CREATED')
            repo.event(c,case_id,event,case['status'],case['status'],None,json.loads(canonical(dict(before=old,after=new))))
            return new
