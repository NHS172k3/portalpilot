alter table public.field_confidence_records
  add column if not exists field_key text,
  add column if not exists selector text,
  add column if not exists input_kind text;

alter table public.agent_requests
  add column if not exists field_key text;

comment on column public.field_confidence_records.field_key is 'Stable normalized key for matching an observed form field to an Action Center answer.';
comment on column public.field_confidence_records.selector is 'Best-effort safe selector for the observed field; used only for non-final field preparation.';
comment on column public.field_confidence_records.input_kind is 'Observed input kind such as input, textarea, select, single-choice group, or multi-choice group.';
comment on column public.agent_requests.field_key is 'Observed field key this request answers, when the request is tied to a browser-observed field.';
