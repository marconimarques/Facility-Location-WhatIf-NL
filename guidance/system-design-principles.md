# System Design Principles

## Purpose
This document establishes the engineering standards for building maintainable, scalable, and debt-free systems. These are not suggestions—they are requirements for engineering excellence.

---

## 1. Architecture Principles

### 1.1 Separation of Concerns
- **Each module has ONE responsibility**. If a module does multiple things, split it.
- **Business logic lives separate from infrastructure code**. No database queries mixed with business rules.
- **Layers must not be bypassed**. Data flows through defined boundaries: Presentation → Application → Domain → Infrastructure.

### 1.2 Dependency Direction
- **Dependencies point inward**. Outer layers depend on inner layers, never the reverse.
- **Use dependency injection**. Hard-coded dependencies create untestable, rigid code.
- **Interfaces over implementations**. Depend on abstractions, not concrete classes.

### 1.3 SOLID Principles (Non-Negotiable)
- **S**ingle Responsibility: One reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Subtypes must be substitutable for their base types
- **I**nterface Segregation: Many specific interfaces > one general interface
- **D**ependency Inversion: Depend on abstractions, not concretions

---

## 2. Code Organization

### 2.1 Project Structure
```
/src
  /domain          # Business entities, value objects, domain services
  /application     # Use cases, application services, DTOs
  /infrastructure  # Database, external APIs, frameworks
  /presentation    # Controllers, API routes, UI adapters
  /shared          # Cross-cutting concerns (logging, validation)
```

### 2.2 File Naming Conventions
- **Be explicit**: `UserRepository.py`, not `repo.py`
- **Match purpose**: `CalculateShippingCost.py` for a use case
- **Avoid generic names**: No `utils.py`, `helpers.py`, or `manager.py` without context

### 2.3 Module Size
- **Files should be < 300 lines**. If longer, refactor.
- **Functions should be < 50 lines**. If longer, decompose.
- **Classes should have < 10 public methods**. If more, split responsibilities.

---

## 3. Design Patterns to Use

### 3.1 Repository Pattern
- **All data access goes through repositories**. Never query databases directly in business logic.
- **One repository per aggregate root**. Don't create god repositories.

### 3.2 Service Layer
- **Application services orchestrate use cases**. They coordinate domain objects but contain no business logic.
- **Domain services contain business logic** that doesn't fit in a single entity.

### 3.3 Factory Pattern
- **Complex object creation uses factories**. Don't clutter constructors with initialization logic.

### 3.4 Strategy Pattern
- **For algorithmic variations**, use strategies. Avoid if/else chains for behavior selection.

### 3.5 Command Pattern
- **For operations that need to be queued, logged, or undone**, use commands.

---

## 4. Data Management

### 4.1 Domain Models
- **Rich domain models over anemic models**. Objects should contain behavior, not just data.
- **Encapsulation is mandatory**. No public setters without business rule validation.
- **Value objects are immutable**. If something has no identity, make it a value object.

### 4.2 Database Access
- **Use ORMs properly**. Understand lazy loading, N+1 queries, and transaction boundaries.
- **No raw SQL in business logic**. If you need raw SQL, it lives in the infrastructure layer.
- **Migrations are code**. Database changes must be versioned and reviewed.

### 4.3 Data Validation
- **Validate at boundaries**. Input validation happens at the presentation/application layer.
- **Domain invariants are enforced in entities**. The domain layer protects business rules.
- **Fail fast**. Invalid data should never enter the system.

---

## 5. Error Handling

### 5.1 Exception Strategy
- **Use exceptions for exceptional cases only**. Not for control flow.
- **Create domain-specific exceptions**. `InvalidShippingRouteException`, not generic `Exception`.
- **Log exceptions at the boundary**. Don't log the same exception multiple times as it propagates.

### 5.2 Error Recovery
- **Design for failure**. External services will fail. Handle it gracefully.
- **Use circuit breakers** for external dependencies.
- **Provide meaningful error messages**. Users and developers need actionable information.

---

## 6. Testing Standards

### 6.1 Test Coverage
- **Domain logic: 100% coverage**. No exceptions.
- **Application services: 90%+ coverage**. Test all use cases.
- **Infrastructure: Integration tests required**. Unit test the mappings, integration test the connections.

### 6.2 Test Organization
```
/tests
  /unit           # Fast, isolated, no external dependencies
  /integration    # Database, external APIs, file system
  /e2e            # Full system tests
```

### 6.3 Test Quality
- **Arrange-Act-Assert pattern**. Structure is mandatory.
- **One assertion per test** (when possible). Tests should have a single reason to fail.
- **No test interdependencies**. Tests must run in any order.
- **Tests must be deterministic**. No flaky tests in the codebase.

---

## 7. Dependency Management

### 7.1 External Libraries
- **Justify every dependency**. Each library increases complexity and risk.
- **Pin versions explicitly**. No floating versions in production.
- **Audit regularly**. Remove unused dependencies monthly.

### 7.2 Internal Dependencies
- **Avoid circular dependencies**. If A depends on B and B depends on A, redesign.
- **Keep coupling low, cohesion high**. Modules should be independent but internally coherent.

---

## 8. Performance Considerations

### 8.1 Design for Performance
- **Understand Big O complexity**. Choose appropriate data structures and algorithms.
- **Lazy loading where appropriate**. Don't load data you won't use.
- **Cache strategically**. Cache expensive operations, but understand cache invalidation.

### 8.2 Database Performance
- **Index foreign keys and query columns**. Understand query execution plans.
- **Batch operations**. Don't execute N queries when 1 will do.
- **Pagination is required** for unbounded result sets.

### 8.3 Monitoring
- **Instrument critical paths**. Measure what matters: latency, throughput, error rates.
- **Set performance budgets**. Define acceptable response times and enforce them.

---

## 9. Documentation Standards

### 9.1 Code Documentation
- **Self-documenting code first**. Clear names reduce the need for comments.
- **Document WHY, not WHAT**. Explain decisions, not implementation.
- **Keep documentation close to code**. Architecture decision records (ADRs) live with the system.

### 9.2 API Documentation
- **All public APIs must be documented**. Include examples, error codes, and edge cases.
- **OpenAPI/Swagger specs required** for REST APIs.
- **Keep documentation in sync**. Outdated docs are worse than no docs.

### 9.3 Architecture Documentation
- **C4 model for system architecture**. Context, Containers, Components, Code.
- **Document key decisions**. Use ADRs for significant architectural choices.
- **Diagrams as code**. Use tools like PlantUML, Mermaid, or Structurizr.

---

## 10. Code Review Standards

### 10.1 Review Checklist
- [ ] Does this follow SOLID principles?
- [ ] Are dependencies pointing in the right direction?
- [ ] Is error handling appropriate?
- [ ] Are there tests, and do they pass?
- [ ] Is the code readable without comments?
- [ ] Are there any performance red flags?
- [ ] Is the documentation updated?

### 10.2 Review Culture
- **Reviews are mandatory**. No code goes to production unreviewed.
- **Reviews are educational**. Use them to share knowledge.
- **Be specific in feedback**. "This is unclear" → "Consider renaming `processData()` to `aggregateShipmentMetrics()`"

---

## 11. Refactoring Discipline

### 11.1 When to Refactor
- **Boy Scout Rule**: Leave code cleaner than you found it.
- **Before adding features**: Refactor to make the change easy, then make the change.
- **When tests are hard to write**: Hard-to-test code is a design smell.

### 11.2 Refactoring Safety
- **Tests must pass before and after**. No refactoring without test coverage.
- **Small, incremental changes**. Big rewrites fail.
- **Refactoring is not new features**. Keep them separate.

---

## 12. Security Principles

### 12.1 Input Validation
- **Never trust user input**. Validate, sanitize, and escape.
- **Use parameterized queries**. SQL injection is unacceptable.
- **Validate file uploads**. Check types, sizes, and content.

### 12.2 Authentication & Authorization
- **Authentication at the boundary**. Don't authenticate deep in the call stack.
- **Authorization on every operation**. Check permissions before executing commands.
- **Use established libraries**. Don't roll your own crypto or auth.

### 12.3 Data Protection
- **Encrypt sensitive data at rest and in transit**.
- **No secrets in code**. Use environment variables or secret management services.
- **Audit sensitive operations**. Log who did what and when.

---

## 13. Deployment & Operations

### 13.1 Configuration Management
- **Twelve-Factor App principles**. Configuration in environment, not code.
- **Environment parity**. Dev, staging, and production should be as similar as possible.
- **Feature flags for risky changes**. Deploy code, enable features separately.

### 13.2 Observability
- **Structured logging**. Use JSON, include correlation IDs.
- **Distributed tracing** for microservices.
- **Health checks and readiness probes**. Systems must report their status.

### 13.3 Deployment Strategy
- **Automated deployments**. No manual steps.
- **Rollback capability**. Every deployment must be reversible.
- **Zero-downtime deployments**. Use blue-green or rolling deployments.

---

## 14. Technical Debt Management

### 14.1 Identifying Debt
- **Code smells**: Duplicated code, long methods, large classes
- **Architectural smells**: Circular dependencies, god objects, tight coupling
- **Process smells**: Skipped tests, manual deployments, no reviews

### 14.2 Paying Down Debt
- **Track debt explicitly**. Use a debt register or backlog.
- **Allocate time for debt reduction**. 20% of sprint capacity minimum.
- **Prioritize high-interest debt**. Fix what causes the most pain first.

### 14.3 Preventing Debt
- **Definition of Done includes quality**. No "we'll fix it later."
- **Automated quality gates**. Linting, testing, and coverage checks block merges.
- **Regular architecture reviews**. Catch problems before they metastasize.

---

## 15. Continuous Improvement

### 15.1 Metrics
- **Measure code quality**: Cyclomatic complexity, code coverage, duplication
- **Measure delivery**: Lead time, deployment frequency, change failure rate
- **Measure reliability**: Uptime, error rates, mean time to recovery

### 15.2 Retrospectives
- **Regular team retrospectives**. What went well, what didn't, what to improve.
- **Act on findings**. Retrospectives without action are theater.
- **Track improvements**. Measure whether changes actually help.

### 15.3 Learning Culture
- **Code katas and practice**. Skills require deliberate practice.
- **Tech talks and knowledge sharing**. Learn from each other.
- **Stay current**. Technology evolves. So must we.

---

## Conclusion

Engineering excellence is not an accident. It's the result of discipline, standards, and relentless focus on quality. These principles are not bureaucracy—they're the foundation of systems that scale, adapt, and last.

**Write code that you'll be proud to maintain in 5 years.**
