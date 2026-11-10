# Tasks: Timeframe Parameterization

**Input**: Design documents from `/specs/002-timeframe-parameterization/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Set the feature baseline and align configuration around a supported interval contract.

- [x] T001 Define supported interval values and default cadence in src/trot/config.py and src/trot/models.py
- [x] T002 [P] Review existing data and backtest fixtures in tests/test_data.py and tests/test_backtest.py to prepare interval-aware regression coverage

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared validation and range logic that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Implement interval-aware validation helpers in src/trot/data.py for timezone, contiguity, and completed-bar checks
- [x] T004 [P] Add interval-aware series rejection paths for gaps, duplicates, stale, and impossible ranges in src/trot/data.py
- [x] T005 [P] Ensure config defaults preserve daily behavior while allowing an explicit override in src/trot/config.py
- [x] T006 Add run metadata capture for selected interval and dataset identity in src/trot/backtest.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Preserve the default daily workflow (Priority: P1) 🎯 MVP

**Goal**: Keep the existing daily BTC/EUR behavior stable when no interval override is provided.

**Independent Test**: A historical daily backtest without a custom interval should match the current output semantics and remain deterministic across repeated runs.

### Tests for User Story 1

- [x] T007 [P] [US1] Add regression tests for default daily behavior and repeatable results in tests/test_backtest.py
- [x] T008 [P] [US1] Add CLI default-interval checks in tests/test_cli.py for the no-override path

### Implementation for User Story 1

- [x] T009 [US1] Preserve daily default handling in src/trot/main.py when `--interval` is omitted
- [x] T010 [US1] Ensure default daily results remain deterministic and continue to use the existing benchmark metadata in src/trot/backtest.py
- [x] T011 [US1] Confirm daily metric output and run labels remain consistent with the current contract in src/trot/backtest.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Support hourly data and next-bar execution (Priority: P1)

**Goal**: Allow hourly BTC/EUR market data and ensure strategy decisions execute only on the next valid bar open.

**Independent Test**: A valid hourly dataset can be loaded, evaluated, and reported without look-ahead or same-close fills.

### Tests for User Story 2

- [x] T012 [P] [US2] Add failing hourly data tests in tests/test_backtest.py for next-bar execution and deterministic hourly runs
- [x] T013 [P] [US2] Add CLI tests for explicit hourly interval selection and validation in tests/test_cli.py

### Implementation for User Story 2

- [x] T014 [US2] Add interval-aware execution cadence logic in src/trot/backtest.py so signals occur on completed candles and fills happen on the next valid bar open
- [x] T015 [US2] Update CLI parsing and validation in src/trot/main.py to accept an explicit `--interval` override and fail on unsupported values
- [x] T016 [US2] Extend dataset loading and range filtering in src/trot/main.py to respect the selected interval while preserving daily defaults
- [x] T017 [US2] Validate hourly metadata propagation and run output in src/trot/backtest.py so the report clearly identifies the active interval

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Reject invalid interval data early and clearly (Priority: P2)

**Goal**: Fail visibly on unsupported intervals, incomplete datasets, duplicates, or impossible requested ranges before producing results.

**Independent Test**: Invalid data and unsupported interval selections are rejected with a clear error and no misleading output.

### Tests for User Story 3

- [x] T018 [P] [US3] Add negative tests in tests/test_data.py for unsupported intervals, missing bars, and duplicate timestamps
- [x] T019 [P] [US3] Add CLI error-path tests in tests/test_cli.py for invalid interval values and impossible range selection

### Implementation for User Story 3

- [x] T020 [US3] Add unsupported-interval rejection and error messaging in src/trot/config.py and src/trot/data.py
- [x] T021 [US3] Ensure impossible requested ranges and stale/incomplete history fail before backtest output in src/trot/main.py
- [x] T022 [US3] Add interval-aware failure handling and run rejection messaging in src/trot/backtest.py
- [x] T023 [US3] Verify the scenarios in specs/002-timeframe-parameterization/quickstart.md and confirm the feature behaves as documented

**Checkpoint**: All user stories should be independently functional and validated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, clean-up, and proof that the feature works end-to-end within the project constraints.

- [x] T024 [P] Review and align interval semantics across src/trot/config.py, src/trot/data.py, src/trot/backtest.py, and src/trot/main.py
- [x] T025 [P] Run the focused validation suite for this feature, including default daily, hourly, and invalid-data scenarios
- [x] T026 Confirm the generated output and metadata in specs/002-timeframe-parameterization/quickstart.md still match the implementation
- [x] T027 [P] Final cleanup of interval naming, validation messaging, and feature documentation to keep the codebase consistent

---

## Phase 7: Close Download and Walk-Forward Coverage Gaps

**Purpose**: Verify interval-aware historical downloads end to end and make hourly chronological validation explicit.

- [x] T028 [P] Add hourly download CLI regression coverage in tests/test_cli.py for interval forwarding, UTC date bounds, completed-candle filtering, Parquet manifest interval, and clear no-data behavior
- [x] T029 [P] Add historical-range pagination regressions in tests/test_exchange.py for exchanges that cap responses or return a newer page than the requested window
- [x] T030 Fix interval-aware OHLCV pagination and download empty-result handling in src/trot/exchange.py and src/trot/main.py; ensure pagination advances toward the requested range and no dataset is written when no completed candles are available
- [x] T031 Add hourly walk-forward regression coverage in tests/test_backtest.py and ensure fold metrics include only the specified chronological test window
- [x] T032 Verify the download and hourly walk-forward scenarios in specs/002-timeframe-parameterization/quickstart.md and run the focused plus full pytest suites

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion
  - User Story 1 can be implemented and validated independently
  - User Story 2 can proceed after the shared validation layer is stable
  - User Story 3 can proceed once invalid-range rejection is in place
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories; daily behavior is the default baseline
- **User Story 2 (P1)**: Depends on the shared validation layer, but should still be independently testable
- **User Story 3 (P2)**: Depends on the same interval validation framework and should be independently testable

### Parallel Opportunities

- T001 and T002 can run in parallel during Setup
- T003, T004, and T005 can run in parallel after Setup completes
- The tests marked [P] within each story can be written in parallel
- Story-specific implementation tasks can be explored in parallel once the Foundational phase is complete

---

## Parallel Example: User Story 2

```bash
# Launch both test tasks for User Story 2 together
Task: "Add failing hourly data tests in tests/test_backtest.py"
Task: "Add CLI tests for explicit hourly interval selection in tests/test_cli.py"

# Launch core implementation tasks for the same story after the tests fail
Task: "Add interval-aware execution cadence logic in src/trot/backtest.py"
Task: "Update CLI parsing and validation in src/trot/main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm default daily behavior remains deterministic
5. Deploy or demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → foundation ready
2. Add User Story 1 → validate independently → keep daily default stable
3. Add User Story 2 → validate hourly execution and metadata
4. Add User Story 3 → validate invalid-data handling and producer safety
5. Run final polish and regression checks

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files or separate validation paths with no hard dependency on incomplete work
- [Story] label maps tasks to the specific user story for traceability
- Each user story remains independently completable and testable
- The feature keeps daily as the default, adds hourly support, and rejects invalid interval data instead of repairing it
