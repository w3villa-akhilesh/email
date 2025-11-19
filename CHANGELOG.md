# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).
---

## [2.0.12] - 2025-11-18 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/436

### Fixed
- Fixed `/resume_parser_agent_psp` endpoint to return proper 401 status code instead of 500 when LLM credentials are not found or misconfigured

---

## [2.0.11] - 2025-11-18 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/423

### Enhanced
- adk-web: Removed chat input box (textarea, attachment, microphone, and video buttons) from chat panel interface.
- Fixed company ID display (showing actual ID instead of N/A).
- Added active agent mappings count to company listing page.
- Removed "Updated By" field from listing page.
- Fixed LLM Credentials filtering to show only company-specific credentials.
- Added full CRUD operations for Agents with conditional parent agent selection.
- Implemented smart form validation based on agent type (primary/sub-agent/tool).
---

## [2.0.10] - 2025-11-17 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/434

### Enhanced
- Optimized resume parser prompt while maintaining all functionality.
- Enhanced LLM credential error handling with 403 status and user-friendly messages.
- Added detailed logging for evaluation criteria in job matching calculations.
---

## [2.0.9] - 2025-11-17 [@w3villa-yash-dubey]
---
PR : https://github.com/w3villa-com/kivo_agent/pull/433

### FIXED 
- Tag removal logic added after response
---

## [2.0.8] - 2025-11-17 [@w3villa-yash-dubey]
---
PR : https://github.com/w3villa-com/kivo_agent/pull/432

### FIXED 
- All import whatsapp formater button prompt issue fixed.
- Added whatsapp formater button in hrms agent.
---


## [2.0.7] - 2025-11-17 [@w3villa-yash-dubey]
---
PR : https://github.com/w3villa-com/kivo_agent/pull/409

### Added 
- Added a WhatsApp button formatter agent to generate custom WhatsApp buttons in responses whenever needed.
- Added a prompt update to enable all triage sub-agents and the user agent to include custom buttons when required.
---

## [2.0.6] - 2025-11-17 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/428

### Enhanced
- Replaced weightage-based evaluation with level-based system (L0-L4) and average scoring calculation.
- Implemented 4 distinct processing modes based on resume_parsing/evaluation_result flags with different response behaviors.
- Added resume_text parameter to skip resume parsing and run evaluation-only mode with synchronous response (no API update).
- Enhanced API update logic with conditional payload formats: nested evaluation_report structure for evaluations, flattened format for parsing-only.
- Added robust handling for nil/empty/invalid evaluation levels with automatic L0 fallback and normalization.
---
## [2.0.5] - 2025-11-13 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/425

### Added
-- Introduced a new script add_4_agents_only.py that allows for the safe addition of four specific agents without modifying existing data or affecting the agent_mappings table.

---
## [2.0.4] - 2025-11-13 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/424

### FIXED
-- crm_faq date issue 

---

## [2.0.3] - 2025-11-13 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/418

### Added
- **Dynamic Agent Loading for Triage Agents**: Implemented dynamic loading for agents for vedika
  - Added `attendance_agent`, `payroll_agent`, `recruiting_agent`, and `travel_expense_agent` to database seed data
  - Configured all 4 agents as children of `triage_agent` for proper routing
  - Added comprehensive agent descriptions for dynamic prompt generation

---
## [2.0.2] - 2025-11-12 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/420

### Fixed
- Replaced the call to `get_llm_engine` with `get_llm_credentials_based_on_company_id` in the `handle_vision_api` function to improve clarity and consistency in credential retrieval based on company ID and origin.
---
## [2.0.1] - 2025-11-12 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/406

### Added
Remove unused import from llm_engine.py

---
## [2.0.0] - 2025-11-12 [@w3villa-rohit-kushwaha, @w3villa-akhilesh, @w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/341

### Added

- **Multi-Tenant Agent System**
  - Implemented database-driven, company-scoped agent architecture with Redis caching.
  - Added AgentRegistryService for dynamic agent loading and discovery.
  - Refactored get_llm_engine to use company+agent mappings with Redis + env fallback.
  - Introduced Company, Agent, and AgentMapping models with new migrations and seed data.
  - Updated all major agents to use dynamic registry-based loading.
  - Centralized LLM credential caching and improved error handling/logging.

- **Tenant Architecture UI**: Introduced company-based tenant management in the Admin Debugger Panel
  - Manage Agent Configurations per company
  - Configure LLM Credentials with company-level isolation
  - Enhanced data segregation and multi-tenancy support

- **API Key Management**: Implemented comprehensive Agent API key authentication
  - Generate new API keys for client applications
  - View and manage existing keys with pagination
  - Revoke keys with secure deletion

---
## [1.8.0] - 2025-11-13 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/414

### Enhaced
- Enhanced pm board story agent to give list of projects, in face of any confusion.

---

## [1.7.21] - 2025-11-11 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/413

### Enhaced
- crm faq prompt fixed

---

## [1.7.20] - 2025-11-11 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/406

### Added
Added a UserFeedback system to record thumbs up/down with session and message details, integrated feedback handling in WebSocket and chat history, ensured feedback deletion with events, and added a migration for the user_feedback table.

---

## [1.7.19] - 2025-11-08 [@w3villa-pranav-gupta]

PR: http://github.com/w3villa-com/kivo_agent/pull/410

### Enhaced
- crm faq date awareness with date and day calculation rules 

---

## [1.7.18] - 2025-11-06 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/407

### Enhaced
- crm faq prompt 

---
## [1.7.17] - 2025-11-06 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/404

### Added
- Added an “Open in ADK” eye button to view any session in the ADK Web UI.
- Backend adapter ensures all events display clearly (including tool calls/transfers).

---


## [1.7.16] - 2025-11-06 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/398

### Fix
- {actual_link} bug fixed in crm_instructions.txt 

---

## [1.7.15] - 2025-11-05 [@w3villa-yash-dubey]
PR : https://github.com/w3villa-com/kivo_agent/pull/401

## chnaged
-- The custom button logic has been commented out and rolled back for now, as it depends on CRM which is not deployable at the moment.

---

## [1.7.14] - 2025-11-05 [@w3villa-rohit]

PR: https://github.com/w3villa-com/kivo_agent/pull/399

### Added
- **Resume Parser Experience Range Support**: Added `min_experience` and `max_experience` parameters to resume parser agent for enhanced job matching accuracy.
  - Added optional `min_experience` and `max_experience` fields to `ResumeParserPayload` schema
  - Updated `/resume_parser_agent_psp` endpoint to accept and process experience range parameters
  - Enhanced prompt with comprehensive instructions for experience-based matching and scoring
  - Experience requirements are now properly factored into job matching percentage calculation
  - Added detailed reasoning in job matching breakdown for experience alignment/misalignment
  - Backward compatible: works with or without experience parameters
---

## [1.7.13] - 2025-11-05 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/397

### Fix
- updated kivo agent prompt to behave agent according to the instruction recieved by user and fix project_id not found issue.

---

## [1.7.12] - 2025-11-05 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/396

### Added
- Added follow up instructions for pm_board_story agent.

---

## [1.7.11] - 2025-11-04 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/395

### Enhancement
- crm faq bot prompt enhanced to return single meeting link and better response

---

## [1.7.10] - 2025-11-04 [@w3villa-yash-dubey]

PR: https://github.com/w3villa-com/kivo_agent/pull/394

### Add
Enhancement – WhatsApp Interaction Handling : 

- Added new processing logic (process_whatsapp_response, remove_tags) for interactive button formatting.
- Updated invoke_triage_agent to use the new formatter.
- Included WHATSAPP_BUTTON_FORMATTER_PROMPT in agent instructions.
- Removed deprecated whatsapp_actions.py.

---

## [1.7.9] - 2025-11-04 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/393

### Fix
- updated HRMS prompt to do not call 'name_suggestion_agent' if recieved data from 'get_employee_details_with_name' tool.

---

## [1.7.9] - 2025-11-05 [@w3villa-rohit]

PR: https://github.com/w3villa-com/kivo_agent/pull/402

### Added
- **Resume Parser Experience Range Support**: Added support for `min_experience` and `max_experience` fields in `JobProfileDetails` schema for enhanced job matching accuracy.
  - Updated `JobProfileDetails` to accept both `min_experience`/`max_experience` and legacy `min_year`/`max_year` field names
  - Added helper methods `get_min_experience()` and `get_max_experience()` to prioritize new field names
  - Experience values are now extracted from `job_profile_details` and included in LLM context for job matching calculation
  - Updated resume parser agent to properly handle experience range in job profile context
  - Backward compatible: supports both new and legacy field naming conventions

### Enhanced
- **Job Matching Context**: Improved job matching calculation by properly extracting and using experience requirements from `job_profile_details` object in resume parser endpoint

---

## [1.7.8] - 2025-10-31 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/392

### Hot Fix
- Changed the actions column in EventBackup from Text to LargeBinary to store binary pickled data.

---

## [1.7.7] - 2025-10-31 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/360

### Enhanced
- **Resume Summary Generation**: Fixed resume parser to generate original summaries instead of copying existing text from resumes.
- **Resume Parser Security**: Added prompt injection protection to prevent malicious instructions in resume content from manipulating scoring or AI behavior.

### Removed
- **Resume Image Scanning**: Removed image-based resume processing feature. Resume parsing now relies solely on OCR text extraction for improved performance and consistency.
---

## [1.7.6] - 2025-10-31 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/390

### Improved 
- Add Database Transactions while events purge
- Removed Admin Panel–related Code
- Code Readability is maintained 

---

## [1.7.5] - 2025-10-30 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/388

### Changed 
- Improved periodic cleanup task logging by consolidating output into a clear, formatted log message.

---

## [1.7.4] - 2025-10-29 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/354

- Introduced an event backup system that securely stores deleted conversation events to prevent data loss, and enabled automated periodic cleanup of old session data.
- Enhanced session cleanup by switching to user turn-based retention and running cleanup tasks non-blockingly in the background, supporting both instant and scheduled cleanups.
- Fixed issues with data serialization, ensured database schemas match for backups, and resolved event loop conflicts for robust and reliable operation.


---

## [1.7.3] - 2025-10-29 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/382

###Fixed 
- Update date formatting in HRMS, Triage, and Leave agents to include the day of the week. Remove redundant session_id parameter from collect_leave_details function and retrieve it from tool context instead.

---
## [1.7.2] - 2025-10-29 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/383

### Fixed
- Added handover instructions in calling agent for proper handling.
---

## [1.7.1] - 2025-10-28 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/380

### Enhanced
- CRM FAQ fucntionality to respond in more dynamic way

---

## [1.7.0] - 2025-10-28 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/378

### Fixed
- Tried to fix story agent url missing issue. Added instructions.
- Added follow up methods to read comments.
---
## [1.6.4] - 2025-10-28 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/356

### Enhanced
Updated invoke_pm_board_agent to include 'origin' parameter for credential scoping, improved session management with Redis and database, and refactored payload structure to include company_id and user_id. Adjusted processing methods to accommodate new parameters and streamlined logging for better traceability.

## [1.6.3] - 2025-10-27 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/370

### Fixed
- Implement current date management in session state for triage agent. Add logic to check and update the current date in session state, ensuring accurate date handling for user sessions.
---

## [1.6.5] - 2025-10-29 [@w3villa-rohit-kushwaha]

PR: https://github.com/w3villa-com/kivo_agent/pull/385

### Changed
- **CRM Analysis Payload Structure**: Completely redesigned payload format to support new message structure with `message_type` (incoming/outgoing/template), attachments array, and user query
- **Removed Mobile Number**: Removed `current_user_mobile_number` from payload and agent flow - email signatures now only include sender name
- **Message Processing**: Updated to process messages based on new structure with separate `content` and `attachments` fields
- **Attachment Handling**: Attachments now processed via `attachment_type` (image/audio) and `attachment_url` instead of direct content

### Added
- **User Query Support**: Added optional `user_query` field as HIGHEST PRIORITY instruction for email generation
- **Contact Labels**: Added optional `label` array for contact/lead context (used for intent understanding only, not in email content)
- **Priority-Based Context Building**: Implemented hierarchical context structure: 1) User Query (highest), 2) Message History, 3) Contact Labels (lowest)
- **Intelligent Subject Generation**: Updated prompt to support AI-driven, context-aware subject line generation instead of hard-coded patterns

### Enhanced
- **CRM-Focused Prompt**: Rewrote agent prompt emphasizing CRM-specific business communications (77 lines, down from 150+)
- **Response Sanitization**: Added multi-layer JSON sanitization to handle markdown code blocks and nested JSON structures
- **Context Structure**: Messages now clearly separated with visual markers and priority labels for better AI understanding
- **Logging**: Added comprehensive logging for new payload fields (user_query, labels) and context building process

### Fixed
- **JSON Code Block Issue**: Implemented sanitization to remove ```json``` wrappers and extract nested JSON from AI responses
- **Generic Subject Lines**: Updated prompt with strict rules against generic subjects, enforcing context-aware generation

---

## [1.6.4] - 2025-10-28 [@w3villa-rohit-kushwaha]

PR: https://github.com/w3villa-com/kivo_agent/pull/374

### Enhanced
- **CRM Analysis Endpoint - Early LLM Validation**: Added upfront validation to check LLM credentials availability before processing messages in `/invoke_crm_analysis` endpoint
- Prevents unnecessary resource consumption (audio transcription, image processing) when LLM credentials are not configured
- Returns clear HTTP 400 error with actionable message directing users to configure credentials in admin panel
- Improved logging for LLM credentials validation process

### Fixed
- **Fail-Fast Mechanism**: Request now fails immediately if LLM credentials are missing instead of failing after expensive multimodal message processing

---

## [1.6.3] - 2025-10-28 [@w3villa-rohit-kushwaha]

PR: https://github.com/w3villa-com/kivo_agent/pull/372

### Added
- **CRM Email Generation Endpoint**: Implemented `/invoke_crm_analysis` endpoint for professional email generation with multimodal input support (text, audio, images)
- **Multimodal Message Processing**: Added support for processing text messages, audio transcription via `extract_query_from_voice_note`, and image analysis via `handle_vision_api`
- **CRM Analysis Agent**: Created dedicated agent for generating context-aware professional emails based on generation types (reminder, greet, follow_up, thank_you, general, apology, proposal, confirmation, announcement, invitation)
- **Email Personalization**: Added support for recipient name (`full_name`) and sender details (`current_user_name`, `current_user_mobile_number`) for personalized email signatures

---

## [1.6.2] - 2025-10-27 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/368

### Added
- Added configuration to use balanced settings for agent. 
- Update assistant instructions to clarify KIVO support and refine meeting scheduling guidelines.

---

## [1.6.1] - 2025-10-25 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/365

### Fixed
- Added app_name check based on role for image handlings.

---

## [1.6.0] - 2025-10-25 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/364

### Added
- Pm board story agent can now create task, milestone, epic.
- Also added support for multiple images.

---

## [1.5.2] - 2025-10-25 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/363

### Changed / Enhanced
- **HRMS Agent**: Integrated name suggestion agent in HRMS to prevent random name generation by AI and updated prompt handling rules to improve name matching and user interaction 


## [1.5.1] - 2025-10-24 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/361

### Enhanced
- **CRM FAQ Agent**: Enhanced prompt for CRM FAQ agent for HRMS and ATS reponses.
- Update CRM FAQ agent connection logic to include agent type parameter

---

## [1.5.0] - 2025-10-22 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/357

### Added
- Added feature: Now uploaded images can be attached while creating stories.

---

### Added
- Add upcoming new features here before tagging a release.

### Fixed
- List bug fixes here.
---

---
## [1.4.16] - 2025-10-23 [@w3villa-rohit-kushwaha]

PR: https://github.com/w3villa-com/kivo_agent/pull/358

### Added
- **Network Activity Logging System**: Implemented comprehensive network activity logging for all API endpoints capturing IP addresses, device types, browser information, operating system details, and user agent strings for security monitoring and analytics.
- **Network Activity Admin Panel**: Added dedicated "Network Activity" page in Admin Frontend with pagination, filtering capabilities (by endpoint, method, IP, device type, user, company, date range), and statistics dashboard showing total requests, unique IPs, device distribution, and browser analytics.
- **Network Details in Error Emails**: Enhanced error notification emails to automatically include network details (IP address, device type, browser, OS) for better debugging and security monitoring across all main API endpoints.

---
## [1.4.15] - 2025-10-21 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/353

### Enhanced
- Enhance CRM FAQ agent functionality: Implemented support for handling multiple concurrent queries by queuing and consolidating them.

---
## [1.4.14] - 2025-10-16 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/347

### Enhanced
- Refactored resume parser: Moved scoring logic to prompt file and enhanced job matching reasons to include detailed gap analysis with specific explanations for point deductions.

---
## [1.4.13] - 2025-10-16 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/348

### Enhanced
- Implement retry mechanism for CRM profile fetch: Added a maximum of 2 retries for fetching user profile data from the CRM, improving error handling and logging for failed attempts.

---
## [1.4.15] - 2025-10-21 [@w3villa-pranav-gupta]

PR: https://github.com/w3villa-com/kivo_agent/pull/354

### Implementation
- Added automated and manual session cleanup via session_cleanup_integration.py and session_event_cleaner.py, triggered after session history updates. Included logging and error handling for better traceability. Updated state_session_manager.py to invoke this cleanup.

---
## [1.4.12] - 2025-10-15 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/346

### Enhanced
- Enhance CRM FAQ request handling: Added support for multimodal inputs including voice notes and images. Updated CRMFAQRequest model to include input_mode and input_data_url.

---
## [1.4.11] - 2025-10-14 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/345

### Enhanced
- Refactor logging and removed unused functions: Eliminated redundant logging statements in main.py and resume_parser_agent.py, enhancing clarity. 

---
## [1.4.10] - 2025-10-13 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/343

### Enhanced
- fixed an issue where Unicode artifacts were breaking email and phone number parsing in PDF text extraction. Added clean_resume_noise() to extract_text_from_pdf() and extract_text_with_fallback() to clean up noise right after text extraction, improving parsing accuracy.

----
## [1.4.9] - 2025-10-08 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/336

### Added
- [REXNORD] Added contact info for rexnord contact agent.

---

## [1.4.8] - 2025-09-25 [@w3villa-adarsh, @w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/310

### Enhanced
- Added comprehensive real-time logging with `/api/v1/resume_parsing_logs` API integration
- Enhanced the calculation of job matching evaluation percentage based on the evaluation criteria and job profile details.

----
## [1.4.7] - 2025-10-09 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/334

### Fixes
- Session management was streamlined by returning a UserSession object for checks, auto-updating session modes, and handling missing queries gracefully.

---
## [1.4.6] - 2025-10-08 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/Kivo_mcp_servers/pull/332

### Fixes
- Added Fix for english language, unwanted deligation to dealer agent for promotional messages.
- Tried to Add Fix for  product list in appropiate format.

---


## [1.4.6] - 2025-09-10 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/337

### Fixed 
- pms agent hallucination issue fixed session_id missing in instructions.

---

## [1.4.5] - 2025-10-07 [@w3villa-rohit-kushwaha]

PR: https://github.com/w3villa-com/kivo_agent/pull/330

### Enhanced
- **Calling Agent Improvements**: Enhanced calling agent to automatically use user's phone number from profile data stored in session. Removed dependency on `my_personal_info.phone_number` and simplified tool signature to `call_by_number_or_name(callee_info, session_id)`. The caller's phone number is now automatically retrieved from session data for improved user experience.

---

## [1.4.4] - 2025-10-07 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/329

### Enhanced
- Added multiple messages edgecases for image and slack image and voice support.

---


## [1.4.3] - 2025-10-06 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/323

### Fixed
- improving multiple message handling by consolidating responses into a single, coherent output and implementing full invocation_id   support across agents. This enables precise conversation cleanup, ensures that user and assistant messages are properly paired with consistent event_ids, and maintains accurate session history. Fallbacks to event_id deletion are included for backward compatibility, resulting in more reliable and consistent conversation lifecycle management.

---

## [1.4.2] - 2025-10-06 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/327

### Fixed
- Added origin handling if '/' is missing.

---

## [1.4.1] - 2025-10-06 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/325

### Added
- Removed unused code from transcription file.

---

## [1.4.0] - 2025-10-06 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/323

### Added
- Added image and voice support from slack. Now one can send image on *slack* and query on it. Also slack can reply on voice notes.

---

## [1.3.3] - 2025-09-29 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/321

### Fixed
- Added fix for session_id in crm_traige agent.

---

## [1.3.2] - 2025-09-29 [@w3villa-sumit]

PR: https://github.com/w3villa-com/kivo_agent/pull/319

### Fixed
- Added fix for session_id in crm_traige agent.

## [1.3.1] - 2025-09-29 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/314

### Fixed
- Added fix for session_id in pms agent.

---

## [1.3.0] - 2025-09-29 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/313

### Enhanced
- [TRIAGE HRMS]: Added retry mechanism for transcription.

---
## [1.3.1] - 2025-09-29 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/313

### Enhanced
- Made API base URL configurable via BACKEND_URL environment variable

---


## [1.3.0] - 2025-09-29 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/312

### Added
- [TRIAGE HRMS]: Added feature for providing input to *hrms triage* using voice note.

---

## [1.2.1] - 2025-09-25 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/309

### Enhanced
- [REXNORD]: Added handling for out of scope queries.

----

## [1.2.0] - 2025-09-25 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/308

### Enhanced
- Added header based `session_id` in entire Triage (hrms) including its sub agents (leave, pms, story, calling, hrms).

----

## [1.1.47] - 2025-09-24 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/306

### Fixed
- Fixed author names in Session Details modal
- Fixed URL pagination navigation across all admin pages
- Fixed pagination component to display page numbers instead of only Previous/Next buttons

----


## [1.1.46] - 2025-09-23 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/303

### Enhanced
- Handled negation replies for missing info in `product_details_agent`.

----

## [1.1.45] - 2025-09-23 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/302

### Fixed
- Enhance email_receiver.py with improved error handling and reconnection logic. Implement exponential backoff for retries on connection errors, set socket timeout to prevent hanging connections, and ensure robust recovery from unexpected errors

----

## [1.1.44] - 2025-09-23 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/300

### Fixed
- [REXNORD] Fixed incorrect url. 

----

## [1.1.43] - 2025-09-23 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/299

### Fixed
- Added fixes for session_id handling and prevented llm confusion by updated instructions `crm_faq_agent`.
- Removed `session_id` input from input query and provided it in context.

----

## [1.1.42] - 2025-09-23 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/298

### Enhanced
- Fixed issue for wrong product name pickup from user query by agent.

---


## [1.1.41] - 2025-09-22 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/296


### Fixed

- Added missing `mode` parameter to fix PM Board Story Agent initialization error.

## [1.1.40] - 2025-09-22 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/297

---

### Enhanced
- Enhanced product instructions for better catalog handling.

---

## [1.1.39] - 2025-09-22 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/292

### Enhanced
- Added more clear dealer instructions for rexnord triage for better deligation.
- Fixed myql connection issue error.

---

## [1.1.38] - 2025-09-19 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/287

### Enhanced
- removed rexnord agent endpoint from main.py

---


## [1.1.37] - 2025-09-19 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/286

### Enhanced
- Updated flow for rexnord agents.

---

## [1.1.36] - 2025-09-19 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/279

### Enhanced
- Updated `crm_triage`, `crm_lead_management` to updated tool calls and deligation instructions.

### Added
- Added `greeting_instructions` to both of above agents.

---

## [1.1.35] - 2025-09-17 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/278

### Enhanced
- Updated flow for rexnord agents. improved instructions, added mcp tools and connections.

---

## [1.1.34] - 2025-09-16 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/277

### Enhanced
- Added `mode` based formatting option for handling `final_response`. Added for both `triage_agent` and `user_agent`.

---

### Removed
- List deprecated or removed functionality here.

## [1.1.33] - 2025-09-16 [@w3villa-sumit]

PR: https://github.com/w3villa-com/kivo_agent/pull/275

### Fixed 
- Fixed the bug saying missing one argument profile context not found

---


## [1.1.32] - 2025-09-16 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/274

### Enhanced
- Updated and fixed issues for crm faq agent.

---

## [1.1.31] - 2025-09-16 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/272

### Added 
- Updated `hrms_questionnaire_agent` for invoking `get_required_workflow` without title. Also made a point that for url, can invoke a diff tool.

---

## [1.1.30] - 2025-09-16 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/271

### Added 
- Updated hrms agent such that removed leave_agent from triage and passed it into hrms as sub agent.
- Adjusted prompts for stable deligation and reduced hallucinations.

---

## [1.1.29] - 2025-09-15 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/270

### Added 
- Updated `KNOWLEDGE_BASE_URL` url.

---

## [1.1.28] - 2025-09-15 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/269

### Changed / Enhanced

- Display of the last updated time on the LLM Credentials page in the Admin Panel. This enables easy tracking of when the credentials were last modified or updated.

----

## [1.1.27] - 2025-09-13 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/268

### Added 
- Added hrms questionnaire agent as a tool in hrms agent which has capability of answering flows, steps based queries on kivo hrms module.
- Added a tool `get_required_workflow` with connection to knowledge based vector db for fetching relevant info.
- Also added <Handling rules> to all sub agents to ease the deligation from one agent to another.
- Added a flow for `preloaded_context` which consists of url and title for which particular section user wants to query.
----

## [1.1.26] - 2025-09-13 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/267

### Changed / Enhanced

- Changed job_applicant_id and resume_parser_access_token as optional, added parameter validation, improved conditional background task handling with logging, and ensured image path cleanup when processing is skipped.
---

## [1.1.25] - 2025-09-13 [@w3villa-sumit]

PR: https://github.com/w3villa-com/kivo_agent/pull/266

### Changed / Enhanced

- Implemented fixes for the session delete, fetching history, searching and editing the chat message, fixed the logger issue

---

## [1.1.24] - 2025-09-12 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/265

### Changed / Enhanced

- Optimized resume_parser_agent for faster API response: now extracts only essential details (first_name, last_name, email, mobile) immediately.
- Full resume parsing runs in a background job for improved user experience.
- Added extract_essential_details_only and CONTACT_EXTRACTION_PROMPT; refactored related functions and models for compatibility.

---

## [1.1.23] - 2025-09-10 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/261

### Changed / Enhanced

- Implemented centralized error propagation in User Agent and IATS Agent. Now all errors propagate to the top level, ensuring only a single consolidated error email is triggered. Improves reliability and avoids duplicate notifications.

---

## [1.1.22] - 2025-09-09 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/203

### Changed / Enhanced

- Refactored the Transcribe Agent flow by moving transcription and summary generation logic from the MCP tool into the Transcribe Agent itself.

- Introduced a new MCP tool `send_transcription_to_crm` that is solely responsible for saving the transcription and summary of call recordings into Kivo CRM once generated by the Transcribe Agent.

---

## [1.1.22] - 2025-09-09 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/260

### Added 
- Updated profile info.


----

## [1.1.21] - 2025-09-09 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/259

### Added 
- Added rexnord image url instead of random s3 url.


----

## [1.1.20] - 2025-09-09 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/258

### Fixed
-**KPAA-760**: Fixed IMAP IDLE hanging issues for 'email_receiver.py' by adding 1-minute timeout with NOOP ping health checks and auto-reconnection on server unresponsiveness.

---

## [1.1.19] - 2025-09-08 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/257
PR: https://github.com/w3villa-com/kivo_agent/pull/256
PR: https://github.com/w3villa-com/kivo_agent/pull/255

### Added
- Updated rexnord tools response, mocked urls and updated instructions.

----

## [1.1.18] - 2025-09-05 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/252

----

## [1.1.17] - 2025-08-28 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/253

### Fixed
-**KPAA-734**: Refactor resume processing logic to enhance document handling and response parsing
    - Introduced a Pydantic model for structured response handling in job application classification.
    - Updated the classification method to utilize a new API client for improved response parsing.
    - Enhanced attachment processing to support multiple document types (PDF, DOC, DOCX) and improved error handling.
    - Streamlined logging for better traceability of processing results and errors.

---
## [1.1.16] - 2025-09-05 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/251

### Enhanced
- **LLM Credentials Enhancements**: Added a `tts_service` column (enum with options `tts_openai_key` and `tts_cartesia_key`) along with a dedicated `openai_api_key` column in the LLM Credentials table.  
- **Conditional API Key Handling**: API Responses now include TTS API keys based on the selected service:  
  - If `tts_openai_key` → returns only `openai_api_key`.  
  - If `tts_cartesia_key` → returns both `deepgram_api_key` and `cartesia_api_key`.  
- **Admin Panel Integration**: Integrated the new TTS service and API key logic into the Admin Frontend panel for credential management.

---

## [1.1.16] - 2025-09-04 [@w3villa-sumit]

PR: https://github.com/w3villa-com/kivo_agent/pull/250#issue-3382601985

### Enhanced

- Updated crm triage prompts and instructions.

---

## [1.1.15] - 2025-09-03 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/248

### Enhanced
- **LLM Credentials UI Improvements**: Improved the LLM Credentials UI in the Admin Debugger Panel. Introduced a dedicated page to view full credential details with support for activate/deactivate, edit, and delete actions.

---

##  [1.1.14]- 2025-09-03 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/245

### Added
- **KPAA-664**: Implemented Interview Scheduling Agent with supporting tools and modules. Added interview_scheduler_agent for managing scheduling, collect_interview_details tool for gathering information, and interview_context for fetching data from Elasticsearch. Updated candidate_iats_agent to initialize the scheduler, improved prompts and logging, and added resilient Elasticsearch connection handling.

---

## [1.1.13] - 2025-09-02 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/247


### Added
- Introduced a new endpoint to invoke the Rexnord triage agent, which routes queries to specific sub-agents (dealer, product, FAQ, and contact).
- Implemented sub-agents for handling dealer-related queries, product inquiries, FAQs, and contact details.
- Added necessary imports and constants for the new functionality.
- Created utility functions for session management and error handling.
- Enhanced logging for better traceability of agent interactions and errors.
- Updated prompt files for the new agents to ensure proper response formatting.
- Added local dummy tools required by sub agents.

---

##  [1.1.12]- 2025-09-01 [@w3villa-pranav]

PR: https://github.com/w3villa-com/kivo_agent/pull/246#issue-3372206121

### Enhanced
- **CRM Instructions Update**: Updated CRM agent instructions to prevent mentioning modules, tool calls, or technical internals in responses, improving user experience and maintaining professional communication standards. [@w3villa-sumit]
- Document any improvements or modifications here.

---

## [1.1.11] - 2025-09-01 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/247

### Enhanced
- **Responsive UI**: Made the LLM Credential Management System responsive for better usability across devices.
- **Timestamp Display**: Updated to show timestamps in IST format.

---

## [1.1.10] - 2025-09-01 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/244

### Added
- **API Response Update**: Extended API responses to include `cartesia_api_key` and `deepgram_api_key` along with a `success` flag property.
- **Authentication Added**: Added access token validation in Admin Frontend and Backend APIs.

---

## [1.1.9] - 2025-08-30 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/242

### Added
- **Extended LLM Credentials Support**: Added support for cartesia_api_key and deepgram_api_key fields in LLM Credentials management system. Both frontend and backend now handle these optional API keys with proper encryption, masking, and copy-to-clipboard functionality in the Admin interface.


---

## [1.1.8] - 2025-08-30 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/240

### Added
- **LLM Credentials Management System**: Complete CRUD (Create, Read, Update, Delete) interface for LLM credentials in Admin Debugger Panel. Features include encrypted API key storage, pagination, filtering by company ID and app name, and a modern React-based UI with copy-to-clipboard functionality for secure credential management.

---

## [1.1.7] - 2025-08-28 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/241


### Fixed
- Improve database connection resilience. Added explicit connection closing to prevent leaks and updated SQLAlchemy engine settings for better connection management.

---


## [1.1.6] - 2025-08-27 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/238
PR: https://github.com/w3villa-com/kivo_agent/pull/239


### Added
- Added story agent to user agent.

---

## [1.1.5] - 2025-08-26 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/237

### Changed / Enhanced
- Story agent has knowledge for user project names. It can now validate project, assignee names 
before preview, and user can create and move stories.


---
## [1.1.4] - 2025-08-26 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/236

### Changed / Enhanced
- **KPAA-654**: Implemented centralized error propagation in CRM FAQ Agent. Now all errors propagate to the top level, ensuring only a single consolidated error email is triggered. Improves reliability and avoids duplicate notifications.
## [1.1.3] - 2025-08-26 [@w3villa-shashank-sahu]

PR: https://github.com/w3villa-com/kivo_agent/pull/235

### Fixed
- **#KPAA-281**: Fixed issue where chat history was persisting across different conversation threads. Implemented thread-based session ID generation using Slack's thread timestamp (`thread_ts`) to create unique session identifiers. Session ID format changed to `{email}_{thread_ts}` to ensure each Slack thread maintains separate conversation context.

---

## [1.1.2] - 2025-08-26 [@w3villa-sachin-awasthi]

PR : https://github.com/w3villa-com/kivo_agent/pull/234

### Fixed
 - **KPAA-649**: Updated WebSocket disconnect method to include app_name parameter in connect.py, iats.py, and workplace.py

 ---
## [1.1.1] - 2025-08-25 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/231

### Changed / Enhanced
- Fixed duplicate session error arising in production server.

---
## [1.1.0] - 2025-08-25 [@w3villa-akhilesh]

PR: https://github.com/w3villa-com/kivo_agent/pull/222

### Changed / Enhanced
  - **KPAA-615**: Implemented centralized error propagation in Triage Agent. Now all errors propagate to the top level, ensuring only a single consolidated error email is triggered. Improves reliability and avoids duplicate notifications.

### Fixed
  - **KPAA-615**: Resolved issue where multiple error emails were being sent for a single failure in Triage Agent. Now only one consolidated error email is sent, eliminating redundant notifications.

## [1.0.8] - 2025-08-24 [@w3villa-rohit-kushwaha]
PR: https://github.com/w3villa-com/kivo_agent/pull/231
### Changed / Enhanced
- **[KPAA-631](https://www.kivo.ai/projects/1882/stories/KPAA-631)**: **Google ADK Framework**: Updated from version 1.1.1 to 1.12.0 while maintaining clean, efficient core functionality without unnecessary configuration overhead.
- **State Management**: Implemented efficient `setdefault` usage throughout the project for better performance in state initialization and management across all agents.

### Fixed
- **Dependencies**: Updated `requirements.txt` and `pyproject.toml` to reflect Google ADK version upgrade from 1.1.1 to 1.12.0.

---

## [1.0.7] - 2025-08-23 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/228

### Changed / Enhanced
- **[KPAA-614](https://www.kivo.ai/projects/1882/stories/KPAA-614)**: 
- **Updated instructions for story creator agent**: Added a clear and complete instructions in pm board story agent along with steps, guidelines, confirmation intent rules according to updated flow in mcp.

---


## [1.0.6] - 2025-08-23 [@w3villa-sachin-awasthi]
PR : https://github.com/w3villa-com/kivo_agent/pull/226
### Added
- **[KPAA-634](https://www.kivo.ai/projects/1882/stories/KPAA-642)**: Connect the user agent with User MCP, update its logic to use the USER_MCP_SERVER_URL constant, and set app_name for logging to improve clarity in the invocation process.

---

## [1.0.5] - 2025-08-22 [@w3villa-sachin-awasthi]

PR: https://github.com/w3villa-com/kivo_agent/pull/225

### Changed / Enhanced
- **Refactored Image Validation Service**: Moved image validation logic from `is_image_valid.py` to a new modular architecture with updated import paths in `main.py`. The refactored `ImageValidator` class maintains support for validation and compression across PNG, JPEG, WebP, and GIF formats while improving code organization and maintainability.

---

## [1.0.4] - 2025-08-22 [@w3villa-ishan-chauhan]

### Added
- **[KPAA-634](https://www.kivo.ai/projects/1882/stories/KPAA-593)**: Added paginated apis handling 
capability in hrms agent. Rules are generic can work for any agent.


### Changed / Enhanced 
- **[KPAA-634](https://www.kivo.ai/projects/1882/stories/KPAA-593)**: 
Enhanced `work_from_home_office` feature with start time based filtering and now capable of returning
entire response.

---

## [1.0.3] - 2025-08-22 [@w3villa-sachin-awasthi]
PR: https://github.com/w3villa-com/kivo_agent/pull/223
### Fixed
- Fixed logger debug statements in `load_leave_context` to use `app_name` directly instead of accessing `callback_context.state` for improved clarity and consistency in logging
- Fixed f-string syntax errors caused by using double quotes inside f-string expressions, resolved by switching to single quotes or proper quote escaping

---


## [1.0.2] - 2025-08-22 [@w3villa-sachin-awasthi]
PR: https://github.com/w3villa-com/kivo_agent/pull/220
### Added
- **[KPAA-593](https://www.kivo.ai/projects/1882/stories/KPAA-593)**: Complete Image Management System - Full-featured REST API for uploading, deleting, and editing images with S3 integration, Bearer token authentication, batch processing, and comprehensive image lifecycle management.
- **[KPAA-577](https://www.kivo.ai/projects/1882/stories/KPAA-577)**: Image Delete API - Secure endpoint for removing images from S3 storage with proper authentication and error handling.
- **Vision API Integration**: AI-powered image analysis and text extraction service with high-detail processing and seamless chat integration.
- **Image-Aware Chat System**: WebSocket-enabled chat with image upload support, context-aware responses, and session state management across IATS, and Triage agents.

### Fixed
- **Enhanced Image File Size Limit**: Increased maximum image upload size from 5MB to 10MB with tiered compression strategy (1-2MB: 30%, 2-5MB: 20%, 5-10MB: 15% quality). 
- Enhanced S3 service with specialized image upload methods and automatic content-type detection. 
- Improved error handling and cleanup mechanisms for image processing workflows. 
- Optimized image compression algorithms with intelligent fallback to original files when compression increases size. 

---


## [1.0.1] - 2025-08-21 [@w3villa-ishan-chauhan]

PR: https://github.com/w3villa-com/kivo_agent/pull/221
- ### Changed / Enhanced 
- **[KPAA-617](https://www.kivo.ai/projects/1882/stories/KPAA-617)**: Enhanced leave agent with holiday checks, confirmation, and full user apply-leave functionality. Prompt-level improvements.

### Fixed
- Fixed code level bugs, code level refactoring, fixed `checking_methods` logical bugs. Fixed Timeline tool response error, manager info hallucination. 


## [1.0.0] - 2025-01-20 [@w3villa-rohit-kushwaha]

### Added
- **KPAA-564**: Added tag-based MCP tools handling in MCP connection. Adjusted instructions for Triage, HRMS, and Calling agent. Fixed `close_match` state issue.
- **Advanced Transcription Service**: AI-powered audio transcription with S3 integration and multi-format support.  
- **Enhanced Resume Parser**: Multi-format resume parsing (PDF, DOC, DOCX) with job matching and company-specific parsing. 
- **CRM FAQ Agent**: Context-aware CRM question answering with knowledge base integration and session handling.  
- **Database Migration System**: Automated schema migration with rollback support, including `app_name` column for `iats_user_sessions`.  
- **Triage Agent**: Intelligent query routing and coordination system.  

---



# Release Highlights

A simplified, business-friendly summary of major features for this release.  

---

## 1. Advanced Transcription Service (v1.0.0)

**What It Does**  
AI-powered transcription of audio files stored in S3, supporting MP3, WAV, M4A, and FLAC.  

**Why It Matters**  
- Eliminates manual transcription  
- Faster processing with higher accuracy  
- Batch processing for bulk files  

**How It Works**  
- Direct S3 integration  
- Machine learning models ensure accuracy  
- Confidence scoring and transaction ID tracking  

**Use Case Example**  
Recruitment calls in S3 are automatically transcribed, making them searchable (e.g., “Java”, “Remote work”).  

**Reference**  
Added in v1.0.0 – documented in `CHANGELOG.md`  

---

## 2. Enhanced Resume Parser (v1.0.0)

**What It Does**  
Extracts skills, experience, and education from resumes (PDF, DOC, DOCX) for smarter job matching.  

**Why It Matters**  
- Saves recruiters hours of manual screening  
- Tailors parsing to company-specific needs  
- Provides candidate analytics  

**How It Works**  
- NLP-powered parsing engine  
- Multi-format support  
- Enhanced analytics & reporting  

**Use Case Example**  
Upload 100 resumes → system auto-matches candidates to jobs with a compatibility score.  

**Reference**  
Added in v1.0.0 – documented in `CHANGELOG.md`  

---

## 3. CRM FAQ Agent (v1.0.0)

**What It Does**  
Answers CRM-related questions using a knowledge base with context-aware responses.  

**Why It Matters**  
- Reduces repetitive CRM queries  
- Maintains conversation context  
- Seamlessly integrates with CRM systems  

**How It Works**  
- Semantic vector search  
- Session handling for continuity  
- Direct CRM integration  

**Use Case Example**  
A sales agent asks, *“What was the pricing of CRM?”* → the FAQ Agent fetches it instantly.  

**Reference**  
Added in v1.0.0 – documented in `CHANGELOG.md`  

---

## 4. Database Migration System (v1.0.0)

**What It Does**  
Automates database schema migrations with rollback support, including `app_name` column for `iats_user_sessions`.  

**Why It Matters**  
- Smooth schema updates without downtime  
- Safeguards data integrity  
- Rollback safety for failed migrations  

**How It Works**  
- Migration scripts with version control  
- Rollback capability  
- Indexing strategies for complex changes  

**Use Case Example**  
Deploy a new feature needing schema changes → migration runs safely with rollback available.  

**Reference**  
Added in v1.0.0 – documented in `CHANGELOG.md`  

---

## 5. Triage Agent (v1.0.0)

**What It Does**  
Routes user queries to the right specialized agent (HRMS, ATS, PM Board, Calling).  

**Why It Matters**  
- Eliminates manual query redirection  
- Improves response time  
- Ensures accurate routing every time  

**How It Works**  
- Role-based access ensures security  
- Acts as the main entry point for all queries  

**Use Case Example**  
A user asks *“Show me work from home employees ?”* → Triage Agent routes it directly to HRMS Agent.  

**Reference**  
Added in v1.0.0 – documented in `CHANGELOG.md`  

---

# Rules and Guidelines

### Categories
Every changelog entry **must** fall into one of these categories:

- **Added** → New features or functionality  
- **Changed / Enhanced** → Improvements or modifications to existing functionality  
- **Fixed** → Bug fixes or error corrections  
- **Removed** → Features or APIs removed in this release  

---

### Version Numbering
- **MAJOR**: Incompatible API changes  
- **MINOR**: New functionality in a backwards-compatible manner  
- **PATCH**: Backwards-compatible bug fixes  

---

### Release Process
1. Update version numbers in relevant files  
2. Move items from **Unreleased** into the new version section  
3. Update `CHANGELOG.md` with categorized entries  
4. Create a Git tag with the version number  
5. Deploy to staging environment for testing  
6. Deploy to production after validation  

---

### Contributing
When contributing to this project:
1. Add entries to the **Unreleased** section  
2. Follow the **categories and format** above  
3. Always include your GitHub username (`[@username]`)  
4. Provide clear details if it’s a **breaking change**  
5. Update documentation as needed  
6. Add your name to the **Contributors** section  

---

### Developer Attribution Guidelines
- Use `[@username]` format immediately after feature/change descriptions  
- For collaborative work, list contributors: `[@user1, @user2]`  
- Keep contributors in **alphabetical order**  

---

For more information about the project setup and deployment, see [README.md](./kivo_agent/README.md).
