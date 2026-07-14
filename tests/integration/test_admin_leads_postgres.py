"""Phase 5A lead flow against explicitly configured isolated PostgreSQL."""
import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services import admin_leads_service

DATABASE_URL=os.getenv("TEST_ADMIN_DATABASE_URL","").strip()
pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="isolated PostgreSQL is required")
ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine():
    database=create_engine(DATABASE_URL,pool_pre_ping=True)
    auth=(ROOT/"migrations/014_admin_auth_foundation.sql").read_text();auth_back=(ROOT/"migrations/014_admin_auth_foundation.rollback.sql").read_text();leads=(ROOT/"migrations/020_automation_service_leads.sql").read_text();leads_back=(ROOT/"migrations/020_automation_service_leads.rollback.sql").read_text()
    with database.begin() as connection:
        connection.exec_driver_sql("""DO $$ BEGIN CREATE ROLE anon; EXCEPTION WHEN duplicate_object THEN NULL; END $$;DO $$ BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END $$;CREATE TABLE public.users(id BIGINT PRIMARY KEY,email TEXT UNIQUE,password_hash TEXT,role TEXT,email_verified BOOLEAN,approval_status TEXT,last_login_at TIMESTAMPTZ);""")
        connection.exec_driver_sql(auth);connection.exec_driver_sql(leads);connection.exec_driver_sql(leads_back);assert connection.execute(text("SELECT to_regclass('public.automation_service_leads')")).scalar_one() is None;connection.exec_driver_sql(leads)
        connection.execute(text("INSERT INTO users(id,email,role,email_verified,approval_status) VALUES (1,'phase5a-integration@example.test','ADMIN',TRUE,'APPROVED')"))
    yield database
    with database.begin() as connection:
        connection.exec_driver_sql(leads_back);connection.exec_driver_sql(auth_back);connection.exec_driver_sql("DROP TABLE IF EXISTS public.users")
    database.dispose()


@pytest.fixture()
def isolated_scope(monkeypatch:pytest.MonkeyPatch,engine):
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    @contextmanager
    def scope():
        session=factory()
        try:yield session;session.commit()
        except Exception:session.rollback();raise
        finally:session.close()
    monkeypatch.setattr(admin_leads_service,"session_scope",scope)
    yield engine
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM automation_service_leads WHERE business_email='phase5a-integration@example.test'"))
        connection.execute(text("DELETE FROM admin_auth_audit_events WHERE request_id LIKE 'phase5a-integration-%'"))


def test_submit_review_notes_archive_restore_and_delete(isolated_scope):
    lead=admin_leads_service.create_public_lead(name="Integration Operator",business_email="phase5a-integration@example.test",country="India",business_type="SaaS",requested_services=["n8n Workflows"],current_tools="CRM",project_description="Integration-only workflow qualification content.",primary_problem="Manual operational handoffs.",expected_outcome="A reviewed observable workflow.",budget_range="Not decided",preferred_timeline="Flexible / planning",preferred_contact_method="EMAIL",consent=True,website_confirm="")
    listed=admin_leads_service.list_leads(page=1,page_size=10,search=lead["reference"][:8]);assert listed["total"]==1
    item=listed["items"][0];assert "internal_notes" not in item
    reviewed=admin_leads_service.update_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-review",status="REVIEWING",internal_notes="Reviewed locally.");assert reviewed["status"]=="REVIEWING"
    archived=admin_leads_service.update_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-archive",status="ARCHIVED");assert archived["status"]=="ARCHIVED"
    trashed=admin_leads_service.update_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-trash",status="TRASHED");assert trashed["deleted_at"] is not None
    restored=admin_leads_service.update_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-restore",status="NEW");assert restored["deleted_at"] is None
    admin_leads_service.update_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-trash2",status="TRASHED")
    assert admin_leads_service.delete_lead(lead_id=item["id"],actor_id=1,request_id="phase5a-integration-delete",confirmed=True)=={"deleted":True}
