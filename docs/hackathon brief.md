# ALX Digital Bridge Accessibility Hackathon 2026
## Hackathon Brief & AI Agent Context Document

**Program:** Digital Bridge – ALX Ethiopia  
**Event:** Accessibility Hackathon 2026  
**Selected Track:** Track 3 – Multilingual Assistant and Live Help  
**Event Dates:** November 14–15, 2026  
**Venue:** ALX Tech Hub, Lideta, Addis Ababa, Ethiopia  
**Application Deadline:** November 13, 2026, 23:59  
**Current Participation Status:** Application/selection confirmation pending.

---

# 1. Project Overview

The Digital Bridge Accessibility Hackathon 2026 is organized by ALX Ethiopia in collaboration with the Addis Ababa Association of Persons with Physical Disabilities (AAAPD) and Tomorrow is Better.

Digital Bridge is a program of ALX, delivered in partnership with SNV and Mercy Corps under LIWAY.

The hackathon aims to improve digital accessibility across Ethiopia's learning platforms and job-matching platforms.

The central objective is:

**Build what works for everyone. Then everyone gets to work.**

Teams of four engineers collaborate with a co-designer who is blind, Deaf, has a disability, or has lived through displacement.

The goal is not simply to build standalone applications. Teams must develop reusable, accessible, open modules that can integrate into existing platforms.

The first intended integration target is Savanna, ALX's learning platform, which serves approximately 3,000 Digital Bridge learners.

The modules will subsequently be made available to eight job-matching platforms and two regional training institutions.

## 1.1 Event Structure

- Three development tracks.
- 30 teams and 40 individual participants selected in each track, according to the announcement.
- Teams consist of four engineers.
- Participants applying individually can be matched into teams.
- Each team works with a co-designer.
- One winning team per track receives 100,000 ETB.
- Each winning team also receives a paid, two-week hardening sprint with ALX engineers.

## 1.2 Current Schedule

| Date | Activity |
|---|---|
| November 9–13 | Online technical training, 19:00–20:30 |
| November 13 | Application deadline, 23:59 |
| November 14 | Hackathon Day 1, 09:00–17:00 |
| November 15 | Hackathon Day 2, submission by 16:30 |
| Around November 22 | Award announcements |
| After awards | Two-week hardening sprint for winners |
| December | Planned deployment to learners and partner platforms |

**Important:** Participation is not yet confirmed. Selection notifications are communicated by phone or email, generally within two days of applying. Do not assume acceptance until confirmation is received.

---

# 2. Selected Track: Track 3

## Multilingual Assistant and Live Help

### 2.1 Problem Statement

Many Ethiopian learners encounter difficulties when using digital learning platforms because the platforms primarily communicate in English.

This creates barriers for learners who:
- Think and communicate more comfortably in Amharic.
- Prefer Tigrinya, Afaan Oromo, Somali, or Arabic.
- Are unfamiliar with computers and digital learning environments.
- Need assistance understanding lessons or navigating the platform.
- Need direct human support when automated assistance is insufficient.

Currently, learners may become stuck without access to a tutor who speaks their language or someone who can see what is happening on their screen.

The hackathon challenges teams to build an accessible, multilingual assistant that makes learning platforms easier to use.

### 2.2 Core Objective

Build a multilingual AI-powered assistant that integrates into existing learning platforms and provides:

1. Multilingual text and voice assistance.
2. Answers grounded exclusively in course content, with citations.
3. Human assistance when AI cannot adequately resolve a problem.
4. Multiple access channels, including web and Telegram.
5. Accessibility features for different users.
6. A flexible AI architecture that can work with cloud models, local models, or offline FAQs.

The solution should be designed as a reusable module, not just an independent chatbot.

---

# 3. Mandatory Functional Requirements

The following requirements are explicitly stated in Track 3 and should be treated as essential.

## 3.1 Multilingual AI Tutor

Build a tutor supporting:

- Amharic.
- English.

The tutor must support both text and voice interactions.

Its responsibilities include:
- Answering questions about course materials.
- Explaining difficult concepts.
- Helping learners understand lessons.
- Providing responses in the learner's preferred language.
- Supporting voice-based interaction.

**Critical requirement: Grounded answers**

The assistant must answer only from available course content.

It must provide citations identifying the source of its answers.

It should not freely hallucinate answers or invent course information.

If the answer cannot be found in the course material, the assistant should communicate that limitation and offer another way to get help.

## 3.2 Multiple Access Channels

The assistant must be accessible through:

**A. Web embed**
- An assistant that can be embedded into Savanna.
- Should be reusable on other websites.
- Must work within the existing platform environment.

**B. Telegram bot**
- Learners should be able to interact with the assistant through Telegram.
- Should support the core tutoring experience.
- Should provide a route to human assistance.

**C. Low-bandwidth SMS or text route**
- Provide a way to access assistance through SMS or another lightweight text-based channel.
- The experience should accommodate users with limited connectivity.

These channels are mandatory requirements, not optional enhancements.

## 3.3 Accessible Chat Interface

The chat interface must:

- Announce newly received messages to assistive technologies.
- Handle right-to-left (RTL) text.
- Support appropriate keyboard navigation.
- Work with screen readers.
- Provide an accessible interaction experience.

RTL support is particularly important for languages such as Arabic.

The interface must not assume that all users communicate using left-to-right scripts.

## 3.4 One-Click Human Assistance

The assistant must provide a way to escalate a conversation to a real person.

Requirements:

- A clearly accessible human-help action.
- One-click escalation.
- Learner-controlled screen sharing.
- The learner must explicitly control whether screen sharing starts.
- Human assistance should be available when AI cannot solve the problem.

Privacy is essential. Screen sharing must never happen automatically or without user consent.

## 3.5 Pluggable AI Architecture

The AI layer must not be tightly coupled to a single commercial AI provider.

The solution should support different backends:

1. Cloud AI models.
2. Locally hosted open models.
3. Offline FAQ-based assistance.

The architecture should allow different AI providers to be substituted without rewriting the entire application.

This is important for affordability, offline accessibility, and long-term sustainability.

---

# 4. Additional Features That Earn Extra Credit

These are explicitly identified as additional benefits rather than mandatory core requirements.

## 4.1 Plain-Language Simple Mode

Provide an option that simplifies explanations.

For example:
- Use shorter sentences.
- Avoid unnecessary technical terminology.
- Explain unfamiliar words.
- Break complex instructions into smaller steps.

The objective is to make information easier to understand for learners with different literacy levels and learning needs.

## 4.2 Teacher Dashboard

Provide a teacher-facing view showing:

- Most frequently asked questions.
- Common topics learners struggle with.
- Frequently unresolved questions.

Privacy requirement:

The dashboard must not reveal individual learner identities.

The goal is to help instructors identify gaps in course materials and improve teaching.

---

# 5. Career Gateway – Required for Every Track

Track 3 is not limited to course assistance.

Every track must also implement the Career Gateway requirements.

These are mandatory.

## 5.1 Job Alerts

Learners must be able to receive job alerts through:

- Telegram.
- SMS.

## 5.2 Interview Accommodation Requests

Provide a way for job applicants to request interview accommodations.

Examples include:
- Accessible interview arrangements.
- Additional time.
- Alternative communication methods.
- Other reasonable accessibility accommodations.

## 5.3 Job-Related Questions

The assistant must also answer questions about jobs, not just course content.

Examples:
- What jobs are available?
- What qualifications are required?
- What skills are needed?
- How can I apply?
- What does a job description mean?

The solution must therefore accommodate both learning-related and employment-related assistance.

---

# 6. Integration and Technical Requirements

One of the most important aspects of this hackathon is that the solution must be reusable and integrable into existing platforms.

## 6.1 Savanna Integration

Every team receives a Savanna starter project and documentation at the hackathon kick-off.

The solution must run inside Savanna.

It should not require rebuilding the existing learning platform.

The goal is to develop a plug-in module that can be added to an existing system.

## 6.2 Three Integration Levels

The announcement identifies three integration levels.

**Level 1 – Script Tag**

The module can be installed on another website using a script tag.

Example concept:

`<script src="https://example.com/assistant.js"></script>`

**Level 2 – REST API**

Expose functionality through a REST API and provide an OpenAPI specification.

**Level 3 – Standards-Based Integration**

Support an appropriate standard, such as:

- LTI 1.3.
- schema.org/JobPosting.
- Open Badges 3.0.

For Track 3, LTI 1.3 and appropriate job-posting interoperability are particularly relevant areas to investigate.

The judging criteria reward adoption across all three integration levels.

However, the actual implementation scope and the required level of integration should be clarified with the organizers and technical mentors.

---

# 7. Accessibility Requirements

Accessibility is a central requirement, not an optional design improvement.

The judging process begins with a mandatory accessibility gate.

A co-designer must be able to complete the main task unaided using:

1. NVDA screen reader.
2. TalkBack screen reader.
3. Keyboard-only navigation.
4. 200% zoom.
5. Sound off.

Additionally:

- axe-core must report zero critical or serious accessibility issues.
- The team must submit a WCAG 2.2 AA conformance report.

The co-designer is an active member of the development team, not someone who only tests the application at the end.

The solution should be continuously evaluated with the co-designer.

Important implementation considerations:

- Semantic HTML.
- Proper ARIA attributes.
- Accessible focus management.
- Screen-reader announcements for incoming messages.
- Keyboard-accessible controls.
- Sufficient color contrast.
- Visible focus indicators.
- Accessible form labels.
- RTL-compatible layouts.
- Responsive interfaces.
- Voice interaction that does not exclude text-based users.

---

# 8. Judging Criteria

The competition uses a two-stage evaluation.

## Stage 1: Mandatory Accessibility Gate

The submission must pass the accessibility requirements described above.

Failure to pass means the submission does not proceed to scoring.

## Stage 2: Scoring – 100 Points

| Category | Points | What Judges Evaluate |
|---|---:|---|
| Works for the people it is for | 30 | Co-designer evaluation, independent task completion, use of feedback |
| Can be adopted | 25 | Ease of installation, documentation, integration levels |
| Built for Ethiopia | 15 | Amharic, Ethiopic script, Ethiopian calendar, affordable Android devices, 3G, offline support |
| Quality, security and privacy | 15 | Tests, minimum data collection, consent, security |
| Can be kept running | 15 | Low operating costs, no paid API lock-in, understandable documentation |

### Important Strategic Implications

**Accessibility is a gate, not just a scoring category.**

A technically impressive AI assistant that cannot be used by the intended beneficiaries may fail before scoring.

**Adoption is worth 25 points.**

A standalone application with no reusable integration strategy is insufficient.

**The solution must work in the Ethiopian context.**

A design that assumes reliable broadband, expensive smartphones, and unlimited AI API access is not appropriate.

**Privacy and sustainability matter.**

The system should minimize data collection, avoid unnecessary costs, and provide understandable documentation.

---

# 9. Training Week

All participants are expected to attend five online training sessions.

Time: 19:00–20:30, Addis Ababa time.

| Date | Topic |
|---|---|
| November 9 | Accessibility, co-design and the October 21 findings |
| November 10 | WCAG 2.2 AA, axe-core, NVDA and TalkBack |
| November 11 | Drop-in web components, REST APIs and integration standards |
| November 12 | Offline-first development, Amharic AI, caching and self-hosted models |
| November 13 | Office hours, setup testing and presentation preparation |

These sessions should inform implementation decisions.

The team should prioritize the official starter project, documentation, and mentor guidance over assumptions about the existing platform.

---

# 10. Co-Design and Intended Beneficiaries

The hackathon is based on inclusive co-design.

The intended beneficiaries include:

- Blind and low-vision learners.
- Deaf and hard-of-hearing learners.
- People with physical disabilities.
- People with learning disabilities.
- Refugees, displaced people and returnees.
- Learners who are unfamiliar with computers.
- Learners who prefer languages other than English.

The co-designer should participate throughout development.

The team should:

1. Understand the co-designer's actual needs.
2. Identify barriers in existing platforms.
3. Validate proposed features with them.
4. Test the application on their own device.
5. Incorporate their feedback.
6. Ensure they can independently complete the main task.

The goal is to build something that genuinely works for the intended users.

---

# 11. Deployment, Ownership and Sustainability

## 11.1 Open Source

The solution will be released under an open licence named by ALX at kick-off.

ALX and its partners may use and publish the code.

The participating team receives credit by name.

## 11.2 Deployment

The intended deployment sequence is:

1. Savanna learning platform.
2. Approximately 3,000 Digital Bridge learners.
3. Eight job-matching platforms.
4. Two regional training institutions.

## 11.3 Post-Hackathon Hardening

Winning teams receive a paid two-week hardening sprint with ALX engineers.

The sprint includes:

- Security review.
- Three testing rounds involving at least 30 testers with disabilities.
- Savanna integration.

The objective is to move the winning prototype toward a deployable solution.

---

# 12. Development Priorities for Track 3

The following is a suggested implementation prioritization based on the official requirements. It is not an additional official requirement list.

## Priority 1 – Essential Core

- Multilingual text assistant.
- Amharic and English support.
- Course-content-grounded answers.
- Citations.
- Web-based chat interface.
- Telegram bot.
- Low-bandwidth text access.
- RTL handling.
- Accessible chat announcements.
- Human escalation.
- Learner-controlled screen sharing.
- Pluggable AI architecture.
- Job alerts.
- Interview accommodation requests.
- Job-related assistance.

## Priority 2 – Important Enhancements

- Voice input and output.
- Offline FAQ support.
- Local open-model support.
- Simple mode.
- Teacher analytics dashboard.
- Improved low-bandwidth behavior.

## Priority 3 – Integration and Production Readiness

- Script-tag integration.
- REST API.
- OpenAPI documentation.
- Savanna integration.
- Security and privacy review.
- Automated tests.
- WCAG 2.2 AA report.
- Deployment documentation.

**Note:** These priorities are a planning aid. They do not change the fact that the official requirements apply to the submission.

---

# 13. Instructions for the AI Agent

You are assisting with the development of a solution for the ALX Digital Bridge Accessibility Hackathon 2026.

The selected track is:

**Track 3 – Multilingual Assistant and Live Help.**

Your role is to act as a technical collaborator, software architect, accessibility consultant, and development assistant.

## Your Responsibilities

Help with:

1. Understanding and analyzing the problem.
2. Identifying practical solutions.
3. Designing the system architecture.
4. Selecting an appropriate technology stack.
5. Evaluating AI and multilingual approaches.
6. Designing RAG and course-content retrieval.
7. Implementing backend APIs.
8. Building the web assistant.
9. Developing Telegram integration.
10. Designing low-bandwidth communication.
11. Implementing voice interactions.
12. Designing human escalation and screen-sharing workflows.
13. Implementing the Career Gateway.
14. Ensuring accessibility.
15. Preparing tests and documentation.
16. Preparing the final demonstration and presentation.

## Non-Negotiable Development Principles

- Follow the official hackathon requirements.
- Prioritize accessibility from the beginning.
- Do not treat this as an ordinary chatbot project.
- Do not invent answers outside available course content.
- Provide citations for course-related answers.
- Support Amharic and English.
- Consider RTL languages.
- Design for low-bandwidth Ethiopian users.
- Minimize data collection.
- Never initiate screen sharing without learner consent.
- Avoid unnecessary paid API dependencies.
- Keep the AI layer replaceable.
- Build reusable modules rather than tightly coupled platform-specific code.
- Do not overengineer the MVP.
- Clearly distinguish implemented features from planned features.
- Never claim that a requirement is satisfied without evidence or testing.

## How You Should Work With Me

- Explain architectural decisions before implementing complicated features.
- Present alternatives when there are meaningful technical trade-offs.
- Prefer practical solutions that can be implemented within the hackathon timeline.
- Break large tasks into small, manageable steps.
- Identify technical risks early.
- Ask for clarification when essential information is missing.
- Do not make assumptions about Savanna's internal architecture.
- Wait for the actual starter project and documentation before proposing platform-specific integration.
- Keep the official judging criteria in mind when suggesting priorities.
- Help me distinguish what is essential for the two-day hackathon from what can be implemented during a later hardening phase.

---

# 14. Important Unknowns to Investigate

The announcement does not provide enough information to settle the following questions.

The agent should help investigate these before making architectural decisions.

### Savanna Platform
- What technology stack does Savanna use?
- How does its frontend architecture work?
- Does it support external widgets or embedded applications?
- Does it expose APIs?
- How does authentication work?
- How can course content be accessed?
- What are the exact integration expectations?

### Course Content and AI
- What formats are course materials provided in?
- How will documents be indexed?
- What citation format is expected?
- How should Amharic and English retrieval work?
- Which speech-to-text and text-to-speech services are suitable?
- What is the expected behavior when a question is outside the course materials?

### Human Support
- Who receives escalated requests?
- Is there an existing tutor or support system?
- How should support sessions be managed?
- What screen-sharing technology is permitted?
- How should user consent and privacy be handled?

### SMS and Telegram
- Which SMS provider or gateway is available?
- Are there hackathon-provided credits?
- What are the expected SMS limitations?
- Should Telegram support voice messages?
- How will conversations remain consistent across channels?

### Career Gateway
- Where will job listings come from?
- Is there an existing job-matching API?
- What job information must be supported?
- How will accommodation requests reach employers?

### Hackathon Logistics
- Has the team been officially selected?
- What is the official starter repository?
- What are the exact submission requirements?
- What open-source licence will ALX specify?
- Are there additional requirements from the mentors?

---

# 15. Definition of Success

A successful solution should demonstrate the following:

1. A learner can ask a course-related question in Amharic or English.
2. The assistant retrieves relevant course information and answers with citations.
3. A learner can interact through the web interface and Telegram.
4. A low-bandwidth text-access route is available.
5. Incoming messages are accessible to screen readers.
6. The chat handles RTL content correctly.
7. A learner can request human assistance.
8. Screen sharing remains under the learner's control.
9. The AI layer can switch between cloud, local and FAQ-based implementations.
10. Learners can access job-related information and job alerts.
11. Applicants can request interview accommodations.
12. The module can be integrated into Savanna and reused elsewhere.
13. The intended co-designer can independently complete the main task.
14. The implementation satisfies the accessibility gate.

**The ultimate goal is not to demonstrate the most sophisticated AI technology. It is to build a practical, accessible, affordable and reusable system that helps Ethiopian learners overcome language and digital-accessibility barriers and transition from learning to employment.**

---

*End of Hackathon Context Document.*