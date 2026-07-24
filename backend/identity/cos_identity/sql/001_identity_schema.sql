-- ============================================================================
-- Identity & RBAC Core (C7) — schema, roles, and FORCE row-level security.
--
-- psql \set-parameterized. Apply as a superuser (or a role that may ALTER object
-- ownership) with, e.g.:
--
--   psql -v schema=cos_identity \
--        -v owner_role=cos_identity_owner \
--        -v app_role=cos_identity_app \
--        -v auth_role=cos_identity_auth \
--        -f 001_identity_schema.sql
--
-- DESIGN (plan D1/D2):
--   * Two NON-OWNER application roles. :app_role runs every product/admin query
--     and is STRICTLY tenant-scoped — with app-layer filters removed it still
--     sees only its own tenant (SC-003). :auth_role additionally carries a
--     broker policy, entered only via app.identity_broker='on' (set by exactly
--     three service methods), for the cross-tenant lookups by unique key that
--     login inherently requires.
--   * ENABLE + FORCE row level security on all six tables — the wall is the DB.
--   * Session vars: app.customer_id, app.user_role, app.user_id,
--     app.cs_admin_scope (csv), app.identity_broker.
-- ============================================================================

SET client_min_messages = warning;

-- ── Roles (idempotent). Requires psql for \gexec; a non-psql applier must
--    create :owner_role/:app_role/:auth_role (NOLOGIN, non-owner) beforehand.
SELECT format('CREATE ROLE %I NOLOGIN', role_name)
FROM (VALUES (:'owner_role'), (:'app_role'), (:'auth_role')) AS t(role_name)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name)
\gexec

-- ── Schema ------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS :schema;
ALTER SCHEMA :schema OWNER TO :owner_role;
GRANT USAGE ON SCHEMA :schema TO :app_role, :auth_role;

-- ── Tables ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS :schema.tenant (
    key            text PRIMARY KEY,
    display_name   text NOT NULL,
    parent_key     text NULL REFERENCES :schema.tenant(key),
    auth_provider  text NOT NULL DEFAULT 'google'
                       CHECK (auth_provider IN ('google', 'microsoft', 'password')),
    allowed_domains text[] NOT NULL DEFAULT '{}',
    status         text NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active', 'inactive')),
    default_locale text NOT NULL DEFAULT 'en-US',
    timezone       text NOT NULL DEFAULT 'UTC',
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE :schema.tenant OWNER TO :owner_role;
CREATE INDEX IF NOT EXISTS tenant_allowed_domains_gin
    ON :schema.tenant USING gin (allowed_domains);
CREATE INDEX IF NOT EXISTS tenant_parent_key_idx
    ON :schema.tenant (parent_key);

CREATE TABLE IF NOT EXISTS :schema.app_user (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_uid   text NULL,
    email          text NOT NULL,
    display_name   text NULL,
    role           text NOT NULL DEFAULT 'viewer'
                       CHECK (role IN ('superuser', 'cs_admin', 'agent', 'viewer')),
    customer_role  text NOT NULL DEFAULT 'member'
                       CHECK (customer_role IN ('account_owner', 'member')),
    status         text NOT NULL DEFAULT 'active'
                       CHECK (status IN ('invited', 'active', 'suspended')),
    provider       text NOT NULL DEFAULT 'google'
                       CHECK (provider IN ('google', 'microsoft', 'password')),
    password_hash  text NULL,
    tenant_key     text NULL REFERENCES :schema.tenant(key),
    last_sign_in_at timestamptz NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE :schema.app_user OWNER TO :owner_role;
CREATE UNIQUE INDEX IF NOT EXISTS app_user_email_lower_uq
    ON :schema.app_user (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS app_user_provider_uid_uq
    ON :schema.app_user (provider_uid) WHERE provider_uid IS NOT NULL;
CREATE INDEX IF NOT EXISTS app_user_tenant_key_idx
    ON :schema.app_user (tenant_key);

CREATE TABLE IF NOT EXISTS :schema.invitation (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email       text NOT NULL,
    role        text NOT NULL
                    CHECK (role IN ('cs_admin', 'agent', 'viewer')),
    tenant_key  text NULL REFERENCES :schema.tenant(key),
    invited_by  uuid NULL,
    status      text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'expired')),
    expires_at  timestamptz NOT NULL DEFAULT (now() + interval '7 days'),
    accepted_at timestamptz NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE :schema.invitation OWNER TO :owner_role;
CREATE INDEX IF NOT EXISTS invitation_email_idx ON :schema.invitation (lower(email));
CREATE INDEX IF NOT EXISTS invitation_tenant_key_idx ON :schema.invitation (tenant_key);

CREATE TABLE IF NOT EXISTS :schema.refresh_token (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL REFERENCES :schema.app_user(id) ON DELETE CASCADE,
    tenant_key text NULL REFERENCES :schema.tenant(key),
    token_hash text NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE :schema.refresh_token OWNER TO :owner_role;
CREATE INDEX IF NOT EXISTS refresh_token_user_idx ON :schema.refresh_token (user_id);

CREATE TABLE IF NOT EXISTS :schema.support_assignment (
    user_id     uuid NOT NULL REFERENCES :schema.app_user(id) ON DELETE CASCADE,
    tenant_key  text NOT NULL REFERENCES :schema.tenant(key),
    assigned_by uuid NULL,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, tenant_key)
);
ALTER TABLE :schema.support_assignment OWNER TO :owner_role;
CREATE INDEX IF NOT EXISTS support_assignment_user_idx
    ON :schema.support_assignment (user_id);

CREATE TABLE IF NOT EXISTS :schema.audit_log (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    action            text NOT NULL CHECK (action IN (
                          'invite', 'accept', 'role_change', 'tenant_assign',
                          'suspend', 'reactivate', 'sign_in', 'sign_out',
                          'escape_hatch')),
    actor_user_id     uuid NULL,
    target_user_id    uuid NULL,
    target_tenant_key text NULL,
    before_state      jsonb NULL,
    after_state       jsonb NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE :schema.audit_log OWNER TO :owner_role;
CREATE INDEX IF NOT EXISTS audit_log_order_idx
    ON :schema.audit_log (created_at, id);
CREATE INDEX IF NOT EXISTS audit_log_tenant_idx
    ON :schema.audit_log (target_tenant_key);

-- ── Grants ------------------------------------------------------------------
-- Full CRUD on the mutable tables to both app roles; audit is append-only
-- (INSERT + SELECT only) — no UPDATE/DELETE grant, so audit rows are immutable.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON :schema.tenant, :schema.app_user, :schema.invitation,
       :schema.refresh_token, :schema.support_assignment
    TO :app_role, :auth_role;
GRANT SELECT, INSERT ON :schema.audit_log TO :app_role, :auth_role;

-- ── Row-level security: ENABLE + FORCE on every table ----------------------
ALTER TABLE :schema.tenant             ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.tenant             FORCE  ROW LEVEL SECURITY;
ALTER TABLE :schema.app_user           ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.app_user           FORCE  ROW LEVEL SECURITY;
ALTER TABLE :schema.invitation         ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.invitation         FORCE  ROW LEVEL SECURITY;
ALTER TABLE :schema.refresh_token      ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.refresh_token      FORCE  ROW LEVEL SECURITY;
ALTER TABLE :schema.support_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.support_assignment FORCE  ROW LEVEL SECURITY;
ALTER TABLE :schema.audit_log          ENABLE ROW LEVEL SECURITY;
ALTER TABLE :schema.audit_log          FORCE  ROW LEVEL SECURITY;

-- Tenant-scope predicate (D2). Fail-closed: unset vars → current_setting(...,
-- true) is NULL → no branch matches → zero rows. cs_admin_scope is a csv.

-- tenant (keyed on `key`)
CREATE POLICY tenant_scope ON :schema.tenant
    FOR ALL TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR key = current_setting('app.customer_id', true)
    )
    WITH CHECK (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR key = current_setting('app.customer_id', true)
    );
CREATE POLICY tenant_broker ON :schema.tenant
    FOR ALL TO :auth_role
    USING (current_setting('app.identity_broker', true) = 'on')
    WITH CHECK (current_setting('app.identity_broker', true) = 'on');

-- app_user (keyed on tenant_key)
CREATE POLICY app_user_scope ON :schema.app_user
    FOR ALL TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    )
    WITH CHECK (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    );
CREATE POLICY app_user_broker ON :schema.app_user
    FOR ALL TO :auth_role
    USING (current_setting('app.identity_broker', true) = 'on')
    WITH CHECK (current_setting('app.identity_broker', true) = 'on');

-- invitation (keyed on tenant_key)
CREATE POLICY invitation_scope ON :schema.invitation
    FOR ALL TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    )
    WITH CHECK (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    );
CREATE POLICY invitation_broker ON :schema.invitation
    FOR ALL TO :auth_role
    USING (current_setting('app.identity_broker', true) = 'on')
    WITH CHECK (current_setting('app.identity_broker', true) = 'on');

-- refresh_token (keyed on tenant_key; own-token branch by app.user_id)
CREATE POLICY refresh_token_scope ON :schema.refresh_token
    FOR ALL TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
        OR user_id::text = current_setting('app.user_id', true)
    )
    WITH CHECK (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
        OR user_id::text = current_setting('app.user_id', true)
    );
CREATE POLICY refresh_token_broker ON :schema.refresh_token
    FOR ALL TO :auth_role
    USING (current_setting('app.identity_broker', true) = 'on')
    WITH CHECK (current_setting('app.identity_broker', true) = 'on');

-- support_assignment (keyed on tenant_key)
CREATE POLICY support_assignment_scope ON :schema.support_assignment
    FOR ALL TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    )
    WITH CHECK (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR tenant_key = current_setting('app.customer_id', true)
    );
CREATE POLICY support_assignment_broker ON :schema.support_assignment
    FOR ALL TO :auth_role
    USING (current_setting('app.identity_broker', true) = 'on')
    WITH CHECK (current_setting('app.identity_broker', true) = 'on');

-- audit_log: append-only. INSERT always permitted to app roles (WITH CHECK
-- true); reads scoped by target_tenant_key. No UPDATE/DELETE grant exists.
CREATE POLICY audit_insert ON :schema.audit_log
    FOR INSERT TO :app_role, :auth_role
    WITH CHECK (true);
-- No broker branch here: audit is written (INSERT) under broker during sign-in,
-- but is NEVER read via the broker posture — so :app_role has no broker path on
-- any table (SC-003). Reads are strictly tenant-scoped.
CREATE POLICY audit_select ON :schema.audit_log
    FOR SELECT TO :app_role, :auth_role
    USING (
        current_setting('app.user_role', true) = 'superuser'
        OR (current_setting('app.user_role', true) = 'cs_admin'
            AND target_tenant_key = ANY(string_to_array(current_setting('app.cs_admin_scope', true), ',')))
        OR target_tenant_key = current_setting('app.customer_id', true)
    );
