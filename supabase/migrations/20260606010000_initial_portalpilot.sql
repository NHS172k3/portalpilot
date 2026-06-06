create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.company_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  legal_name text,
  trading_name text,
  registration_id text,
  address text,
  industry_summary text,
  primary_contact_email text,
  primary_contact_phone text,
  filing_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.people (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.company_profiles(id) on delete cascade,
  full_name text not null,
  role text not null,
  email text,
  sensitivity text not null default 'personal' check (sensitivity in ('public', 'business', 'personal', 'confidential')),
  created_at timestamptz not null default now()
);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.company_profiles(id) on delete cascade,
  file_name text not null,
  mime_type text,
  retention_policy text not null default 'short_lived' check (retention_policy in ('short_lived', 'retained', 'delete_after_processing')),
  status text not null default 'uploaded' check (status in ('uploaded', 'processing', 'processed', 'processed_with_fallback', 'extracted', 'failed')),
  created_at timestamptz not null default now()
);

create table public.extracted_facts (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete cascade,
  label text not null,
  value text,
  source_type text not null check (source_type in ('business_profile', 'filing_context', 'uploaded_document', 'official_source', 'agent_inference')),
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  sensitivity text not null check (sensitivity in ('public', 'business', 'personal', 'confidential')),
  evidence_note text,
  created_at timestamptz not null default now()
);

create table public.filings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  profile_id uuid references public.company_profiles(id) on delete set null,
  name text not null,
  jurisdiction text not null,
  agency text not null,
  status text not null check (status in ('not_started', 'in_progress', 'needs_you', 'ready_for_review', 'completed', 'blocked', 'archived')),
  progress int not null default 0 check (progress >= 0 and progress <= 100),
  last_agent_action text not null default 'Created',
  deadline text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid not null references public.filings(id) on delete cascade,
  state text not null check (state in ('idle', 'researching', 'filling', 'paused_missing_info', 'paused_human_wall', 'blocked', 'done')),
  model text,
  trace_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.agent_requests (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid not null references public.filings(id) on delete cascade,
  request_type text not null check (request_type in ('data_request', 'human_wall_handoff', 'confirmation', 'warning')),
  title text not null,
  prompt text not null,
  why_needed text not null,
  proposed_answer text,
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),
  source_type text check (source_type is null or source_type in ('business_profile', 'filing_context', 'uploaded_document', 'official_source', 'agent_inference')),
  portal_url text,
  status text not null default 'open' check (status in ('open', 'answered', 'cleared', 'cancelled')),
  answer text,
  answered_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.regulatory_recommendations (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid not null references public.filings(id) on delete cascade,
  reason text not null,
  prerequisites jsonb not null default '[]'::jsonb,
  fee_expectation text,
  warnings jsonb not null default '[]'::jsonb,
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table public.readiness_checklist_items (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid not null references public.filings(id) on delete cascade,
  label text not null,
  status text not null check (status in ('filled', 'left_blank', 'needs_review', 'blocked', 'user_required', 'not_applicable')),
  reason text not null,
  created_at timestamptz not null default now()
);

create table public.field_confidence_records (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid not null references public.filings(id) on delete cascade,
  portal_section text not null,
  field_label text not null,
  proposed_value text,
  source_type text not null check (source_type in ('business_profile', 'filing_context', 'uploaded_document', 'official_source', 'agent_inference')),
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  sensitivity text not null check (sensitivity in ('public', 'business', 'personal', 'confidential')),
  status text not null check (status in ('filled', 'left_blank', 'needs_review', 'blocked', 'user_required', 'not_applicable')),
  reason text not null,
  created_at timestamptz not null default now()
);

create table public.activity_events (
  id uuid primary key default gen_random_uuid(),
  filing_id uuid references public.filings(id) on delete cascade,
  event_type text not null,
  summary text not null,
  detail text,
  created_at timestamptz not null default now()
);

create table public.autonomy_policies (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null default 'Default policy',
  auto_discover boolean not null default true,
  auto_fill_high_confidence_business_fields boolean not null default true,
  confirm_medium_confidence boolean not null default true,
  confidence_threshold numeric not null default 0.8 check (confidence_threshold >= 0 and confidence_threshold <= 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index company_profiles_user_id_idx on public.company_profiles(user_id);
create index people_profile_id_idx on public.people(profile_id);
create index documents_profile_id_idx on public.documents(profile_id);
create index extracted_facts_document_id_idx on public.extracted_facts(document_id);
create index filings_user_id_idx on public.filings(user_id);
create index filings_status_idx on public.filings(status);
create index agent_runs_filing_id_idx on public.agent_runs(filing_id);
create index agent_requests_filing_id_status_idx on public.agent_requests(filing_id, status);
create index regulatory_recommendations_filing_id_idx on public.regulatory_recommendations(filing_id);
create index readiness_checklist_items_filing_id_idx on public.readiness_checklist_items(filing_id);
create index field_confidence_records_filing_id_idx on public.field_confidence_records(filing_id);
create index activity_events_filing_id_created_at_idx on public.activity_events(filing_id, created_at desc);
create index autonomy_policies_user_id_idx on public.autonomy_policies(user_id);

create trigger company_profiles_set_updated_at
before update on public.company_profiles
for each row execute function public.set_updated_at();

create trigger filings_set_updated_at
before update on public.filings
for each row execute function public.set_updated_at();

create trigger agent_runs_set_updated_at
before update on public.agent_runs
for each row execute function public.set_updated_at();

create trigger agent_requests_set_updated_at
before update on public.agent_requests
for each row execute function public.set_updated_at();

create trigger autonomy_policies_set_updated_at
before update on public.autonomy_policies
for each row execute function public.set_updated_at();

alter table public.company_profiles enable row level security;
alter table public.people enable row level security;
alter table public.documents enable row level security;
alter table public.extracted_facts enable row level security;
alter table public.filings enable row level security;
alter table public.agent_runs enable row level security;
alter table public.agent_requests enable row level security;
alter table public.regulatory_recommendations enable row level security;
alter table public.readiness_checklist_items enable row level security;
alter table public.field_confidence_records enable row level security;
alter table public.activity_events enable row level security;
alter table public.autonomy_policies enable row level security;

create policy "Users can manage their company profiles"
on public.company_profiles
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can manage people for their profiles"
on public.people
for all
to authenticated
using (
  exists (
    select 1 from public.company_profiles
    where company_profiles.id = people.profile_id
      and company_profiles.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.company_profiles
    where company_profiles.id = people.profile_id
      and company_profiles.user_id = auth.uid()
  )
);

create policy "Users can manage documents for their profiles"
on public.documents
for all
to authenticated
using (
  exists (
    select 1 from public.company_profiles
    where company_profiles.id = documents.profile_id
      and company_profiles.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.company_profiles
    where company_profiles.id = documents.profile_id
      and company_profiles.user_id = auth.uid()
  )
);

create policy "Users can manage extracted facts for their documents"
on public.extracted_facts
for all
to authenticated
using (
  exists (
    select 1
    from public.documents
    left join public.company_profiles on company_profiles.id = documents.profile_id
    where documents.id = extracted_facts.document_id
      and company_profiles.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.documents
    left join public.company_profiles on company_profiles.id = documents.profile_id
    where documents.id = extracted_facts.document_id
      and company_profiles.user_id = auth.uid()
  )
);

create policy "Users can manage their filings"
on public.filings
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can manage agent runs for their filings"
on public.agent_runs
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = agent_runs.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = agent_runs.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage requests for their filings"
on public.agent_requests
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = agent_requests.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = agent_requests.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage recommendations for their filings"
on public.regulatory_recommendations
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = regulatory_recommendations.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = regulatory_recommendations.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage checklist items for their filings"
on public.readiness_checklist_items
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = readiness_checklist_items.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = readiness_checklist_items.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage confidence records for their filings"
on public.field_confidence_records
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = field_confidence_records.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = field_confidence_records.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage activity for their filings"
on public.activity_events
for all
to authenticated
using (
  exists (
    select 1 from public.filings
    where filings.id = activity_events.filing_id
      and filings.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.filings
    where filings.id = activity_events.filing_id
      and filings.user_id = auth.uid()
  )
);

create policy "Users can manage their autonomy policies"
on public.autonomy_policies
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

comment on table public.company_profiles is 'MVP uses server-side service-role access with nullable user_id. When Supabase Auth is enabled, user_id drives auth.uid()-scoped RLS.';
comment on table public.filings is 'PortalPilot filing lifecycle board. MVP is single-tenant through FastAPI service-role access; auth-ready RLS is scoped by nullable user_id.';
comment on table public.agent_requests is 'Action Center requests. Human-only walls and missing information are represented here, never hidden agent failures.';
comment on table public.field_confidence_records is 'Per-field confidence, source attribution, status, and sensitivity for agent-produced values.';
