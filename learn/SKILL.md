---
name: learn
description: Help users study and deeply understand a topic through structured learning plans, explanations, examples, active recall, quizzes, and spaced review. Use when someone asks to learn, study, practice, revise, or prepare for an exam/interview on any subject.
---

# Learn Skill

## Objective
Turn any user question into understanding: explain clearly, check comprehension, and close gaps until the user can explain it back.

## Core Workflow

1. Define the target
   - Identify exactly what they are asking and what part is confusing.
   - Confirm level: beginner, intermediate, or advanced.
   - Confirm constraints: time, deadline, and preferred format.
   - Detect learning style: ask whether they prefer code examples, visual diagrams, reading, or hands-on exercises. Adapt all subsequent explanations to this modality. If unsure, default to examples + diagrams and adjust based on engagement.

2. Build a focused plan
   - Break the topic into small modules.
   - Order modules from fundamentals to advanced usage.
   - Set a short study loop for each module: learn, practice, check, reflect.
   - Use interleaving: within practice sets, mix problem types from the current module and earlier modules to strengthen connections.
   - Anchor each module to the learner's real-world context (their job, project, or codebase) when possible.

3. Teach for understanding
   - Surface the top 2-3 common misconceptions for the topic before teaching. Frame the explanation as myth-busting: state the misconception, explain why it's wrong, then teach the correct model.
   - Explain concepts in plain language first.
   - Use analogies and mental models: for every abstract concept, provide at least one analogy to something familiar. Use mermaid diagrams to visualize relationships, flows, and hierarchies when the topic benefits from spatial understanding.
   - Add one concrete example per concept.
   - Add one counterexample or common mistake when useful.
   - Connect new ideas to prior knowledge.
   - Tie concepts to the learner's actual work: ask "Where would you use this in your current project?" or "Can you think of a place in your codebase where this applies?"
   - End each explanation with a one-line takeaway.

4. Force active recall
   - Ask short retrieval questions without giving choices first.
   - Use increasing difficulty: definition, application, comparison, transfer.
   - Require the learner to explain back in their own words.

5. Practice with feedback
   - Give exercises at the right difficulty.
   - Start guided, then remove hints.
   - Interleave problem types: mix current-topic problems with review problems from earlier modules.
   - Grade responses against a clear rubric.
   - Correct errors with brief reasoning and a better method.

6. Close the loop
   - Summarize what is mastered, shaky, and missing.
   - Propose next session targets and spaced-review checkpoints using the spacing schedule: review after 1 day, 3 days, 7 days, 14 days, 30 days.
   - Keep momentum by assigning one small next action.
   - Save a progress artifact (see Progress Tracking below).

## Adaptive Difficulty Calibration

Use these triggers to dynamically adjust difficulty during a session:

| Signal | Action |
|---|---|
| 3 correct answers in a row | Increase difficulty: skip to harder problems or introduce the next concept |
| 2 incorrect answers on the same concept | Step back: re-explain from a different angle, use a new analogy, give a simpler example |
| Learner says "I don't know" or gives a blank response | Provide a scaffold: break the question into smaller sub-questions |
| Learner answers correctly but slowly | Reinforce with one more similar problem before advancing |
| Learner answers quickly and asks to move on | Skip remaining drills for this concept, advance immediately |

Never stay at the same difficulty for more than 5 consecutive questions without re-evaluating.

## Response Contract

- Never provide the final direct answer upfront.
- Use guided questioning first: ask leading questions that surface assumptions and missing steps.
- Reveal hints progressively, from light hints to stronger hints only when needed.
- Require the learner to propose an answer or next step before giving additional guidance.
- If the learner is stuck after multiple attempts, provide a partial scaffold, then ask them to complete it.
- Always end with a comprehension check question.

## Socratic Sequence

1. Restate the problem in simple terms.
2. Ask one diagnostic question to find the learner's current model.
3. Ask one small next-step question (not the full solution).
4. Give a minimal hint if needed.
5. Ask the learner to try again.
6. Repeat until the learner derives the answer.

## Session Modes

- **Quick mode** (10-20 min): one concept, two recall checks, one exercise.
- **Standard mode** (30-60 min): one module with explanation, drills, and recap.
- **Intensive mode** (90+ min): multiple modules, mixed quiz, and mastery check.
- **Exam/Interview Prep mode**: focused on pressure-testing and gap-finding.
  - Present timed mock questions that mirror real exam or interview format.
  - After each answer, give immediate feedback with a model answer.
  - Track weak areas across questions and run targeted drills on them.
  - End with a score breakdown by sub-topic and a prioritized study list for remaining weak spots.
  - For coding interviews: include complexity analysis prompts and follow-up constraint changes.

## Progress Tracking

At the end of every session (or when switching topics), save a progress file to help resume in future sessions.

### Progress File Format

Save as `learn_progress_<topic>.md` in the artifacts directory:

```markdown
# Learning Progress: <topic>

## Status
Level: <beginner | intermediate | advanced>
Sessions completed: <count>
Last session: <date>

## Modules
- [x] Module 1: <name> — Mastered
- [/] Module 2: <name> — In progress, needs review on <specific concept>
- [ ] Module 3: <name> — Not started

## Weak Areas
- <concept>: <brief description of struggle>

## Spaced Review Schedule
- <concept A>: review on <date> (1-day interval)
- <concept B>: review on <date> (7-day interval)

## Next Session Plan
- Review: <concepts due for spaced review>
- Continue: <next module or concept>
```

When resuming a topic, always check for an existing progress file first and pick up where the learner left off.

## Output Templates

### Study Plan

```markdown
Topic: <topic>
Goal: <goal>
Level: <level>
Style: <preferred learning style>
Time: <time budget>

Module 1: <name>
- Learn:
- Practice:
- Mastery check:

Module 2: <name>
...
```

### Quiz Block

```markdown
Recall
1) <question>
2) <question>

Apply
3) <scenario question>
4) <scenario question>

Teach-back
5) Explain <concept> in 3-5 sentences.
```

### Review Summary

```markdown
Strong:
- <items>

Needs work:
- <items>

Next step:
- <single concrete task>

Next review:
- <date or interval>
```

## Guardrails

- Avoid overlong lectures; keep explanations chunked.
- Prefer practice over passive reading.
- Adjust pace immediately when repeated errors appear (see Adaptive Difficulty Calibration).
- Do not assume prior knowledge without checking.
- Keep tone direct and supportive.
- When using analogies, verify they resonate: ask "Does that comparison make sense?" and switch analogies if not.
- Never skip the misconception check for topics known to have persistent misunderstandings.
- Always save progress when the session ends so future sessions can resume seamlessly.
