# Capturing the Why: An LLM-Mediated Tacit-Knowledge Layer for Collaborative Data-Driven Science on Scientific Data Catalogs

*Approach & theory — design report, 2026-07-06.*

## Abstract

Reproducibility in collaborative computational and data-driven science — of which machine
learning is a prominent instance — is a recognized and growing crisis (Kapoor & Narayanan
2023), and it is commonly treated as a problem of recording *artifacts*: datasets, code,
configurations, execution environments. But faithfully re-running a flawed data selection
or an inappropriate method reproduces a mistake, not a result — mechanical reproducibility
of bad data or a bad process has no scientific value. What makes a computational result
scientifically reproducible is the **reasoning behind it**: why particular data were
selected, what alternatives were rejected, and what was learned from failures — the *why*
that lives in people's heads and informal conversation rather than in any artifact, and
that is precisely the *data and context* work most undervalued in practice (Sambasivan et
al. 2021). This reasoning is hardest to preserve exactly where modern data-driven science
now operates: on **multidisciplinary teams** whose members hold different vocabularies,
mental models, and tacit practices, so that the *why* must cross disciplinary boundaries
that neither shared artifacts nor even shared physical presence bridge.

We present the design of a **tacit-knowledge layer** — an always-on, LLM-mediated system
that captures decision rationale as a by-product of normal work and surfaces the relevant
prior knowledge at the moment a team member is about to act, warning of known dead ends
and suggesting next steps. The system is built on one hard constraint — *the user must do
nothing* — realized as a three-moment loop (capture-on-action, retrieve-before-action,
accumulate-for-the-next-teammate). We ground the design in the knowledge-management and
networks-of-practice literature: the LLM occupies the **knowledge-intermediary** role
that external knowledge reuse is known to require but rarely gets (Markus 2001); the data
catalog serves as an **evolving boundary object** whose controlled vocabulary grounds
cross-discipline translation (Star & Griesemer 1989; Carlile 2004); and the accumulated
journal supplies **desire-line** signals that steer the catalog's own schema/vocabulary
co-evolution (Noy & Klein 2004). We argue the design is simultaneously literature-sound,
field-motivated by a 19-month clinical-ML deployment, and doctrinally aligned with the
SCALE / agentic-infrastructure vision of the underlying platform — and we are explicit
about the honesty boundary the theory imposes: the system moves the *articulable* shell of
knowledge and *points at* the irreducibly tacit remainder, which no text file can hold.

*This is a pre-implementation design report. Concrete mechanics (file formats, field
syntax, skill surfaces) live in the companion implementation spec,
[`../superpowers/specs/2026-07-06-tacit-knowledge-retrieval-index-design.md`](../superpowers/specs/2026-07-06-tacit-knowledge-retrieval-index-design.md);
decision IDs (D1–D11) are shared between the two. Positioning within the broader body of
work — the founding Deriva-ML paper (Li et al. 2024), the AI-Ready-Ecosystems vision
(Kesselman & Schuler 2026), and the interactional-layer study (Li & Kesselman 2026) — is
given in §1.2. Note: "TK-R1…TK-R4" (this report's requirements, §7) are distinct from the
Deriva-ML paper's own R1–R4 (Data-centric / Comprehensive / Adaptive / Socio-technical).*

## 1. Introduction

### 1.1 The problem: reproducibility fails when the *why* is lost

Computational and data-driven science and engineering — simulation, data-intensive
experiment, genomic and imaging pipelines, and, prominently, machine learning — is
fundamentally an *experimental* process. Researchers iteratively explore data subsets,
parameters, features, models, and configurations to understand what works and why. Simply
re-running a past execution is insufficient if that execution rested on a flawed data
selection, an inappropriate method, or a mis-set parameter. Meaningful reproducibility
therefore requires capturing not just *what* was executed but *why* particular approaches
were tried, what alternatives were rejected, how understanding evolved across iterations,
and what was learned from failures. **Machine learning is the instance we develop
throughout this report** — its data-selection, feature, and hyperparameter choices make
the *why* especially load-bearing — but the problem, and the design that addresses it,
generalize across data-driven computational work.

Data-driven science of this kind is intrinsically **multidisciplinary**, and that is what
makes preserving the *why* hard. A team of the kind such work now demands mixes a *domain
scientist* (who understands the phenomenon and the data's meaning but may not code), a
*data engineer* or *research software engineer* (who understands data management and
pipelines), and a *computational or ML specialist* (who understands the methods but not the
domain) — and often a fourth role such as a clinician or experimentalist. Each brings a
different vocabulary, different mental models, and different tacit practices. The same word
(*"sample," "label," "confidence," "validation"*) means different things to each. This is a
boundary between **different communities of practice**, and knowledge does not flow freely
across it: Brown and Duguid (1991; 2001) show that practice-based knowledge is "sticky" —
it travels readily *within* a shared practice but sticks *across* practice boundaries,
because the shared assumptions that make it interpretable are absent on the other side.
Crucially, this cause is **epistemic, not geographic**: the boundary persists even when the
team is **fully co-located**. Sitting in the same room does not give a domain scientist the
ML specialist's tacit sense of when a loss curve is doomed, nor the ML specialist the domain
scientist's feel for which data artifacts are trustworthy; the knowledge that must cross the
boundary is precisely the kind that shared physical presence does *not* transmit (§4.3).

This experimental context, and the cross-boundary reasoning it depends on, rarely appears
in formal documentation. It emerges in discussions among team members, resides in
individual researchers' understanding of the project's history, and is communicated
informally during handoffs. When that context is lost — as inevitably happens over time,
across team-member transitions, and as understanding that was obvious in the moment fades —
**reproducibility breaks down not because artifacts are missing but because the reasoning
that made those artifacts meaningful has evaporated.** A 19-month deployment of a
data-centric ML management system on an interdisciplinary clinical research project (see
§1.2, §4.9) makes this concrete: even with comprehensive versioning and provenance already
in place, the recurring breakdowns were *lost rationale over time*, *incomplete experiment
configurations*, and *loss of shared context* — interactional, not artifactual, failures.

### 1.2 A socio-technical problem, newly tractable

The failures of §1.1 are **not, at root, technical failures.** The datasets, code, and
executions are captured correctly; what is missing is the human and organizational work —
explanation, coordination, sensemaking, the articulation of informal decisions — through
which collaborators interpret prior work and align on shared intent over time.
Reproducibility in collaborative data-driven science is therefore best understood not as a
static property of artifact completeness but as an ongoing **socio-technical
accomplishment**: a
successful system must support the interactions among people, technology, and
organizational practice as an integrated whole, not optimize the technical artifacts in
isolation (Bauer & Herder 2009; the socio-technical-systems tradition, from Trist &
Bamforth 1951 onward). This is why purely structural infrastructure — versioning,
provenance, lineage — is *necessary but insufficient*: it records what was executed and
how artifacts relate, but it cannot by itself carry the reasoning that makes those
artifacts meaningful to a later reader. The gap is in the *social* half of the
socio-technical system, and it must be addressed there.

**What makes addressing it newly tractable is the recent maturation of LLMs and agentic
assistants.** Historically, the only agent that could translate loosely-stated intent,
explain a design decision in a colleague's vocabulary, or notice that a proposed action
resembles a past dead end was another *human* — which is exactly the scarce, non-scalable
resource whose absence causes the breakdowns. Large language models change this: embedded,
context-aware AI assistance has moved from research prototype to everyday practice in
software work (GitHub Copilot's 2025 agent mode; the broader code-agent and AI-in-IDE
literature — Sergeyuk et al. 2026), demonstrating that an AI agent can operate effectively
*within* a complex technical system without replacing human judgment. An LLM grounded in a
data catalog's semantics can now plausibly occupy the mediating role — retrieving,
translating, and re-contextualizing prior knowledge at the point of need — that the
socio-technical gap demands. This is the "why now": the socio-technical need is old, but
an assistant capable of filling it interactively, at low cost, and without adding tasks to
the user (§1.3) has only recently become feasible.

**Positioning.** Concretely, this design is the mechanism-level realization of the
*interactional layer* in a two-layer socio-technical model of collaborative ML — a
*structural layer* (the Deriva-ML data catalog) plus an *interactional layer* (an AI agent,
grounded in the catalog's semantics, that mediates explanation, coordination, and shared
understanding). It sits at the base of a four-level body of work: the **founding Deriva-ML
paper** (Li et al. 2024) defines the catalog this design layers on, including the cyclic
data-model/vocabulary co-evolution its schema-evolution mechanism instantiates; the
**AI-Ready-Ecosystems vision** (Kesselman & Schuler 2026) supplies the SCALE principles
and the agentic-infrastructure arc it conforms to; and the **interactional-layer study**
(Li & Kesselman 2026) supplies the two-layer model and the 19-month EyeAI field study that
motivates it (§4.9). This report contributes what those documents had no room for: the
mechanism-level design and its validation against the knowledge-management and
networks-of-practice literature — supplying the *mechanisms*, and the argument that they
are *theoretically sound*, behind a socio-technical need the upper documents frame.

### 1.3 Approach and contributions

The design's central principle is that **the system must align with the user's own
incentives rather than add tasks in service of a goal the user does not hold.** A
researcher at the keyboard is trying to *get work done* — to build an effective model —
not to produce reproducibility or to document rationale for a future stranger. Decades of
evidence show that asking users to invest additional up-front effort, even effort that
would demonstrably pay off later, is not a path to success. Carroll and Rosson's *paradox
of the active user* (1987) documents that users skip manuals and setup and dive straight
into the task because they are motivated by the immediate product, not the system — their
*production paradox*: the very motivation to get results suppresses the willingness to
invest in anything that is not the result. Behavioral economics gives the same finding a
mechanism: small frictions — an extra field, a confirmation, a "please tag this" prompt —
impose transaction costs that cause people to defer or abandon the action entirely
(Thaler and Sunstein's *sludge*; Sunstein 2019); good choice architecture removes friction
rather than adding it. And knowledge-management research names the specific failure this
produces for documentation: the *incentive asymmetry* between who does the recording work
(now) and who reaps the benefit (a later, different person), which, left to discretion,
drives contribution to a shared record toward zero (Grudin 1994; §4.5).

The design's answer is therefore not to make capture *easy* but to make it *invisible* —
to fold it into work the user is already doing for their own reasons. Concretely, **the
user must do nothing**: tacit knowledge accumulates in the background and is seamlessly
integrated; capture is automatic, retrieval is automatic, and the organizing structure
maintains itself. There is no command to invoke, no prompt to answer, no tagging chore.
Any design choice that would require a user action — that would put an additional task in
front of someone whose goal is elsewhere — is wrong by this principle. Reproducibility, in
this framing, is not a task the user performs but a *by-product* of the assistance they
accept because it advances the model they actually want to build.

We claim four contributions:

1. **A point-of-need capture-and-guidance loop** (§3) that makes decision rationale a
   by-product of normal ML work rather than a separate documentation burden.
2. **A theoretical account** (§4) that identifies what the system *is* (an automated
   knowledge intermediary over a boundary object), what it *can and cannot* honestly claim
   (the tacit/explicit limit), and *which mechanisms* the literature prescribes
   (point-of-need delivery, structural supersession, controlled-vocabulary grounding).
3. **A conceptual architecture** (§5) of four coupled layers — an append-only journal, a
   derived retrieval index, the evolving catalog boundary object, and human-gated
   refinement — unified by a single recurring discipline (controlled vocabulary +
   find-before-create + human-gated extension) applied at three levels.
4. **A requirement validation** (§7) of the system's four requirements against the
   literature, honest about where the design is sound, where it is reframed, and where it
   surfaces an open design decision.

The remainder of the report is organized as follows: §2 reviews the background research
(intent, why knowledge isn't reused, friction and incentives) that the design must
satisfy; §3 states the practical loop the whole design serves; §4 develops the
theoretical grounding; §5 gives the conceptual architecture; §6 summarizes the eleven
design decisions and their rationale; §7 validates the requirements; and §8 lists
references.

## 2. Background and related work

Three bodies of research jointly explain *why* the problem of §1 is hard and *what shape*
a solution must take. They concern (2.1) the primacy of the user's **intent**; (2.2) the
well-documented reasons **reusable knowledge does not get reused**; and (2.3) the
**friction and incentive** dynamics that determine whether any capture-and-reuse system is
actually used. These findings are the constraints the design of §5 is built to satisfy;
the design-specific theoretical grounding (boundary objects, supersession, provenance) is
developed in §4, which builds on this section.

### 2.1 Intent is primary — the user is building a model, not producing reproducibility

The organizing fact of this work is that a researcher at the keyboard has a **goal — build
an effective model — and everything the system offers must serve that intent** rather than
compete with it. This is not incidental framing; it is the pivot on which the rest turns.
Machine learning is an *experimental* activity (Li et al. 2024): the researcher's intent
is loosely specified and evolves — "find a subset that isn't biased," "get the model to
stop underperforming on this group" — and is rarely expressed as the structured operations
a data catalog understands. A long line of work on data-centric repositories shows that
the hard step is exactly this **translation of loosely-stated intent into precise,
structured action**: faceted, data-centric search is powerful but imposes a steep learning
curve, and new users "struggle to translate conceptual questions into the technical
constraints required to locate relevant data" (Kesselman & Schuler 2026). The role their
"virtual librarian" plays — and that this system generalizes — is to **meet the user's
intent and translate it**, not to ask the user to reformulate their intent in the system's
terms. Intent, therefore, is a first-class theme: the system aligns with it (§2.3),
translates it across disciplinary vocabularies (§5), and treats reproducibility as a
*by-product* of serving it rather than a separate goal imposed on the user.

### 2.2 Why reusable knowledge does not get reused

Even when knowledge is captured, *reuse* by someone other than the producer fails at a
high rate — and the literature is specific about why. **Markus (2001)**, in the foundational
theory of knowledge reuse, decomposes reuse into three roles — **producer, intermediary,
consumer** — and finds that **external reuse fails primarily from loss of context**:
knowledge is recorded by and for producers whose situation differs from the later
consumer's, and "producers rarely have the resources and incentives to do a good job of
repurposing knowledge" for a different audience. Her prescribed remedy is an
**intermediary** — human or technical — who re-contextualizes knowledge for the consumer.
This "context problem" recurs across the field: **Ackerman & Halverson (2000)** argue that
organizational memory is not a static store but a *reconstructive, situated process* — a
record stripped of its originating context is silently re-understood by whoever reuses it;
and the situated-cognition tradition (Brown, Collins & Duguid 1989) names the underlying
**decontextualization** mechanism directly.

A second, blunter failure is that **passive repositories go unread.** **Ye, Fischer &
Reeves (2000)** show reuse repositories fail because the user must both *know* the item
exists and *judge the search worth the effort* — their remedy is **active information
delivery** that "presents information without explicit queries." The empirical anchor is
stark: **Weber, Aha & Becerra-Fernandez (2000)** found that NASA/DOE/Navy lessons-learned
systems, despite significant investment, are **"rarely used"** — they succeed at
collect/store but fail at *disseminate/reuse*, because no one consults a standalone store
at the decision point. Together these findings prescribe the two load-bearing features of
this design: an **intermediary that re-contextualizes** (§2.1, §5) and **delivery at the
point of need** rather than a browsable archive (§5).

### 2.3 Friction and incentive alignment — why systems that add tasks fail

The deepest constraint is behavioral: **any system that puts an additional task in front
of a user whose goal lies elsewhere will be skipped**, regardless of its long-run value.
Three literatures converge on this. In HCI, Carroll and Rosson's **paradox of the active
user** (1987) documents that users refuse up-front investment — skipping manuals, setup,
and learning — because they are motivated by the immediate product, not the system; their
**production paradox** is that *the very motivation to get results suppresses the
willingness to do anything that is not the result.* In behavioral economics, small
**frictions ("sludge")** impose transaction costs that cause people to defer or abandon a
secondary action entirely (Thaler & Sunstein 2008; Sunstein 2019); good choice
architecture *removes* friction rather than adding it. And in knowledge management,
**Grudin (1994)** identifies the specific failure this produces for a shared record: the
**incentive asymmetry** between who does the recording work (a cost borne now) and who
reaps the benefit (a later, different person) — which, left to discretion, drives
contribution toward zero.

The design consequence is decisive and shapes every subsequent decision: the solution is
not to make capture *easy* but to make it **invisible** — to fold it into work the user is
already doing for their own intent, so that no task is added at all. This is the
**incentive-alignment principle** (developed in §4.3) that the "user must do nothing"
constraint operationalizes; §4.5 shows how LLM-mediated automatic capture dissolves the
active-user paradox, the friction, and the incentive asymmetry simultaneously.

## 3. The practical loop (the "why" of everything that follows)

The whole system is a three-moment loop, keyed on the **action**, never on a question
(a teammate never says "consult the knowledge base" — they just act):

1. **A team member states an action** — *"drop the low-confidence rows from the vehicle
   images before training."*
2. **The system retrieves and interjects *before* the action** — it finds a prior
   teammate's record about the same entity or the same kind of change, **quotes it**, and
   hands the decision back with options. This is the payoff: another member's months-old
   dead end stops a mistake in seconds.
3. **After the action, the system captures the new knowledge** — attributed to the
   current member — so the next teammate inherits this step too.

The accumulation is a **cross-team, cross-time asset**: knowledge built by other members
of the repository, retrieved automatically by whoever acts next. Everything below exists
to make Moment 2 land reliably and Moments 1/3 cost the user nothing.

## 4. Underlying theory

Building on the motivating research of §2, this section develops the theory specific to
*this* design — validated against the literature on tacit-knowledge acquisition and reuse
in collaborative settings and *networks of practice* (sources verified against
primary/publisher records; full reference list in §8). The theory does three things: it
**names what the system is** (an intermediary, not a repository), it **bounds what it can
honestly claim** (the tacit/explicit limit), and it **prescribes the mechanisms**
(point-of-need delivery, structural supersession, controlled-vocabulary grounding).

### 4.1 The governing frame — the LLM is a Markus "knowledge intermediary"

**Markus (2001)** decomposes knowledge reuse into three roles: the **producer**, the
**intermediary** (who indexes, standardizes, and *re-contextualizes* knowledge for an
audience unlike the producer), and the **consumer**. Her central empirical finding:
**external reuse fails at a high rate, primarily from loss of context**, because
producers "rarely have the resources and incentives to do a good job of repurposing
knowledge." Her prescribed fix is an intermediary — *human or technical*.

This is the strongest grounding for the whole design. Capture (a producer externalizing)
and consumption (a teammate acting) are exactly the two ends Markus says fail without a
broker between them; the retrieve-and-quote loop **is** that broker, running
automatically at the point of need. **The system is not a naïve repository — which the
literature repeatedly shows decays — but a repository *plus* an always-on intermediary,
the configuration the reuse literature actually endorses.**

The automated precedent is **Ackerman's Answer Garden (1998)**: retrieve a stored answer
at the point of need; when none exists, route to a human and fold the answer back in — a
self-growing memory. The system's extension beyond Answer Garden is that the LLM
*generates* the re-contextualization Answer Garden delegated to a human.

Why not just a browsable repository? Because passive repositories go unread. **Ye,
Fischer & Reeves (2000)** show repositories fail because the user must both *know* the
item exists and *judge the search worth the effort*; their remedy is **active
information delivery** ("presents information without explicit queries"). **Weber, Aha &
Becerra-Fernandez (2000)** supply the hard empirical anchor: NASA/DOE/Navy
lessons-learned systems, though well-intentioned, are **"rarely used"** — they fail at
dissemination/reuse because nobody consults a standalone store at the decision point.
The point-of-need auto-fire is precisely the fix these findings prescribe.

### 4.2 The broker's job scales with the boundary — Carlile's 3-T framework

**Carlile (2002, 2004)** studied how knowledge moves across boundaries between groups
(engineers, designers, marketers in new-product development). His **3-T framework**
identifies three boundary kinds of rising difficulty, each with a matching process:

- **Syntactic** (groups share a lexicon) → **transfer** — just move it.
- **Semantic** (same words, different meanings) → **translate** — negotiate common
  meaning.
- **Pragmatic** (different, sometimes competing, interests) → **transform** — jointly
  *change* what is known, a social/negotiated act the literature locates in **humans**.

This maps directly onto the broker's read behavior. When one ML engineer reads another's
record (syntactic), **quoting verbatim** is right. When a pathologist reads an ML
engineer's record (semantic — the "cross-domain bridge"), the broker must **translate**
into the reader's vocabulary. When the record touches competing interests (pragmatic —
e.g. evolving a shared schema), the broker must **surface the tension and hand to
humans**, never resolve it. This gives a principled account of *when the machine acts and
when it must defer.*

### 4.3 What half of the knowledge the system can legitimately move

The boundary the system spans is between **different communities of practice** — the
domain scientist, the data engineer, the computational/ML specialist (§1.1). Such
boundaries are *epistemic*, present even when the team is co-located; distribution and
turnover across a wider **network of practice** (Brown & Duguid, 2001; often held together
by weak ties, Granovetter, 1973) sharpen them but are not their source. Across either kind
of boundary the same limit holds, and **Hansen (1999)** states it precisely: **weak ties —
and, more generally, links between people who do not share a practice — are good at
*search* (locating that relevant knowledge exists) and at moving *codified* knowledge, but
hinder the transfer of *complex/tacit* knowledge, which needs strong ties and shared
practice.** This tells us exactly which half the system legitimately moves: the **search
half** (find the record) and the **codified shell** (articulable rationale) — the half
that crosses a practice boundary — while *pointing at*, not transmitting, the tacit
remainder, which only shared practice conveys. **Szulanski (1996)** adds the residual
barrier: *causal ambiguity* means lineage gives traceability but not the *why*, which is
why records must pair provenance with captured reasoning.

### 4.4 The honesty ceiling — what cannot be captured, and the naming overclaim

The strongest reading of the theory (**Polanyi, 1966**; **Tsoukas, 2003**; **Gourlay,
2006**; **Duguid, 2005**) holds that the genuinely *tacit* is **unwritable in
principle**: attending focally to a subsidiary particular in order to articulate it
destroys the role that made it work ("logically unspecifiable," "irreversible"). What
lands in the file is **articulable rationale** — precisely the part that was never
tacit. Tsoukas: tacit knowledge "cannot be captured, translated, or converted but only
displayed, manifested, in what we do." Duguid: codified *know-that* does not produce
practice-embedded *know-how*.

The honest model, therefore, is **an instrument of "instructive talk" / reminders**
(Tsoukas) — the finger, not the moon — whose payload is decision rationale, dead ends,
and conditions-of-validity, and which *points at* the tacit remainder it cannot hold.
The **name "tacit knowledge" is the design's single biggest overclaim**; the literature
would call it a *decision/rationale record* or *design memory*. (Renaming is deferred:
the name is load-bearing across the plugin, an MCP-prompt mirror, and session hooks —
a large, separate change.) The **ADR tradition** (Nygard, 2011) independently confirms
the *content* is right: context/forces-in-tension, decision, rejected alternatives,
consequences, and status/supersession.

### 4.5 The design's most defensible innovation — dissolving the capture-incentive asymmetry

This is where the incentive-alignment principle of §1.3 does its work, and it converges
from three literatures. **Carroll & Rosson (1987)** establish the behavioral fact — the
*production paradox*: a user motivated to get a result actively resists any effort that is
not the result, so extra up-front tasks are skipped even when they would pay off.
Behavioral economics supplies the mechanism — small **frictions / sludge** (Thaler &
Sunstein 2008; Sunstein 2019) impose transaction costs that push people to defer or
abandon a secondary action. And **Grudin (1994)** names the specific failure this produces
for a shared record: **the person who does the recording work (cost, now) is not the
person who benefits (a later reader)**, so left to discretion, records don't get written.
**The zero-touch, LLM-mediated auto-capture dissolves all three at once** — it removes the
extra task (Carroll & Rosson), the friction (sludge), and the cost side of the asymmetry
(Grudin); the human no longer pays anything to capture. This is the part of the design
most worth foregrounding, and it is *more* defensible than the "tacit knowledge" claim.
The predicted flip-side (Grudin, applied): zero-cost capture inverts *under*-supply into an
*over*-supply/noise problem — so a signal filter ("do not record routine lookups / tooling
chores with no rationale") becomes load-bearing.

### 4.6 Updating knowledge — append-only with structural supersession

New knowledge can invalidate old. The organizational-memory literature (**Walsh & Ungson,
1991**, on maladaptive automatic retrieval; **Levitt & March, 1988**, on the competency
trap; **Tsang & Zahra, 2008**: unlearning is *suspending authority*, not erasing) plus
the temporal-database and event-sourcing traditions converge on: **never delete; append a
superseding record and retire the old one from the *served* view.** The critical
refinement is **Yadav (2026)**: keeping both stale and current versions with only a text
marker serves the superseded fact **15–40 % of the time** under similarity retrieval;
the fix is a **structural** supersession relation that excludes the retired record from
default retrieval. Slogan: *never delete, but never serve a superseded record as if
current.*

### 4.7 Point-of-need delivery — supported, with two preconditions

The push-at-the-moment-of-action design is well supported (**Rhodes & Maes**, JITIR
agents; **Sweller**, cognitive load; **Eppler & Mengis**, information overload — a
whole knowledge base at once *degrades* decisions). But the interruption literature
(**Bailey & Konstan, 2006**; **Mark et al., 2008**) and automation-bias work
(**Parasuraman et al., 2000**) attach two hard preconditions: **(a) precision must be
high** — a wrong push doesn't merely add noise, it triggers the first-failure effect and
can irrecoverably erode trust; **(b) timing must ride a task boundary** — the same
information costs ~2× errors mid-task versus at a boundary. Firing **on the stated
action** is a natural boundary; the push must stay **ignorable**. Operative rule: *surface
only genuinely-relevant records; when unsure, stay silent — a false "you've done this
before" is worse than none.*

### 4.8 Provenance grounds trust

Each record carries author, timestamp, and support/supersession links forming a DAG.
**W3C PROV-DM (2013)** confirms this exact schema (`wasAttributedTo`, `wasRevisionOf`, a
DAG) exists *precisely to enable trust judgments*, and its `wasRevisionOf` is the direct
precedent for the supersession edge. Caveats the literature adds: attribution can mislead
(authority/halo bias — the supersession edge partly mitigates); trust from attribution is
fragile (the *sleeper effect*), so provenance must be **re-surfaced at each reuse**, not
assumed to stick.

### 4.9 Empirical grounding — the field-observed breakdowns this design addresses

The parent paper's 19-month EyeAI deployment is a "reproducibility stress test": robust
*structural* infrastructure (Deriva-ML) was already in place, yet reproducibility still
broke down — **not from missing artifacts, but from lost context and reasoning.** Its
Table 1 records five recurring interactional breakdowns; the design here is, layer by
layer, the response to them. This turns the design's motivating claim ("a future
teammate would need the rationale") from a hypothesis into a field observation.

| Field-observed breakdown (paper, Table 1) | Consequence in practice (paper) | Mechanism here |
|---|---|---|
| **Lost rationale over time** — *why* runs related, *why* results mattered | Handoffs needed meetings with original developers; hard to reuse prior work independently | The append-only journal of *why* (D1); retrieve-and-quote at point of need (§2) |
| **Incomplete experiment configurations** — param choices, ad-hoc script changes | Couldn't reproduce runs without asking the original developer | Capture-on-action (D7) + retrieval-before-action; provenance DAG (§4.8) |
| **Dataset version context not captured** — changing inclusion criteria, preprocessing | Models on "similar" datasets couldn't be reproduced | Entity-RID-anchored entries + structural supersession (D2) |
| **Provenance gaps from offline / exploratory work** | Reuse required reverse engineering and personal memory | Capture fires even for exploratory runs; the "don't fabricate rationale" honesty rule (§4.4) |
| **Loss of shared context** — understanding depended on original developers | Handoffs required meetings to reconstruct reasoning | The cross-team/cross-time intermediary loop (§4.1); cross-discipline translation (§5-layer-3) |

The paper further clusters these into three patterns — **alignment drift** (data/code/
environment evolving separately), **exploratory work outside the system**, and **loss of
shared context** — which are the same failure modes the knowledge-management literature
names abstractly (§4), now observed in a real interdisciplinary clinical project. The
paper's three derived **design goals** align one-to-one with this design: *maintain
alignment as work evolves* (supersession + the catalog-evolution return path, §5-layer-3);
*support exploration within system boundaries* ("vibe-modeling" — reproducibility comes
for free via the user's primary objective, §4.5); and *preserve informal context as
shared artifacts* (the journal itself). The paper also names, in its own words, the
mechanisms formalized here: the agent **"grounded in the semantics of the underlying ML
management system"** (§5-layer-3, catalog-grounded translation); the **"virtuous cycle"**
where conversations enrich artifact descriptions which improve guidance (the
catalog-grounding + desire-line return path, §5-layers 3–3a); and rationale accumulating
as **shared context linked to evolving artifacts** (the journal). *Caveat:* the paper
describes the interactional layer as a **prototype not yet longitudinally evaluated** —
so this report is the forward design of that layer, not a reported result.

### 4.10 Platform doctrine — this design is a SCALE-conformant instance

The grandparent vision document (Kesselman & Schuler, 2026) supplies the top-level
framework this design instantiates, and — importantly — independently states several of
this design's core positions as *platform doctrine*, which strengthens them beyond the
ML-literature grounding above.

- **SCALE principles.** The Deriva platform is built on **S**elf-service curation,
  domain-**A**gnostic platforms, **L**ightweight information models, and **E**volvable
  systems. Two are load-bearing here: **Self-service curation** rests on the premise that
  *"researchers possess unique tacit knowledge about their experimental conditions and
  methodological nuances that no third-party curator can match"* — the platform-level
  warrant for capturing tacit knowledge at all; and **Evolvable systems** ("schema
  evolution without costly migrations") is the doctrinal source of the
  catalog-evolution return path (§5-layer-3 / D10), academically grounded in Schuler et
  al. (2020), "Towards Co-Evolution of Data-Centric Ecosystems."
- **RAG is insufficient for structured scientific data (independent confirmation of the
  repo-local retrieval choice).** The vision doc argues conventional RAG "is
  fundamentally insufficient for scientific repositories" because traditional IR "favor[s]
  verbose documents over compact, structured descriptions," so "valuable datasets are
  frequently overlooked." This independently confirms the design's decision **not** to
  treat catalog semantic search / conventional RAG as the retrieval substrate for
  structured knowledge (§5-layer-2).
- **The "virtual librarian" is the intermediary, stated in platform language.** The
  FaceBase Chatbot "acts as an intelligent intermediary — much like a reference
  librarian … translat[ing] loosely defined scientific intent into the structured
  constraints required by a data-centric repository." This is the Markus-intermediary +
  Carlile-translate frame (§4.1–3.2) in the platform's own words; the agent *orchestrates*
  structured discovery rather than replacing it.
- **"Scientific fact guardrail" + model collapse — a stronger motivation for structural
  supersession.** The vision doc requires that "every synthesized answer is backed by
  explicit source attribution … anchoring agentic reasoning in verifiable knowledge
  rather than probabilistic inference alone," and names the risk it guards against:
  **model collapse**, where "unverified outputs fed into training data compound over
  time." This is the provenance-grounds-trust rule (§4.8) and the point-at-don't-fabricate
  honesty boundary (§4.4) — and model collapse is an *additional* reason a superseded
  record must be structurally retired from the served set (§4.6 / D2), not merely marked:
  a stale record served as current is exactly the unverified input the guardrail exists to
  keep out of downstream reasoning.

Net: the design is not only literature-sound (§4.1–3.8) and field-motivated (§4.9) but
also **doctrinally aligned** — it is what the SCALE/agentic-infrastructure vision
prescribes, made concrete for tacit knowledge.

## 5. The approach (conceptual architecture)

The system is four coupled layers, joined by one recurring discipline.

1. **An append-only journal (the record of *why*).** Decision rationale accumulates as a
   chronological, append-only log. Chronology *is* the structure — the log reads
   top-to-bottom as the project's history, and records reference prior records to form a
   support DAG. Supersession is additive and *structural*: a new record points at what it
   replaced, and the retired record is excluded from the served view but never deleted.

2. **A derived retrieval index (context-window economy).** Because there is no
   server-side semantic index for repo-author knowledge — it lives in git, travels with
   the code, and must work offline — retrieval is repo-local. A compact, **derived**
   index lets the LLM find the few relevant records without loading the whole journal
   into its context. The index is a regenerable *cache*, never an authority; it can only
   *accelerate* retrieval, never gate it (delete it and retrieval degrades to a full
   scan). It maintains itself as a silent, throttled side-effect of capture — no user
   action.

3. **The catalog as an *evolving* boundary object (the shared-syntax ground).** The
   scientific data catalog — controlled vocabularies, table/column descriptions, and
   stable identifiers that every discipline references — is a **boundary object** in the
   precise sense of **Star & Griesemer (1989)**: "plastic enough to adapt to local needs,
   yet robust enough to maintain a common identity across sites," and specifically their
   *repository* type. It is the **shared syntax** Carlile's translate-step requires. Two
   consequences: **(a)** the broker's cross-discipline translation is **grounded** in the
   catalog's controlled-vocabulary *synonyms* (bridging the words) and *descriptions*
   (bridging the meaning), rather than invented — closing the honesty gap of §4.4; and
   **(b)** the boundary object is not static — the Deriva platform is **evolvable by
   design** (a SCALE principle), and the founding Deriva-ML paper (**Li et al., 2024**)
   already defines vocabulary/schema evolution as a **cyclic best practice**: its
   seven-step process (Fig 4) *loops back*, ending with "Evolution of the Controlled
   Vocabulary and Data Model," and states that "the evolution of shared vocabulary is an
   essential aspect of collaboration." **So the catalog-evolution return path is not a
   novel addition here — it is the tacit-knowledge instantiation of a co-evolution cycle
   the platform already prescribes.** The accumulated journal is what *steers* that
   cycle: recurring patterns in the journal are **"desire lines"** (Merholz; **Halpin,
   2007**, on folksonomy→ontology) — worn paths that say *the schema should gain this
   column, or the vocabulary this term.* The distinction the return path rests on —
   evolving a vocabulary/ontology versus migrating a schema — is exactly **Noy & Klein
   (2004), "Ontology Evolution: Not the Same as Schema Evolution"**; the machinery that
   receives the desire line is **Schuler & Kesselman (2022), "Managing
   Database-Application Co-Evolution in a Scientific Data Ecosystem."** This closes the
   knowledge-spiral return path and relocates durable self-organization from the (small,
   single-team) journal to the (broad, cross-project) catalog — the layer that can
   actually bear it.

4. **The human in the loop (low-cost refinement of the bridge).** When catalog-grounded
   translation is thin or uncertain — no synonym exists, a description is stale, or two
   disciplines genuinely diverge — the broker **surfaces the gap to the human who is in
   the practice**, whose low-cost refinement feeds back into the catalog (add a synonym,
   sharpen a description) or the journal. This is Answer Garden's escalate-and-fold-back
   applied to *translation*, and Guy & Tonkin's "soft intervention" (suggest, never
   hard-rewrite). Crucially, **evolving the shared vocabulary is a *pragmatic*-boundary
   act (Carlile's transform)** — it changes what everyone depends on — so it stays
   **human-gated**: the system *proposes and recommends*; a human *decides and evolves*.

**The recurring discipline — controlled vocabulary + find-before-create + human-gated
extension — operates at all three structural layers**, which is the design's unifying
idea:

- at the **catalog** layer, steering schema/CV evolution (layer 3);
- at the **translation** layer, grounding cross-discipline reads (layer 3a);
- at the **journal-classification** layer, controlling how records are tagged (below).

On that last point: because the **only tagger is the LLM**, the classic folksonomy
failure modes (personal vocabularies, typos, inter-person drift) do not apply — a single
consistent tagger avoids them. The residual risk is *temporal* drift (the one tagger
inventing different terms for the same thing across sessions). The fix is the same
discipline again: classify records against a **controlled topic vocabulary** via
find-before-create, so the vocabulary supplies the cross-session memory the single tagger
lacks. The controlled vocabulary *is* the noise control — and the terms it keeps failing
to match are themselves desire lines feeding layer 3.

## 6. Summary of decisions and rationale

The full mechanics are specified in the companion implementation spec (decision IDs
D1–D11 are shared between the two documents). One line each:

| ID | Decision | Why (one line) |
|----|----------|----------------|
| **D1** | Storage stays an append-only journal, **not** a per-fact bundle | Preserves chronology-as-structure, the in-document support DAG, and append-only integrity; partition by *time* not *topic* if ever needed |
| **D2** | Supersession is an **additive, structural** edge (never delete) | New record points at what it replaced; the retired record is **excluded from the served view** — Yadav (2026): text markers alone serve stale facts 15–40 % of the time |
| **D3** | Retrieval is **repo-local** (no server index for this knowledge) | Repo-author knowledge lives in git, travels with the code, works offline; can't live in a catalog index |
| **D4** | A **derived, whole-rebuilt** index as accelerator | A regenerable cache, never an authority; can only accelerate, never gate — a builder bug costs speed, not correctness |
| **D5** | Retrieval = index for candidates **+ grep the un-indexed tail** | Bounds context cost; the tail-grep guarantees just-written records are never missed; index is pure upside |
| **D6** | Index starts **flat**; clustering is a later, migration-free layer | Entity-lookup is the high-value path; clustering adds non-determinism and helps only a rarer query; flat-now costs nothing later |
| **D7** | Index rebuild is a **silent, throttled side-effect of capture** | Zero-touch: no user-invoked skill; amortized every *N* records; safe to be lazy because the tail-grep covers the gap |
| **D8** | Domain background → a separate `Concept` surface, one retrieval loop | Domain understanding is *semantic*, not *episodic*; forcing it into the dated journal fights its nature — but link the catalog term, don't restate it |
| **D9** | The **catalog is a boundary object**; controlled vocab grounds translation; human refines the bridge cheaply | Grounds cross-discipline translation in synonyms + descriptions (closing the honesty gap); human fold-back supplies what a single-team log can't |
| **D10** | The boundary object **evolves**; the journal is the **desire-line** signal that steers it (human-gated) | Closes the knowledge-spiral return path; relocates durable self-organization to the broad catalog layer; promotion is a pragmatic-boundary act → human-gated |
| **D11** | Records are classified against a **repo-local topic vocabulary** — seeded with an LLM-hypothesized set of keywords and continuously refined, not free-tagged | The sole tagger (the LLM) drifts *temporally*; a controlled vocabulary is its cross-session memory and the noise control. Because a project's N is permanently small (no folksonomy emergence to wait for), the vocabulary is **seeded richly up front** by a bundled setup script — spanning **entity-anchored axes** (the five abstractions) *and* **entity-free axes** (process, domain, tooling, team — since much TK is not about a catalog object) — then refined each index rebuild by an LLM keyword-discovery pass (add/retire/split/merge), all human-gated. Feeds D10's desire-line signal |

## 7. Requirement validation (verdicts)

Four requirements were stated up front for the tacit-knowledge system; each was
validated against the literature. **These are labelled TK-R1…TK-R4 to avoid collision
with the Deriva-ML root paper's own R1–R4** (Data-centric / Comprehensive / Adaptive /
Socio-technical — Li et al. 2024, §III), which are the *platform's* requirements, not
these. The two sets are complementary: the platform's R1–R4 shape the structural layer;
TK-R1…TK-R4 shape this interactional layer on top of it.

- **TK-R1 — Context-economy retrieval → ✔.** The index + point-of-need auto-fire is the
  passive-repository fix the literature prescribes (Ye/Fischer/Reeves; Answer Garden),
  and avoids the "rarely used" failure (Weber/Aha).
- **TK-R2 — Self-organize over time → ✔, reframed.** The strong self-organization is the
  journal steering *catalog* evolution (D10), not the journal self-clustering; with a
  single LLM tagger, a controlled topic vocabulary (D11) supplies the structure by
  construction.
- **TK-R3 — Update knowledge → ✔.** Append-only-with-*structural*-supersession is the
  right anti-stale pattern (Yadav; the organizational-memory + event-sourcing
  traditions); the broker actively surfacing the tombstone operationalizes the hard
  "unlearning" step.
- **TK-R4 — Consult for guidance + capture domain background → partially, and it surfaced
  a real design addition.** Consult is well supported (SECI internalization). "Capture
  domain background" is a *different knowledge type* (semantic vs. episodic) → a separate
  `Concept` surface (D8), consulted by the same loop, with a hard honesty boundary: point
  at the tacit remainder (the catalog term + the human who practices it), don't pretend
  to contain it.

**Overarching validation:** the system is a **repository + an automated Markus
intermediary, grounded in an evolving boundary object, with human-gated refinement of the
shared vocabulary** — a configuration the reuse literature endorses over a bare
repository, honest about the tacit/explicit limit it cannot cross.

## 8. References

Verified against primary/publisher records during the validation.

**Document lineage (this design is the interactional layer, built SCALE-conformant).**
*Founding paper:* Li, Kesselman, D'Arcy, Pazzani & Xu, "Deriva-ML: A Continuous FAIRness
Approach to Reproducible Machine Learning Models," arXiv:2407.01608 (IEEE e-Science
2024) — defines the five ML abstractions, the two-schema catalog, the platform's R1–R4
(Data-centric/Comprehensive/Adaptive/Socio-technical), and the **cyclic** data-model/CV
co-evolution best practice (Fig 4) that D10 instantiates. *Vision:* Kesselman & Schuler,
"Building AI-Ready Scientific Data Ecosystems: From FAIR Principles to Intelligent Agent
Integration" (2026, NIH U24DE034163) — the SCALE framing. *Interactional-layer study:*
Li & Kesselman, "Reproducibility Beyond Artifacts," submitted to ACM (2026) — grounded in
the 19-month EyeAI deployment. *Catalog-evolution (D10) grounding:* **Noy & Klein,
"Ontology Evolution: Not the Same as Schema Evolution," *Knowledge and Information
Systems* (2004)** — the exact distinction D10 rests on; **Schuler & Kesselman, "Managing
Database-Application Co-Evolution in a Scientific Data Ecosystem" (e-Science 2022)** — the
co-evolution machinery that receives the desire line; Schuler et al., "Towards
Co-Evolution of Data-Centric Ecosystems" (SSDBM 2020). *Platform basis:* Bugacov et al.,
"Experiences with DERIVA" (e-Science 2017); Schuler et al., "FaceBase: A Community-Driven
Hub" (*J Dent Res* 2022); Li et al., "From Data to Decision" (e-Science 2025); Wilkinson
et al., "The FAIR Guiding Principles" (*Scientific Data* 2016). On the model-collapse /
fact-guardrail motivation for structural supersession: platform doctrine in the vision
document (§7.3).

**Reproducibility crisis & the value of data/context work:** Kapoor & Narayanan, "Leakage
and the Reproducibility Crisis in Machine-Learning-Based Science," *Patterns* 4(9) (2023) —
329 papers across 17 fields; Sambasivan et al., "'Everyone Wants to Do the Model Work,
Not the Data Work': Data Cascades in High-Stakes AI," *CHI* (2021); Semmelrock et al.,
"Reproducibility in Machine-Learning-Based Research: Overview, Barriers, and Drivers,"
*AI Magazine* (2025); and — for the beyond-artifacts thesis — the parent paper (Li &
Kesselman 2026, above).

**Socio-technical systems & AI-assisted work:** Trist & Bamforth, "Some Social and
Psychological Consequences of the Longwall Method of Coal-Getting," *Human Relations*
(1951) — the founding socio-technical-systems study; Bauer & Herder, "Designing
Socio-Technical Systems," in *Philosophy of Technology and Engineering Sciences* (2009);
Sergeyuk et al., "Human-AI Experience in Integrated Development Environments: A Systematic
Literature Review," *Empirical Software Engineering* (2026); GitHub Copilot agent mode
(2025) as an instance of embedded, context-aware AI assistance in everyday software work.

**Tacit knowledge & its limits:** Polanyi, *The Tacit Dimension* (1966); Nonaka (1994) /
Nonaka & Takeuchi, SECI (1995); Tsoukas (2003) and Gourlay (2006), critiques of
tacit→explicit conversion; Cook & Brown, "Bridging Epistemologies," *Org. Sci.* (1999);
Duguid, "The Art of Knowing," *The Information Society* 21(2) (2005).

**Communities / networks of practice & stickiness:** Lave & Wenger, *Situated Learning*
(1991); Wenger (1998); Brown & Duguid, "Knowledge and Organization," *Org. Sci.* 12(2)
(2001) and *The Social Life of Information* (2000); Orr, *Talking About Machines* (1996);
Granovetter, "The Strength of Weak Ties," *AJS* (1973); Szulanski, "Exploring Internal
Stickiness," *SMJ* (1996); von Hippel, "Sticky Information," *Mgmt Sci.* (1994); Hansen,
"The Search-Transfer Problem," *ASQ* (1999).

**Knowledge reuse, intermediaries & boundary objects:** Markus, "Toward a Theory of
Knowledge Reuse," *JMIS* 18(1) (2001); Ackerman, "Augmenting the Organizational Memory:
Answer Garden," *ACM TOIS* 16(3) (1998); Ackerman & Halverson, "Reexamining
Organizational Memory," *CACM* (2000); Star & Griesemer, "Institutional Ecology...
Boundary Objects," *Social Studies of Science* (1989); Star, "This Is Not a Boundary
Object" (2010); Carlile, *Org. Sci.* (2002) and (2004); Burt, "Structural Holes and Good
Ideas," *AJS* (2004); Hargadon & Sutton, "Technology Brokering," *ASQ* (1997); Ye,
Fischer & Reeves, FSE-8 (2000); Weber, Aha & Becerra-Fernandez, AAAI (2000).

**Incentive alignment & capture cost:** Carroll & Rosson, "The Paradox of the Active
User," in *Interfacing Thought: Cognitive Aspects of Human-Computer Interaction*, MIT
Press (1987) — the production paradox; users won't invest up-front effort even when it
pays off; Thaler & Sunstein, *Nudge* (2008) and Sunstein, "Sludge and Ordeals," *Duke Law
Journal* (2019) — friction/sludge causing task deferral and abandonment; Grudin,
"Groupware and Social Dynamics," *CACM* (1994) and CSCW (1988) — the who-does-the-work-vs-
who-benefits asymmetry.

**Design rationale:** Nygard, "Documenting Architecture Decisions" (2011); Conklin &
Begeman, gIBIS (1988); Horner & Atwood (2006); Orlikowski, "Learning from Notes," CSCW
(1992).

**Self-organization / emergent structure:** Shirky, "Ontology Is Overrated" (2005);
Golder & Huberman, *J. Info. Sci.* (2006); Halpin, Robu & Shepherd, WWW (2007); Vander
Wal (broad vs. narrow folksonomy, 2005); Mathes (2004); Guy & Tonkin (2006); Glaser &
Strauss, *The Discovery of Grounded Theory* (1967).

**Organizational memory, obsolescence & supersession:** Walsh & Ungson, "Organizational
Memory," *AMR* (1991); Stein & Zwass, *ISR* (1995); Levitt & March, "Organizational
Learning," *Ann. Rev. Sociology* (1988); Hedberg (1981); de Holan & Phillips, *Mgmt Sci.*
(2004); Tsang & Zahra, *Human Relations* (2008); Argote, Beckman & Epple, *Mgmt Sci.*
(1990); temporal/bitemporal-database & event-sourcing patterns; Yadav, "Temporal Validity
in Retrieval Memory," arXiv:2606.26511 (2026).

**Point-of-need delivery & trust:** Rhodes & Maes, "Just-in-Time Information Retrieval
Agents," *IBM Sys. J.* (2000); Sweller, cognitive load (1988); Eppler & Mengis,
information overload (2004); Bailey & Konstan (2006); Mark, Gudith & Klocke, CHI (2008);
Parasuraman, Sheridan & Wickens (2000); W3C PROV-DM (2013); Buneman, Khanna & Tan (2001);
Groth, Gibson & Velterop, nanopublications (2010); Hovland & Weiss (1951); Metzger,
Flanagin & Medders (2010).
