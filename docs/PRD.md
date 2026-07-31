# Frontier GoWild Destination Explorer

## Product Requirements Document (PRD)

**Version:** 1.0
**Status:** Initial Specification
**Author:** ChatGPT
**Target Audience:** Software Engineers, AI Coding Agents, Product Designers

---

# 1. Executive Summary

## Problem

Frontier GoWild Pass users currently have no efficient way to discover all destinations they can realistically travel to on a specific day.

The existing booking experience requires users to manually search every destination individually, making spontaneous travel planning tedious.

Current third-party solutions exist but typically require paid subscriptions.

---

## Goal

Build an application that allows a GoWild Pass holder to:

* Select a departure airport.
* Select a departure date.
* View every reachable Frontier destination.
* View direct and connecting options.
* View estimated or live GoWild pricing.
* Filter and sort results.
* Open Frontier to complete booking.

The application should prioritize speed, ease of exploration, and low infrastructure cost.

---

# 2. Product Vision

The application should become the fastest way for a Frontier GoWild Pass holder to answer one question:

> "Where can I fly today?"

Eventually the product should evolve into an intelligent travel assistant capable of answering questions such as:

* Where can I go for under $30?
* Where is warm this weekend?
* Show beach destinations.
* Show destinations with cheap hotels.
* Find the cheapest weekend trip.

---

# 3. Scope

## Phase 1 (MVP)

Included:

* Airport selection
* Date selection
* Frontier route search
* Direct flights
* One-stop itineraries
* Estimated GoWild pricing
* Flight duration
* Total travel time
* Connection information
* Filters
* Sorting

Excluded:

* Hotel booking
* Flight booking
* User accounts
* Notifications
* Return-trip optimization
* AI recommendations

---

## Phase 2

Included:

* Live GoWild availability
* Accurate taxes/fees
* Cached search results
* Availability confidence

---

## Phase 3

Included:

* AI travel recommendations
* Weather integration
* Hotel prices
* Attractions
* Alerts
* Saved destinations

---

# 4. User Personas

## Persona 1

GoWild Weekend Traveler

Needs:

"I have Friday off."

"I live in Atlanta."

"Show me everywhere I can go."

---

## Persona 2

Budget Traveler

Needs:

"Only show destinations under $25."

---

## Persona 3

Explorer

Needs:

"I don't care where."

"Show the coolest destinations."

---

# 5. Functional Requirements

## Search Inputs

Required

Departure Airport

Date

Optional

Maximum Connections

* Direct only
* One stop

Departure Time

Arrival Time

Maximum Flight Duration

Maximum Total Travel Time

Domestic Only

International Only

Maximum Estimated Cost

Destination Search

Weather Preference (future)

Beach

Mountains

City

Nightlife

Family Friendly

---

## Search Output

Each result contains:

Destination

Airport Code

City

Country

Flight Number(s)

Departure Time

Arrival Time

Connection Airport

Connection Duration

Flight Duration

Total Travel Time

Estimated GoWild Price

Actual GoWild Price (Phase 2)

Availability Status

Confidence

Open in Frontier Button

---

## Filters

Estimated Price

Travel Time

Flight Duration

Departure Time

Arrival Time

Connections

Domestic

International

Weekend Trips

---

## Sorting

Cheapest

Shortest Flight

Shortest Total Travel Time

Earliest Departure

Latest Departure

Alphabetical

Most Popular

---

# 6. User Stories

As a GoWild user,

I want to enter ATL,

so that I can see every possible destination.

---

As a traveler,

I want to sort by price,

so I can maximize my value.

---

As a traveler,

I want direct flights only,

so I avoid long layovers.

---

As a traveler,

I want to open Frontier booking,

so I can purchase immediately.

---

# 7. System Architecture

Frontend

Next.js

React

TypeScript

TailwindCSS

Mapbox (optional)

---

Backend

Python FastAPI

or

Next.js API Routes

---

Database

PostgreSQL

Hosted on Supabase

---

Cache

Redis (optional)

---

Hosting

Frontend

Vercel

Backend

Railway

Render

Fly.io

---

# 8. Database Schema

## Airports

```text
airport_code

city

country

latitude

longitude

timezone
```

---

## Routes

```text
origin

destination

effective_start

effective_end

operating_days
```

---

## Flights

```text
flight_number

origin

destination

departure_time

arrival_time

arrival_day_offset
```

---

## Availability Snapshot

```text
origin

destination

departure_date

price

currency

availability

checked_at

confidence

source
```

---

# 9. Search Engine Requirements

The search engine must NOT rely on an LLM.

Use deterministic graph traversal.

Algorithm

Load all flights leaving origin.

Filter by operating date.

Generate direct routes.

Generate one-stop routes.

Remove impossible layovers.

Calculate travel time.

Calculate segment count.

Estimate GoWild cost.

Sort.

Return.

Complexity target:

<1 second for normal searches.

---

# 10. Pricing Logic

Phase 1

Estimate

Domestic

Base estimate:

~$15 per segment

International

Unknown until lookup

Label:

Estimated

---

Phase 2

Retrieve

Taxes

Airport Fees

Government Fees

Actual GoWild Price

Label:

Live

---

# 11. AI Requirements

LLM Responsibilities

Natural language search

Example

"I want somewhere warm under $40."

↓

Convert into structured filters.

Explain itineraries.

Recommend destinations.

Generate summaries.

---

LLM MUST NOT

Compute routes

Calculate prices

Predict availability

Replace deterministic logic

---

Recommended Models

OpenAI GPT-5.6 Terra

Claude Sonnet 5

Claude Opus 5

No reasoning model required for normal searches.

---

# 12. Data Sources

Priority

Official Frontier API

If available

Otherwise

Authorized third-party APIs

Otherwise

Manual schedule dataset

Website automation only if legally permitted.

---

# 13. API Design

GET

/search

Parameters

origin

date

max_connections

max_cost

direct_only

Returns

```json
{
  "results":[]
}
```

---

GET

/destination/{airport}

Returns airport metadata.

---

GET

/routes

Returns supported Frontier routes.

---

# 14. UI Requirements

Home Screen

Origin Selector

Date Picker

Search Button

---

Results Page

Cards

List View

Map View

Filters

Sort

---

Each Result Card

Destination

Airport

Price

Travel Time

Connections

Availability

Book Button

---

# 15. Performance Requirements

Search response

<1 second

API latency

<500ms

Cold boot

<2 seconds

Frontend

Responsive

Mobile-first

---

# 16. Error Handling

No flights

Display:

"No Frontier destinations available."

Unknown pricing

Display:

"Price unavailable."

API timeout

Retry once

Show cached result

---

# 17. Future Features

Hotel prices

Weather

Google Maps attractions

Trip scoring

Favorite destinations

Price alerts

Weekend planner

Calendar view

Travel history

Passport reminders

Travel restrictions

Airport lounges

Packing recommendations

---

# 18. Security

No Frontier passwords stored.

Secrets encrypted.

HTTPS only.

Rate limiting.

Input validation.

Server-side API keys.

---

# 19. Analytics

Track

Search origin

Search destination

Filters used

Average search time

Popular airports

Search success rate

---

# 20. Development Roadmap

Sprint 1

Repository

CI/CD

Database

Airport dataset

---

Sprint 2

Search backend

Route generation

Filters

---

Sprint 3

Frontend

Results

Map

---

Sprint 4

Price estimation

Caching

Testing

---

Sprint 5

Live availability integration

---

Sprint 6

AI search

Recommendations

Alerts

---

# 21. Stretch Features

Interactive map with reachable destinations

Multi-day calendar

Weekend optimizer

Hotel integration

Rental car integration

AI itinerary generator

Budget estimator

Weather forecasting

Travel recommendations

Export itinerary

Shareable links

Mobile application

---

# 22. Non-Functional Requirements

Availability

99.9%

Scalability

Support 10,000+ daily searches.

Maintainability

Strong typing

Unit tests

Integration tests

OpenAPI documentation

Accessibility

WCAG AA

Responsive design

Cross-browser support

---

# 23. Success Metrics

Search completion time under one second.

95%+ successful search execution.

Less than 1% backend error rate.

Accurate route generation.

Positive user feedback regarding ease of discovering destinations.

---

# 24. Open Questions

1. Can Frontier's official APIs expose GoWild inventory?
2. Are there commercial restrictions on automated search?
3. Should authentication be added for saving preferences?
4. Will one-stop itineraries be enabled by default?
5. Should round-trip planning be introduced in MVP or deferred?
6. What cache lifetime balances freshness with API usage?
7. How should unavailable pricing be represented in the UI?

---

# 25. Agent Work Breakdown

## Agent 1 – Backend

* Design database schema.
* Build route graph engine.
* Implement deterministic search.
* Build REST API.
* Implement caching.

Deliverables:

* FastAPI service
* PostgreSQL schema
* OpenAPI specification
* Unit tests

---

## Agent 2 – Frontend

* Build Next.js application.
* Implement search form.
* Create results page.
* Add filters and sorting.
* Ensure responsive design.

Deliverables:

* Production-ready UI
* Component library
* End-to-end tests

---

## Agent 3 – Data Integration

* Evaluate official Frontier developer/NDC APIs.
* Integrate authorized schedule sources.
* Normalize schedule data.
* Design synchronization jobs.
* Implement availability snapshot ingestion.

Deliverables:

* Data ingestion service
* Normalized schema
* Synchronization documentation

---

## Agent 4 – AI Features

* Implement natural-language search.
* Translate user intent into structured filters.
* Generate destination summaries.
* Build recommendation prompts.
* Evaluate model latency and cost.

Deliverables:

* Prompt library
* Tool-calling implementation
* Recommendation service
* Evaluation report

---

## Agent 5 – QA & DevOps

* Configure CI/CD.
* Implement monitoring.
* Load test search endpoints.
* Validate accessibility.
* Create deployment pipelines.

Deliverables:

* Automated test suite
* Performance benchmarks
* Deployment documentation
* Monitoring dashboards
