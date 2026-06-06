-- =============================================================================
-- seed_bizfile_local_company.sql
-- PortalPilot demo seed: BizFile "Register a new local company (Pte Ltd)"
--
-- THIS IS THE ONLY PLACE FORM-SPECIFIC DATA MAY LIVE (per AGENTS.md §0).
-- The engine must NOT reference any identifier in this file by name.
-- A new government form = a new seed file like this one, with zero engine changes.
--
-- Source: ACRA BizFile public dummy-data walkthrough, "Register new business entity"
--         -> Local Company, Exempt Private Company Limited by Shares.
--         Captured 6 Jun 2026. RE-VERIFY field labels against the live portal
--         before the final demo; portal labels drift.
--
-- Field provenance model (the important part):
--   'agent_fillable' : free business data the agent may fill from profile/docs.
--   'retrieved'      : system pulls it (name-app data, SSIC, NRIC particulars,
--                      postal-code address). Agent must NOT invent these; it
--                      triggers the portal's own "Retrieve" action or leaves blank.
--   'human_only'     : identity / declaration / beneficial-ownership / payment.
--                      Agent must NEVER fill or click. Executor-enforced.
--
-- sensitivity: public | business | personal | confidential
-- =============================================================================

-- ---- form_definition ---------------------------------------------------------
insert into form_definitions (id, jurisdiction, agency, name, portal_url, notes)
values (
  'fd_bizfile_local_company',
  'SG',
  'ACRA',
  'Register a new local company (Private Limited by Shares)',
  'https://www.bizfile.gov.sg',  -- real eService is Corppass-gated; mirror renders from this definition
  'Filed after business name application is approved. 7-step wizard. Login (Corppass), '
  || 'the Step 6 statutory declaration checkbox, endorsement routing, and Step 7 payment '
  || 'are all human-only walls. ~S$300 incorporation fee. Several sections are repeatable. '
  || 'Many fields are system-retrieved, not typed.'
);

-- Helper note for whoever maintains this:
-- provenance + human_only together drive agent behavior. human_only=true is the
-- executor "never touch" flag. retrieved fields are human_only=false but the agent
-- should use the portal's Retrieve button rather than typing a value.

-- =============================================================================
-- STEP 1 — Entity information
-- =============================================================================
insert into form_fields
  (form_definition_id, key, label, section, "type", options, sensitivity, required, human_only, provenance, conditional_on, notes)
values
-- Pre-filled from the approved name application (read-only / retrieved)
('fd_bizfile_local_company','entity_name','Entity name','Entity information','text',null,'public',true,false,'retrieved',null,'Prefilled from name application via transaction number.'),
('fd_bizfile_local_company','entity_type','Entity type','Entity information','text',null,'public',true,false,'retrieved',null,'e.g. Local Company.'),
('fd_bizfile_local_company','company_type','Company type','Entity information','text',null,'public',true,false,'retrieved',null,'e.g. Exempt Private Company Limited by Shares.'),
('fd_bizfile_local_company','primary_business_activity','Primary business activity (SSIC)','Entity information','text',null,'public',true,false,'retrieved',null,'SSIC code + description, prefilled from name application.'),
('fd_bizfile_local_company','name_app_txn_number','Name application transaction number','Entity information','select',null,'business',true,false,'agent_fillable',null,'Selected at entry; drives Retrieve information. Demo value e.g. T250000640.'),
-- Financial year end
('fd_bizfile_local_company','fye_date','Financial year end','Entity information','date',null,'business',true,false,'agent_fillable',null,'e.g. 31 Mar 2025.'),
('fd_bizfile_local_company','fye_period','Financial year period','Entity information','radio','["12 months","52 weeks accounting period"]','business',true,false,'agent_fillable',null,null),
-- Registered office address
('fd_bizfile_local_company','office_postal_code','Registered office postal code','Entity information','text',null,'business',true,false,'agent_fillable',null,'Triggers Retrieve address.'),
('fd_bizfile_local_company','office_street','Registered office street address','Entity information','text',null,'business',true,false,'retrieved','office_postal_code','Auto-filled from postal code lookup.'),
('fd_bizfile_local_company','office_level','Level','Entity information','text',null,'business',false,false,'agent_fillable',null,null),
('fd_bizfile_local_company','office_unit','Unit','Entity information','text',null,'business',false,false,'agent_fillable',null,null),
('fd_bizfile_local_company','office_no_level_unit','Address doesn''t have level and unit','Entity information','checkbox',null,'business',false,false,'agent_fillable',null,null),
-- Office hours
('fd_bizfile_local_company','working_hours','Working hours','Entity information','radio','["At least 3 hours but less than 5 hours during ordinary business hours on each business day.","At least 5 hours during ordinary business hours on each business day."]','business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','number_of_working_hours','Number of working hours','Entity information','select','["3","4","5","6","7","8"]','business',true,false,'agent_fillable',null,'Option list approximate; verify.'),
-- Entity email
('fd_bizfile_local_company','entity_email','Entity email address','Entity information','text',null,'business',true,false,'agent_fillable',null,'Receives govt notifications.'),

-- =============================================================================
-- STEP 2 — Position holder information (REPEATABLE: one block per holder)
-- =============================================================================
('fd_bizfile_local_company','ph_category','Category','Position holders','radio','["Individual","Corporate"]','business',true,false,'agent_fillable',null,'Repeatable section. Drives individual vs corporate branch.'),
('fd_bizfile_local_company','ph_position_held','Position held','Position holders','multi_select','["Chief Executive Officer","Director","Managing Director","Secretary","Shareholder","Member"]','business',true,false,'agent_fillable',null,'Multi-select.'),
('fd_bizfile_local_company','ph_amount_guaranteed','Amount guaranteed','Position holders','number',null,'business',false,false,'agent_fillable','ph_position_held=Member','Currency + amount; only for company-limited-by-guarantee Member.'),
-- Individual holder identity (RETRIEVED from govt / human-owned)
('fd_bizfile_local_company','ph_id_type','Identification type','Position holders','select','["NRIC (Citizen)","NRIC (PR)","FIN","Passport"]','personal',true,true,'human_only','ph_category=Individual','Identity. Particulars retrieved from govt agencies; not agent-entered.'),
('fd_bizfile_local_company','ph_id_number','Identification number','Position holders','text',null,'confidential',true,true,'human_only','ph_category=Individual','NRIC/FIN. Never agent-filled.'),
('fd_bizfile_local_company','ph_name','Name (as per NRIC/Identification document)','Position holders','text',null,'personal',true,true,'human_only','ph_category=Individual','Retrieved via Retrieve information; identity.'),
('fd_bizfile_local_company','ph_dob','Date of birth','Position holders','date',null,'personal',true,true,'human_only','ph_category=Individual','Retrieved/identity.'),
('fd_bizfile_local_company','ph_res_address_type','Residential address type','Position holders','radio','["Local","Foreign"]','personal',true,true,'human_only','ph_category=Individual',null),
('fd_bizfile_local_company','ph_res_postal_code','Residential postal code','Position holders','text',null,'personal',true,true,'human_only','ph_category=Individual','Identity-linked; human-owned.'),
('fd_bizfile_local_company','ph_res_level','Residential level','Position holders','text',null,'personal',false,true,'human_only','ph_category=Individual',null),
('fd_bizfile_local_company','ph_res_unit','Residential unit','Position holders','text',null,'personal',false,true,'human_only','ph_category=Individual',null),
('fd_bizfile_local_company','ph_contact_email','Contact email address','Position holders','text',null,'personal',true,false,'agent_fillable','ph_category=Individual','Contact info; agent may fill from profile if known.'),
('fd_bizfile_local_company','ph_contact_country_code','Contact country code','Position holders','select','["65"]','personal',true,false,'agent_fillable','ph_category=Individual',null),
('fd_bizfile_local_company','ph_contact_mobile','Contact mobile number','Position holders','text',null,'personal',true,false,'agent_fillable','ph_category=Individual',null),
-- Corporate holder branch (RETRIEVED via UEN / entity-name search)
('fd_bizfile_local_company','ph_corp_registered_locally','Is the corporate position holder registered locally?','Position holders','radio','["Yes","No"]','business',true,false,'agent_fillable','ph_category=Corporate',null),
('fd_bizfile_local_company','ph_corp_retrieve_by','Retrieve information by','Position holders','radio','["By UEN","By entity name"]','business',true,false,'agent_fillable','ph_category=Corporate',null),
('fd_bizfile_local_company','ph_corp_identifier','Corporate UEN or entity name','Position holders','text',null,'business',true,false,'agent_fillable','ph_category=Corporate','Triggers Search; UEN/name/address returned by system.'),
-- Section-level declaration
('fd_bizfile_local_company','more_than_50_members','Does the company have more than 50 members?','Position holders','radio','["Yes","No"]','business',true,false,'agent_fillable',null,'EPC determination.'),

-- Nominee director / shareholder declaration (BENEFICIAL OWNERSHIP — human-only)
('fd_bizfile_local_company','nominee_exempt','Will the entity be exempted from the register of nominee directors and shareholders requirements from incorporation?','Position holders','radio','["Yes","No"]','confidential',true,true,'human_only',null,'Beneficial-ownership declaration. Agent must not answer.'),
('fd_bizfile_local_company','has_nominees','Does the company have any nominee directors or nominee shareholders?','Position holders','radio','["Yes","No"]','confidential',true,true,'human_only',null,'Beneficial-ownership declaration. Agent must not answer.'),
('fd_bizfile_local_company','nominee_details','Nominee director/shareholder + nominator particulars','Position holders','text',null,'confidential',false,true,'human_only','has_nominees=Yes','Repeatable nominee+nominator identity block; human-only.'),

-- Register of Registrable Controllers (RORC) (BENEFICIAL OWNERSHIP — human-only)
('fd_bizfile_local_company','rorc_exempt','Will the entity be exempted from the Register of Registrable Controllers (RORC) requirements upon incorporation?','Position holders','radio','["Yes","No"]','confidential',true,true,'human_only',null,'Beneficial-ownership declaration. Agent must not answer.'),
('fd_bizfile_local_company','rorc_can_identify','Is the entity able to identify registrable controller(s) under the Companies Act 1967 / LLP Act 2005?','Position holders','radio','["Yes","No"]','confidential',true,true,'human_only',null,null),
('fd_bizfile_local_company','rorc_controllers','Registrable controller particulars (individual/corporate)','Position holders','text',null,'confidential',false,true,'human_only','rorc_can_identify=Yes','Repeatable controller identity block; human-only.'),

-- =============================================================================
-- STEP 3 — Share capital (REPEATABLE per currency / class)
-- =============================================================================
('fd_bizfile_local_company','sc_currency','Currency','Share capital','select','["Singapore dollar","US dollar","Euro"]','business',true,false,'agent_fillable',null,'Repeatable currency block. Option list abbreviated; full ISO list in portal.'),
('fd_bizfile_local_company','sc_shares_payable','Shares payable','Share capital','radio','["All in cash","All otherwise than in cash","No consideration","Partially in cash and otherwise than in cash"]','business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sc_class','Class of shares','Share capital','select','["Ordinary","Preference","Others"]','business',true,false,'agent_fillable',null,'Repeatable class; supports sub-class.'),
('fd_bizfile_local_company','sc_number_of_shares','Number of shares','Share capital','number',null,'business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sc_issued_capital','Issued share capital','Share capital','number',null,'business',true,false,'agent_fillable',null,'Currency amount.'),
('fd_bizfile_local_company','sc_paidup_capital','Paid-up share capital','Share capital','number',null,'business',true,false,'agent_fillable',null,'Enter 0 if not applicable.'),

-- =============================================================================
-- STEP 4 — Share allotment (REPEATABLE: individual + group)
-- =============================================================================
('fd_bizfile_local_company','sa_shareholder','Shareholder','Share allotment','select',null,'business',true,false,'agent_fillable',null,'Dropdown of position holders added in Step 2.'),
('fd_bizfile_local_company','sa_currency','Currency','Share allotment','select','["Singapore dollar","US dollar","Euro"]','business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sa_class','Class of shares','Share allotment','select','["Ordinary","Preference","Others"]','business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sa_number_of_shares','Number of shares','Share allotment','number',null,'business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sa_paidup_capital','Paid-up share capital','Share allotment','number',null,'business',true,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sa_held_in_trust','Are shares held in trust? Provide name of trust?','Share allotment','radio','["Yes","No"]','business',false,false,'agent_fillable',null,null),
('fd_bizfile_local_company','sa_trust_name','Name of trust','Share allotment','text',null,'business',false,false,'agent_fillable','sa_held_in_trust=Yes',null),
('fd_bizfile_local_company','sa_group_name','Group name','Share allotment','text',null,'business',false,false,'agent_fillable',null,'Group share variant.'),
('fd_bizfile_local_company','sa_group_shareholders','Group shareholder(s)','Share allotment','multi_select',null,'business',false,false,'agent_fillable',null,'Multi-select of position holders.'),

-- =============================================================================
-- STEP 5 — Constitution
-- =============================================================================
('fd_bizfile_local_company','con_type','Constitution type','Constitution','radio','["Attach customised constitution","Use model constitution"]','business',true,false,'agent_fillable',null,'Agent may set the choice if user-directed; upload is human-confirmed.'),
('fd_bizfile_local_company','con_model_type','Model constitution type','Constitution','radio','["Adopt the constitution in force at the time of adoption","Adopt the constitution which may be in force for time to time"]','business',false,false,'agent_fillable','con_type=Use model constitution',null),
('fd_bizfile_local_company','con_upload','Attach customised constitution (file)','Constitution','upload',null,'business',false,true,'human_only','con_type=Attach customised constitution','File upload (JPG/PNG/PDF/DOCX/XLSX/PPTX, max 2MB, 1 file). Upload only after explicit user confirmation.'),

-- =============================================================================
-- STEP 6 — Review and confirm  ==> THE STATUTORY DECLARATION WALL
-- =============================================================================
('fd_bizfile_local_company','review_summary','Review of all entered information','Review and confirm','text',null,'business',false,false,'retrieved',null,'Read-only summary. Note: routed to position holders for endorsement after submission.'),
('fd_bizfile_local_company','statutory_declaration','I confirm the following declarations apply where applicable (statutory declaration)','Review and confirm','checkbox',null,'confidential',true,true,'human_only',null,'HARD STOP. Legally-binding attestation (personal responsibility, consent, not undischarged bankrupt, etc). Executor must block any attempt to check this.'),

-- =============================================================================
-- STEP 7 — Payment  ==> THE PAYMENT WALL
-- =============================================================================
('fd_bizfile_local_company','special_uen','Do you wish to select a Special UEN?','Payment','radio','["Yes","No"]','business',false,false,'agent_fillable',null,'Optional paid Special UEN. Agent may set No.'),
('fd_bizfile_local_company','payment_method','Select payment method','Payment','radio','["Saved card(s)","Other methods"]','confidential',true,true,'human_only',null,'HARD STOP. Payment. ~S$300 incl GST.'),
('fd_bizfile_local_company','make_payment','Make payment','Payment','button',null,'confidential',true,true,'human_only',null,'HARD STOP. Final binding action. Executor must block.');

-- =============================================================================
-- Demo business profile (paired with the form above)
-- =============================================================================
insert into business_profiles (id, name)
values ('bp_chocoero', 'CHOCOERO PTE. LTD. (demo founder profile)');

insert into attributes (business_profile_id, key, label, value, sensitivity, notes)
values
('bp_chocoero','entity_name','Entity name','CHOCOERO PTE. LTD.','public',null),
('bp_chocoero','name_app_txn_number','Name application transaction number','T250000640','business','Pretend name already approved.'),
('bp_chocoero','primary_business_activity','Primary business activity (SSIC)','78101 | IT manpower contracting services','public',null),
('bp_chocoero','fye_date','Financial year end','31 Mar 2025','business',null),
('bp_chocoero','fye_period','Financial year period','12 months','business',null),
('bp_chocoero','office_postal_code','Registered office postal code','117371','business',null),
('bp_chocoero','office_street','Registered office street','70 PASIR PANJANG ROAD, MAPLETREE BUSINESS CITY','business',null),
('bp_chocoero','office_level','Office level','12','business',null),
('bp_chocoero','office_unit','Office unit','2','business',null),
('bp_chocoero','working_hours','Working hours','At least 3 hours but less than 5 hours during ordinary business hours on each business day.','business',null),
('bp_chocoero','number_of_working_hours','Number of working hours','3','business',null),
('bp_chocoero','entity_email','Entity email address','general@chocoero.com.sg','business',null),
('bp_chocoero','ph_category','Category','Individual','business','Demo holder is an individual.'),
('bp_chocoero','ph_position_held','Position held','Director','business','Demo operational role; legal identity fields remain human-only.'),
('bp_chocoero','ph_contact_email','Contact email address','founder@chocoero.com.sg','personal',null),
('bp_chocoero','ph_contact_country_code','Contact country code','65','personal',null),
('bp_chocoero','ph_contact_mobile','Contact mobile number','81234567','personal',null),
('bp_chocoero','more_than_50_members','Does the company have more than 50 members?','No','business',null),
('bp_chocoero','share_currency','Share currency','Singapore dollar','business',null),
('bp_chocoero','sc_shares_payable','Shares payable','All in cash','business',null),
('bp_chocoero','share_class','Class of shares','Ordinary','business',null),
('bp_chocoero','share_number','Number of shares','100','business',null),
('bp_chocoero','share_issued','Issued share capital','100','business',null),
('bp_chocoero','share_paidup','Paid-up share capital','100','business',null),
('bp_chocoero','sa_shareholder','Shareholder','Director','business','Dropdown value from the position-holder section.'),
('bp_chocoero','constitution_type','Constitution type','Use model constitution','business',null),
('bp_chocoero','constitution_model_type','Model constitution type','Adopt the constitution which may be in force for time to time','business',null),
('bp_chocoero','special_uen','Do you wish to select a Special UEN?','No','business',null),
-- Director identity intentionally NOT included as agent-usable:
-- this is human_only/retrieved on the form, so the agent should leave it blank
-- and route to Action Required. Including a dummy here would tempt the agent to fill it.
('bp_chocoero','director_name_DO_NOT_AUTOFILL','(Director identity — human/retrieved only)','Provided by user at the portal via Singpass; agent must not fill','confidential','Marker only; demonstrates leave-blank behavior.');

-- =============================================================================
-- Demo queue: incorporation active + auto-suggested follow-on obligations
-- (follow-ons are suggestions only; no form_definition needed for the demo)
-- =============================================================================
insert into filing_tasks (id, business_profile_id, form_definition_id, status, origin, notes)
values
('ft_incorp','bp_chocoero','fd_bizfile_local_company','not_started','auto_suggested','Hero task: incorporate the company.'),
('ft_corppass','bp_chocoero',null,'not_started','auto_suggested','Suggested follow-on: set up Corppass (digital identity for govt agencies).'),
('ft_gst','bp_chocoero',null,'not_started','auto_suggested','Suggested follow-on: evaluate GST registration (mandatory above ~S$1M turnover).'),
('ft_licence','bp_chocoero',null,'not_started','auto_suggested','Suggested follow-on: check sector licences via GoBusiness.');
