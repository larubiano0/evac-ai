# In-Depth Requirements Interview

## Purpose

Conduct a comprehensive, iterative interview with the user to understand their requirements, preferences, constraints, and expectations before producing a detailed, actionable specification.

The objective is to uncover important details, resolve ambiguities, identify hidden assumptions, and explore meaningful tradeoffs rather than simply collecting surface-level requirements.

## Instructions

### 1. Understand the Initial Request

Begin by reviewing the user's request and any relevant context.

Identify:
- The problem being solved.
- The intended outcome.
- Existing requirements and constraints.
- Important ambiguities or missing information.
- Decisions that require user input.

Do not ask questions whose answers are already available from the provided context.

### 2. Conduct an In-Depth Interview

Interview the user interactively, asking thoughtful, specific, and non-obvious questions.

Explore all relevant dimensions, including but not limited to:

- **Goals and motivation:** What problem is being solved, why it matters, and what success looks like.
- **Functional requirements:** Expected features, capabilities, workflows, and behaviors.
- **Technical implementation:** Architecture, technologies, integrations, dependencies, and implementation constraints.
- **User experience:** Interactions, accessibility, usability, and design preferences.
- **Data and state:** Data structures, persistence, validation, privacy, and lifecycle.
- **Edge cases:** Failure scenarios, unusual inputs, boundary conditions, and recovery mechanisms.
- **Performance and reliability:** Scalability, latency, availability, and resource constraints.
- **Security:** Permissions, authentication, authorization, and potential vulnerabilities.
- **Tradeoffs:** Alternative approaches, their consequences, and user priorities.
- **Scope:** Essential requirements, optional features, exclusions, and future extensions.
- **Validation:** Acceptance criteria, testing strategies, and definitions of completion.

Adapt the interview topics to the nature of the request. Do not force irrelevant categories into the conversation.

### 3. Ask High-Value Questions

Prioritize questions that:

- Reveal hidden assumptions.
- Expose conflicting requirements.
- Clarify ambiguous expectations.
- Identify decisions with significant downstream consequences.
- Explore non-obvious edge cases.
- Distinguish essential requirements from preferences.
- Make implicit tradeoffs explicit.

Avoid obvious, redundant, overly broad, or purely procedural questions.

When useful, present concrete alternatives and explain their implications.

Ask questions in manageable groups, allowing the user's answers to inform subsequent questions.

Do not overwhelm the user with an unnecessarily large questionnaire.

### 4. Interview Iteratively

Treat the interview as an adaptive process rather than a fixed checklist.

After each response:

1. Incorporate the new information.
2. Identify remaining uncertainties.
3. Detect contradictions or incomplete requirements.
4. Determine which questions are now most important.
5. Continue interviewing where additional clarification would materially improve the specification.

Revisit earlier decisions when new information reveals inconsistencies or important tradeoffs.

Do not prematurely conclude the interview merely because the initial questions have been answered.

### 5. Maintain a Clear Understanding of Decisions

Throughout the conversation, distinguish between:

- Confirmed requirements.
- User preferences.
- Assumptions.
- Open questions.
- Deferred decisions.
- Explicitly excluded functionality.

Do not silently convert assumptions into requirements.

When proposing a default or making a recommendation, clearly distinguish it from a decision explicitly approved by the user.

### 6. Determine When the Interview Is Complete

Continue interviewing until the requirements are sufficiently detailed to produce a useful, actionable specification.

The interview can conclude when:

- The primary goals and expected outcomes are clear.
- Major functional and non-functional requirements are understood.
- Important technical and design decisions have been addressed.
- Significant ambiguities and contradictions have been resolved.
- Relevant edge cases and failure scenarios have been considered.
- Acceptance criteria can be defined.
- Remaining uncertainties are documented and do not prevent meaningful implementation.

Do not extend the interview indefinitely for marginal details.

### 7. Produce the Specification

Once the interview is complete, synthesize the findings into a structured specification.

Include relevant sections such as:

1. Overview
2. Problem Statement
3. Goals and Success Criteria
4. Scope and Non-Goals
5. Functional Requirements
6. Non-Functional Requirements
7. Architecture and Technical Design
8. Data Models and Integrations
9. User Experience and Workflows
10. Edge Cases and Failure Handling
11. Security and Privacy Considerations
12. Design Decisions and Tradeoffs
13. Testing and Acceptance Criteria
14. Implementation Considerations
15. Open Questions and Future Work

Adapt the structure to the project. Omit irrelevant sections and add others when necessary.

The specification should be:

- Detailed enough to guide implementation.
- Internally consistent.
- Explicit about assumptions and constraints.
- Clear about expected behaviors.
- Organized for easy reference.
- Actionable without requiring extensive additional clarification.

### 8. Deliver the Specification

Provide the completed specification in Markdown format.

If file-writing capabilities are available, save it to an appropriate location based on the user's instructions or the conventions of the current environment.

Do not assume a particular directory structure, filename, development environment, or tool.

If no destination is specified, use a sensible default when appropriate or provide the Markdown content directly.

Clearly communicate where the specification was saved, if applicable.

## Guiding Principles

- **Depth over superficiality:** Investigate meaningful details instead of collecting generic answers.
- **Adaptability:** Tailor the interview to the actual problem.
- **Clarity over assumptions:** Explicitly resolve uncertainty whenever it matters.
- **Tradeoff awareness:** Help the user understand the consequences of important choices.
- **Progressive refinement:** Let each answer guide subsequent questions.
- **Efficiency:** Avoid redundant questions and unnecessary interview length.
- **User authority:** Recommend approaches, but let the user make consequential decisions.
- **Actionability:** Produce a specification that can meaningfully guide execution.

## User Request

{{USER_REQUEST}}